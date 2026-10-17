"""FastAPI app: barcode scans, receipt upload, community price database, shop planner."""

import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, baseline, db, diet, identify, planner, scan


conn = db.connect()
db.init(conn)
app = FastAPI(title="Nostobon")
STATIC = Path(__file__).parent / "static"
SAMPLES = db.DATA / "sample_receipts"
STORES_FETCHED_AT = json.loads((db.DATA / "stores.json").read_text()).get("fetched_at")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

DIGITS = re.compile(r"\d{8,}")  # card and loyalty numbers never reach the database


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/meta")
def meta():
    return {
        "stats": db.stats(conn),
        "stores": db.stores(conn),
        "catalogue": db.catalogue(conn),
        "loyalty_schemes": db.LOYALTY_SCHEMES,
        "model": ai.MODEL,
        "ai_key_set": bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")),
        "stores_fetched_at": STORES_FETCHED_AT,
        "reference": db.reference_meta(),
        "product_index": db.kaggle_meta(),
        "chains": sorted({s["chain"] for s in db.stores(conn)}),
        "allergens": diet.ALLERGENS,
        "diets": {k: v["label"] for k, v in diet.DIETS.items()},
    }


@app.get("/api/geocode")
def geocode(postcode: str | None = None, lat: float | None = None, lon: float | None = None):
    """Used once, at profile setup. The profile keeps the result on the device."""
    try:
        if postcode:
            lat, lon = planner.geocode_postcode(postcode)
            pc = re.sub(r"\s+", "", postcode).upper()
            label = pc[:-3] + " " + pc[-3:]
        elif lat is not None and lon is not None:
            label = planner.nearest_postcode(lat, lon) or "Your location"
        else:
            raise HTTPException(400, "Give a postcode or a location.")
    except planner.LocationError as e:
        raise HTTPException(400, str(e))
    nearest = min(planner.km((lat, lon), (s["lat"], s["lon"])) for s in db.stores(conn))
    warning = None if nearest < 5 else f"Nearest shop we know is {nearest:.0f} km away. Nostobon covers Southampton only."
    return {"lat": lat, "lon": lon, "label": label, "warning": warning}


@app.get("/api/samples/{name}", response_class=PlainTextResponse)
def sample(name: str):
    path = SAMPLES / name
    if path.parent != SAMPLES or not path.is_file():
        raise HTTPException(404, "No such sample.")
    return path.read_text()


# ---------- receipts ----------

@app.post("/api/receipts/parse")
async def parse_receipt(file: UploadFile | None = File(None), text: str = Form("")):
    if file and file.filename:
        data = await file.read()
        media_type = file.content_type or ""
        source = "e-receipt" if media_type == "application/pdf" else "photo"
    elif text.strip():
        data, media_type, source = text.encode(), "text/plain", "text"
    else:
        raise HTTPException(400, "Upload a receipt file or paste the receipt text.")
    if len(data) > 8_000_000:
        raise HTTPException(413, "File over 8 MB. Take a smaller photo.")
    catalogue = db.catalogue(conn)
    warnings, parser = [], "ai"
    try:
        receipt = ai.parse_receipt(data, media_type, catalogue).model_dump()
    except ValueError as e:
        raise HTTPException(415, str(e))
    except ai.AIUnavailable as e:
        if media_type != "text/plain":
            raise HTTPException(503, f"Reading photos and PDFs needs the AI, which is unavailable: {e}")
        receipt, parser = baseline.parse_receipt_text(text, catalogue), "baseline"
        warnings.append(f"AI unavailable ({e}). Baseline regex parser used: check every line.")
    if not receipt["is_receipt"]:
        raise HTTPException(422, f"This does not look like a receipt: {receipt['reason_if_not']}")
    for line in receipt["lines"]:
        line["raw_text"] = DIGITS.sub("", line["raw_text"]).strip()
    warnings += identify.run(conn, receipt.get("chain"), receipt["lines"], use_ai=parser == "ai")
    if receipt["lines"] and receipt["total"] is not None:
        summed = sum(l["line_total"] - (l["loyalty_discount"] or 0) * l["quantity"] for l in receipt["lines"])
        if abs(summed - receipt["total"]) > 0.05:
            warnings.append(f"Lines add up to £{summed:.2f} but the receipt total is £{receipt['total']:.2f}. "
                            "A line may be missing or misread.")
    suggested = _suggest_store(receipt)
    if receipt.get("store_postcode") and not suggested:
        warnings.append(f"No {receipt.get('chain') or ''} store found near {receipt['store_postcode']}. Pick the store.")
    return {"receipt": receipt, "parser": parser, "source": source, "warnings": warnings,
            "suggested_store_id": suggested, "content_hash": hashlib.sha256(data).hexdigest(),
            "synthetic": b"SYNTHETIC" in data.upper()}  # our test receipts carry this marker


def _suggest_store(receipt: dict) -> str | None:
    pc, chain = receipt.get("store_postcode"), receipt.get("chain")
    if not pc:
        return None
    try:
        here = planner.geocode_postcode(pc)
    except (planner.LocationError, Exception):
        return None
    options = [s for s in db.stores(conn) if not chain or s["chain"] == chain]
    if not options:
        return None
    best = min(options, key=lambda s: planner.km(here, (s["lat"], s["lon"])))
    return best["id"] if planner.km(here, (best["lat"], best["lon"])) < 1.5 else None


class CommitLine(BaseModel):
    raw_text: str
    quantity: float
    unit_price: float
    loyalty_discount: float | None = None
    loyalty_scheme: str | None = None
    product_id: str | None = None
    confidence: str = "high"
    chain_product_id: int | None = None  # exact product the shopper confirmed
    identified_by: str | None = None     # ai | community | baseline | shopper


class Commit(BaseModel):
    store_id: str
    purchase_date: str | None = None
    source: str
    parser: str
    content_hash: str
    synthetic: bool = False
    lines: list[CommitLine]


@app.post("/api/receipts/commit")
def commit_receipt(body: Commit):
    store = db.store(conn, body.store_id)
    if not store:
        raise HTTPException(400, "Unknown store.")
    if conn.execute("SELECT 1 FROM receipts WHERE content_hash = ?", (body.content_hash,)).fetchone():
        raise HTTPException(409, "This receipt is already in the database.")
    today = date.today().isoformat()
    purchased = body.purchase_date if body.purchase_date and body.purchase_date <= today else today
    cur = conn.execute(
        "INSERT INTO receipts (store_id, purchased_on, source, parser, content_hash, synthetic) VALUES (?,?,?,?,?,?)",
        (store["id"], purchased, body.source, body.parser, body.content_hash, int(body.synthetic)))
    receipt_id, warnings, saved = cur.lastrowid, [], 0
    for l in body.lines:
        if l.unit_price <= 0 or l.unit_price > 500:
            warnings.append(f"Skipped {l.raw_text!r}: price £{l.unit_price} out of range.")
            continue
        outlier = 0
        if l.product_id:
            med = db.median_price(conn, l.product_id)
            if med and not (0.4 * med <= l.unit_price <= 2.5 * med):
                outlier = 1
                warnings.append(f"{l.raw_text!r} at £{l.unit_price:.2f} is far from the usual £{med:.2f}. "
                                "Saved but not used in plans until others confirm it.")
        loyalty_price = round(l.unit_price - l.loyalty_discount, 2) if l.loyalty_discount else None
        scheme = l.loyalty_scheme and db.LOYALTY_SCHEMES.get(store["chain"])
        exact = l.chain_product_id and conn.execute(
            "SELECT id FROM chain_products WHERE id = ? AND chain = ?", (l.chain_product_id, store["chain"])).fetchone()
        if l.chain_product_id and not exact:
            warnings.append(f"{l.raw_text!r}: the exact product picked is not sold by {store['chain']}. Saved without it.")
        raw = DIGITS.sub("", l.raw_text)
        conn.execute(
            """INSERT INTO observations (receipt_id, store_id, product_id, raw_line, quantity, unit_price,
               loyalty_price, loyalty_scheme, observed_on, confidence, outlier, synthetic, chain_product_id,
               identified_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (receipt_id, store["id"], l.product_id, raw, l.quantity, l.unit_price,
             loyalty_price, scheme if loyalty_price else None, purchased, l.confidence, outlier, int(body.synthetic),
             l.chain_product_id if exact else None, l.identified_by if exact else None))
        if exact and not body.synthetic:  # synthetic samples must not teach the community memory
            identify.remember(conn, store["chain"], raw, l.unit_price, l.chain_product_id, purchased)
        saved += 1
    conn.commit()
    return {"receipt_id": receipt_id, "saved_lines": saved, "warnings": warnings, "stats": db.stats(conn)}


# ---------- barcode scans ----------

@app.get("/api/barcode/{code}")
def barcode(code: str):
    return scan.describe(conn, code)


class ScanPrice(BaseModel):
    store_id: str
    barcode: str
    name: str                           # Open Food Facts name, or what the shopper typed
    unit_price: float                   # shelf price
    loyalty_price: float | None = None  # member price on the same label, if there is one
    product_id: str | None = None       # catalogue product, if the scan maps to one
    shopper_named: bool = False         # the shopper typed or corrected the name
    synthetic: bool = False


@app.post("/api/scans")
def save_scan(body: ScanPrice):
    store = db.store(conn, body.store_id)
    if not store:
        raise HTTPException(400, "Unknown store.")
    code, problem = scan.normalise(body.barcode)
    if problem:
        raise HTTPException(400, problem)
    name = DIGITS.sub("", body.name).strip()[:120]
    if not name:
        raise HTTPException(400, "Give the product a name.")
    if not 0 < body.unit_price <= 500:
        raise HTTPException(400, f"Price £{body.unit_price} is out of range.")
    if body.loyalty_price is not None and not 0 < body.loyalty_price < body.unit_price:
        raise HTTPException(400, "The member price has to be lower than the shelf price.")
    if body.product_id and not conn.execute("SELECT 1 FROM products WHERE id = ?", (body.product_id,)).fetchone():
        raise HTTPException(400, "Unknown catalogue product.")
    today = date.today().isoformat()
    if conn.execute("""SELECT 1 FROM observations WHERE barcode = ? AND store_id = ? AND observed_on = ?
                       AND unit_price = ? AND method = 'scan'""", (code, store["id"], today, body.unit_price)).fetchone():
        raise HTTPException(409, f"Already saved: £{body.unit_price:.2f} at {store['name']} today.")
    warnings = []
    own = scan.cached_own_label(conn, code)
    if own and own != store["chain"]:
        warnings.append(f"This is {own} own label, but the shop is {store['chain']}. Check you picked the right shop.")
    med = db.median_price(conn, body.product_id) if body.product_id else scan.median_for_barcode(conn, code)
    outlier = int(bool(med) and not (0.4 * med <= body.unit_price <= 2.5 * med))
    if outlier:
        warnings.append(f"£{body.unit_price:.2f} is far from the usual £{med:.2f}. Saved but not used in plans "
                        "until others confirm it.")
    scheme = db.LOYALTY_SCHEMES.get(store["chain"]) if body.loyalty_price else None
    if body.loyalty_price and not scheme:
        warnings.append(f"{store['chain']} has no loyalty scheme we know of. Member price saved without a scheme name.")
    conn.execute(
        """INSERT INTO observations (store_id, product_id, raw_line, quantity, unit_price, loyalty_price,
           loyalty_scheme, observed_on, confidence, outlier, synthetic, identified_by, barcode, method)
           VALUES (?,?,?,1,?,?,?,?,?,?,?,?,?,'scan')""",
        (store["id"], body.product_id, name, body.unit_price, body.loyalty_price, scheme, today, "high", outlier,
         int(body.synthetic), "shopper" if body.shopper_named else "barcode", code))
    conn.commit()
    if not body.product_id:
        warnings.append("Not one of the products we compare yet, so plans cannot use this price. It is kept for "
                        "when we add it.")
    return {"saved": True, "observed_on": today, "warnings": warnings, "stats": db.stats(conn)}


@app.get("/api/barcode/{code}/prices")
def barcode_prices(code: str):
    code, problem = scan.normalise(code)
    if problem:
        raise HTTPException(400, problem)
    rows = conn.execute(
        """SELECT o.unit_price, o.loyalty_price, o.loyalty_scheme, o.observed_on, o.outlier, o.synthetic,
                  s.name AS store, s.chain
           FROM observations o JOIN stores s ON s.id = o.store_id
           WHERE o.barcode = ? ORDER BY o.observed_on DESC, o.id DESC LIMIT 50""", (code,)).fetchall()
    return {"prices": [dict(r) for r in rows]}


# ---------- planning ----------

class PlanRequest(BaseModel):
    list_text: str
    lat: float
    lon: float
    mode: str = "walk"
    radius_km: float = 3.0
    max_shops: int = 2
    loyalty: list[str] = []
    discounts: dict[str, float] = {}
    allergies: list[str] = []
    diets: list[str] = []
    strict_traces: bool = False
    avoid_chains: list[str] = []


@app.post("/api/plan")
def make_plan(body: PlanRequest):
    if not body.list_text.strip():
        raise HTTPException(400, "Your list is empty.")
    if body.mode not in planner.SPEED_KMH:
        raise HTTPException(400, f"mode must be one of {list(planner.SPEED_KMH)}")
    unknown = set(body.allergies) - set(diet.ALLERGENS) | set(body.diets) - set(diet.DIETS)
    if unknown:
        raise HTTPException(400, f"Unknown allergy or diet: {', '.join(sorted(unknown))}")
    home = (body.lat, body.lon)
    catalogue, warnings, matcher = db.catalogue(conn), [], "ai"
    try:
        items = ai.match_list(body.list_text, catalogue)
    except ai.AIUnavailable as e:
        parts = [p.strip() for p in re.split(r"[,\n;]+", body.list_text) if p.strip()]
        items, matcher = baseline.match_list(parts, catalogue), "baseline"
        warnings.append(f"AI unavailable ({e}). Baseline fuzzy matcher used: brands and vague items "
                        "will be matched badly.")
    items = diet.apply(items, catalogue, set(body.allergies), set(body.diets), body.strict_traces)
    matched = [i for i in items if i["status"] == "matched"]
    ids = sorted({pid for i in matched for pid in i["product_ids"]})
    community = db.latest_prices(conn, ids, planner.MAX_AGE_DAYS)
    reference = db.reference_prices(conn, ids, planner.REF_MAX_AGE_DAYS)
    discounts = {k: max(0.0, min(v, 50.0)) for k, v in body.discounts.items()}
    result = planner.plan(matched, community, reference, db.stores(conn), home, mode=body.mode,
                          radius_km=body.radius_km, max_shops=max(1, min(body.max_shops, 3)),
                          loyalty=set(body.loyalty), discounts=discounts,
                          avoid_chains=set(body.avoid_chains)) if matched else {
        "error": "Nothing on the list matched a product we track" + (" and suits your profile." if
                                                                       body.allergies or body.diets else ".")}
    names = {p["id"]: p["name"] for p in catalogue}
    for option in result.get("options", []):
        for line in option["lines"]:
            line["product_name"] = names.get(line["product_id"])
    return {"matcher": matcher, "items": items, "plan": result, "warnings": warnings,
            "home": {"lat": home[0], "lon": home[1]}}


@app.get("/api/prices/{product_id}")
def product_prices(product_id: str):
    rows = conn.execute(
        """SELECT o.unit_price, o.loyalty_price, o.loyalty_scheme, o.observed_on, o.outlier, o.synthetic,
                  o.raw_line, s.name AS store, s.chain, cp.name AS exact_product, o.identified_by, o.method
           FROM observations o JOIN stores s ON s.id = o.store_id
           LEFT JOIN chain_products cp ON cp.id = o.chain_product_id
           WHERE o.product_id = ? ORDER BY o.observed_on DESC LIMIT 200""", (product_id,)).fetchall()
    ref = conn.execute(
        """SELECT unit_price, loyalty_price, promo_price, observed_on, location, city, chain, proof_type, off_name
           FROM reference_prices WHERE product_id = ? ORDER BY observed_on DESC LIMIT 100""", (product_id,)).fetchall()
    return {"community": [dict(r) for r in rows], "reference": [dict(r) for r in ref]}

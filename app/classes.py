"""Product classes: which scanned products count as the same thing across chains.

Barcodes only join identical products. Own label has a different barcode at every chain, so
Tesco hazelnut spread 400g and Aldi Nutoka 400g share nothing a lookup can join. A class groups
products a shopper would swap for each other. The 46 catalogue products are the first classes.
A scan that fits no class starts a new one, so the next chain's version has something to join.

Order for one barcode:
1. A shopper already saved a price for it: use that class.
2. AI: Claude reads the product and the list of classes and says same (which one), new or unsure.
   The answer is cached per barcode.
3. Baseline (rules, also the fallback when the AI is unavailable): the catalogue rules in
   app/offmap.py, else a class member with the same Open Food Facts category, size within 10%
   and the same brand (any own label counts as one brand).
"""

import json
import re
import sqlite3
import threading
from datetime import date, datetime, timezone

from . import ai
from .offmap import map_product
from .scan import own_label_chain, own_label_tier

SIZE_TOLERANCE = 0.10
MEMBERS_SHOWN = 3  # example members per class in the AI prompt
UNITS = {"kg": ("mass", 1000), "g": ("mass", 1), "l": ("volume", 1000), "litre": ("volume", 1000),
         "litres": ("volume", 1000), "liter": ("volume", 1000), "ml": ("volume", 1), "cl": ("volume", 10),
         "pint": ("volume", 568.26), "pints": ("volume", 568.26), "pt": ("volume", 568.26)}
AMOUNT = r"(\d+(?:[.,]\d+)?)\s*(kg|g|ml|cl|l|litres?|liter|pints?|pt)\b"
COUNT = r"\b(\d+)\s*(?:x\s*)?(?:large |medium |mixed )?(?:eggs?|pcs|pieces|pack|pk|tea ?bags|bags|rolls|fruits)\b"


def parse_size(text: str) -> dict[str, float]:
    """{"mass": grams, "volume": ml, "count": n}, whichever the text gives. "4 x 400g" is 1600 g."""
    t = (text or "").lower().replace("×", "x")
    out = {}
    multi = re.search(r"\b(\d+)\s*x\s*" + AMOUNT, t)
    if multi:
        dim, factor = UNITS[multi.group(3)]
        out[dim] = int(multi.group(1)) * float(multi.group(2).replace(",", ".")) * factor
        out["count"] = int(multi.group(1))
    else:
        one = re.search(AMOUNT, t)
        if one:
            dim, factor = UNITS[one.group(2)]
            out[dim] = float(one.group(1).replace(",", ".")) * factor
    count = re.search(COUNT, t) or re.fullmatch(r"\s*(\d+)\s*", t)
    if count and "count" not in out:
        out["count"] = int(count.group(1))
    return out


def size_close(a: dict, b: dict) -> bool:
    shared = set(a) & set(b)
    return bool(shared) and all(abs(a[k] - b[k]) <= SIZE_TOLERANCE * max(a[k], b[k]) for k in shared)


def brand_key(p: dict) -> str:
    """The own label tier ("value", "own" or "premium") for any supermarket's own label, else the first brand listed."""
    if own_label_chain(p):
        return own_label_tier(f"{p.get('brands') or ''} {p.get('product_name_en') or p.get('product_name') or ''}")
    return re.sub(r"[^a-z0-9]", "", (p.get("brands") or "").split(",")[0].lower())


def snapshot(p: dict) -> dict:
    """The fields matching uses. Stored with each class member."""
    tags = p.get("categories_tags") or []
    return {"name": p.get("product_name_en") or p.get("product_name") or "", "brand": p.get("brands") or "",
            "quantity": p.get("quantity") or "", "category": tags[-1] if tags else "",
            "categories": tags[-3:], "own_label_of": own_label_chain(p)}


# ---------- classes and members ----------

def all_classes(conn: sqlite3.Connection) -> list[dict]:
    classes = {r["id"]: {**dict(r), "members": []} for r in conn.execute(
        "SELECT id, name, generic, brand, size, origin FROM products ORDER BY generic, brand")}
    for m in conn.execute("SELECT * FROM class_members WHERE class_id IS NOT NULL ORDER BY added_on DESC"):
        if m["class_id"] in classes:
            classes[m["class_id"]]["members"].append(dict(m))
    return list(classes.values())


def confirmed(conn: sqlite3.Connection, code: str) -> dict | None:
    row = conn.execute("SELECT * FROM class_members WHERE barcode = ?", (code,)).fetchone()
    return dict(row) if row else None


# ---------- baseline ----------

def baseline_match(p: dict, classes: list[dict]) -> dict:
    ids = {c["id"] for c in classes}
    pid = map_product(p)
    if pid in ids:
        return {"status": "same", "class_id": pid, "by": "rules", "reason": "Matches our catalogue rules."}
    snap, key = snapshot(p), brand_key(p)
    size = parse_size(snap["quantity"] + " " + snap["name"])
    for c in classes:
        for m in c["members"]:
            m_brand = own_label_tier(f"{m['brand']} {m['name']}") if m["own_label_of"] else \
                re.sub(r"[^a-z0-9]", "", (m["brand"] or "").split(",")[0].lower())
            if (snap["category"] and m["category"] == snap["category"] and m_brand == key
                    and size_close(size, parse_size(m["quantity"] + " " + m["name"]))):
                return {"status": "same", "class_id": c["id"], "by": "rules",
                        "reason": f"Same category, brand and size as {m['name']}."}
    if not size:
        return {"status": "unsure", "class_id": None, "by": "rules", "reason": "Pack size unknown."}
    return {"status": "new", "class_id": None, "by": "rules", "reason": "No class with this category, brand and size.",
            "proposal": {"name": f"{snap['name'].capitalize()} {snap['quantity']}".strip(),
                         "generic": snap["category"].split(":")[-1] or "other",
                         "brand": key if own_label_chain(p) else (p.get("brands") or "").split(",")[0].strip() or "unknown",
                         "size": snap["quantity"]}}


# ---------- AI ----------

def _sizes_agree(p: dict, c: dict) -> bool:
    """Guard on an AI "same": product data is crowd-sourced text, so a size we can read must agree."""
    snap = snapshot(p)
    mine = parse_size(snap["quantity"] + " " + snap["name"])
    theirs = parse_size(c["size"]) or next((parse_size(m["quantity"]) for m in c["members"] if parse_size(m["quantity"])), {})
    return not (set(mine) & set(theirs)) or size_close(mine, theirs)


def ai_match(p: dict, classes: list[dict]) -> dict:
    result = ai.match_class(snapshot(p), classes, MEMBERS_SHOWN)
    ids = {c["id"] for c in classes}
    out = {"status": result.status, "class_id": None, "by": "ai", "reason": result.reason}
    if result.status == "same":
        if result.class_id not in ids:
            out.update(status="unsure", reason=f"The AI named a class we do not have ({result.class_id}).")
        elif not _sizes_agree(p, next(c for c in classes if c["id"] == result.class_id)):
            out.update(status="unsure", reason="The AI said same, but the pack sizes differ by more than 10%.")
        else:
            out["class_id"] = result.class_id
    if result.status == "new" and result.new_class:
        out["proposal"] = result.new_class.model_dump()
    return out


def assign(conn: sqlite3.Connection, code: str, p: dict, use_ai: bool = True) -> tuple[dict, list[str]]:
    """(match, warnings) for one Open Food Facts product. Never raises for AI trouble: falls back to rules."""
    member = confirmed(conn, code)
    if member:
        if not member["class_id"]:
            return {"status": "unsure", "class_id": None, "by": "shopper",
                    "reason": "A shopper said this is not the same as the product we suggested."}, []
        who = {"ai": "Suggested by AI", "rules": "Suggested by simple rules"}.get(member["by"], "Chosen")
        return {"status": "same", "class_id": member["class_id"], "by": "shopper",
                "reason": f"{who}, accepted by a shopper on {member['added_on']}."}, []
    row = conn.execute("SELECT result FROM class_guesses WHERE barcode = ?", (code,)).fetchone()
    if row:
        return json.loads(row["result"]), []
    classes = all_classes(conn)
    if not ai.key_set():
        return baseline_match(p, classes), ["No AI key set, so simple rules chose the match."] if use_ai else []
    if use_ai:
        try:
            match = ai_match(p, classes)
        except ai.AIUnavailable as e:
            return baseline_match(p, classes), [f"AI could not match this product ({e}). Simple rules chose the match."]
        conn.execute("INSERT OR REPLACE INTO class_guesses (barcode, result, made_at) VALUES (?,?,?)",
                     (code, json.dumps(match), datetime.now(timezone.utc).isoformat(timespec="seconds")))
        conn.commit()
        return match, []
    return baseline_match(p, classes), []


def _new_class_id(conn: sqlite3.Connection, proposal: dict) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", f"{proposal['name']} {proposal['brand']}".lower()).strip("-")[:50] or "product"
    pid, n = f"scan-{base}", 2
    while conn.execute("SELECT 1 FROM products WHERE id = ?", (pid,)).fetchone():
        pid, n = f"scan-{base}-{n}", n + 1
    return pid


def _create_class(conn: sqlite3.Connection, prop: dict) -> str:
    class_id = _new_class_id(conn, prop)
    conn.execute("""INSERT INTO products (id, name, generic, brand, size, origin, created_on)
                    VALUES (?,?,?,?,?,'scan',?)""",
                 (class_id, prop["name"][:80], prop["generic"][:40], prop["brand"][:40], prop["size"][:30],
                  date.today().isoformat()))
    return class_id


def save_member(conn: sqlite3.Connection, code: str, p: dict | None, match: dict, accepted: bool) -> str | None:
    """Record the shopper's answer for this barcode. Creates the class for a "new" match. Returns the class id."""
    class_id = None
    if accepted and match["status"] == "same":
        class_id = match["class_id"]
    elif accepted and match["status"] == "new" and match.get("proposal"):
        class_id = _create_class(conn, match["proposal"])
    snap = snapshot(p or {})
    conn.execute("""INSERT OR REPLACE INTO class_members
                    (barcode, class_id, name, brand, quantity, category, own_label_of, by, added_on)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                 (code, class_id, snap["name"], snap["brand"], snap["quantity"], snap["category"],
                  snap["own_label_of"], match["by"] if accepted else "shopper", date.today().isoformat()))
    return class_id


# ---------- shelf labels ----------
# A label is matched to an exact product on the chain's list (chain_products), not a barcode. The first
# time one is saved, the same AI or rules as a barcode pick its class, and a link joins the two. The shopper
# already confirmed the exact product; a wrong class shows in the save note and can be fixed in the database.

def pack_size(cp: sqlite3.Row | dict) -> str:
    """"500g" from the name, else price over price per kg, litre or item ("about 833g", "about 12 pack").
    Many chains leave the size out of the name. Matching refuses a product with no size."""
    m = re.search(r"\b\d+\s*[x×]\s*" + AMOUNT, cp["name"], re.I) or re.search(AMOUNT, cp["name"], re.I) \
        or re.search(COUNT, cp["name"], re.I)
    if m:
        return m.group(0)
    unit = (cp["unit"] or "").lower()
    if cp["unit_price"] and cp["price"] and unit in ("kg", "l"):
        return f"about {round(1000 * cp['price'] / cp['unit_price'])}{'g' if unit == 'kg' else 'ml'}"
    if cp["unit_price"] and cp["price"] and unit in ("unit", "each", "ea"):
        return f"about {round(cp['price'] / cp['unit_price'])} pack"
    return ""


def assign_chain_product(conn: sqlite3.Connection, cp: sqlite3.Row) -> tuple[str | None, str | None, list[str]]:
    """(class id, note for the shopper, warnings). Links a new or matched class to this chain product."""
    linked = conn.execute("SELECT class_id FROM class_links WHERE chain_product_id = ?", (cp["id"],)).fetchone()
    if linked:
        return linked["class_id"], None, []
    # Shaped like an Open Food Facts product so the barcode matchers work unchanged
    p = {"product_name": cp["name"], "brands": cp["chain"] if cp["own_brand"] else "", "quantity": pack_size(cp),
         "categories_tags": [cp["category"]] if cp["category"] else []}
    match, warnings = assign(conn, f"chain:{cp['id']}", p)
    if match["status"] == "same":
        class_id = match["class_id"]
        name = conn.execute("SELECT name FROM products WHERE id = ?", (class_id,)).fetchone()["name"]
        note = f"Compared with other shops as {name} ({'AI' if match['by'] == 'ai' else 'simple rules'})."
    elif match["status"] == "new" and match.get("proposal"):
        class_id = _create_class(conn, match["proposal"])
        note = "New to us. Added to the products plans compare, so lists can find it now."
    else:
        return None, None, [f"Not compared with other shops yet: {match['reason']} The price is kept."]
    # One product per class per chain. If the class already has one here, this price still counts for it.
    # A row with no product (the search found none here) gives way to the product a shopper just confirmed.
    conn.execute("""INSERT INTO class_links VALUES (?,?,?,'scan',?) ON CONFLICT (class_id, chain)
                    DO UPDATE SET chain_product_id = excluded.chain_product_id, reason = excluded.reason
                    WHERE class_links.chain_product_id IS NULL""",
                 (class_id, cp["chain"], cp["id"], f"{match['by']}: {match['reason']}"))
    conn.execute("UPDATE observations SET product_id = ? WHERE chain_product_id = ? AND product_id IS NULL",
                 (class_id, cp["id"]))
    return class_id, note, warnings


# ---------- starting prices at the other chains ----------
# A class started by a scan has a price only at the shop it was scanned in. Linking it to the same product
# at every other chain gives it their online price too, so a plan can compare shops for it straight away.

LINKING: set[str] = set()


def link_other_chains(conn: sqlite3.Connection, class_id: str) -> list[str]:
    """Link a scan class to the product each chain without a link sells, or record that none fits
    (chain_product_id NULL, so the search is not repeated). Same rules as scripts/link_classes.py."""
    from . import identify
    cls = conn.execute("SELECT * FROM products WHERE id = ? AND origin = 'scan'", (class_id,)).fetchone()
    if not cls:
        return []
    cls = dict(cls)
    done = {r[0] for r in conn.execute("SELECT chain FROM class_links WHERE class_id = ?", (class_id,))}
    use_ai, out = ai.key_set(), []
    for chain in sorted(identify.chains_indexed(conn) - done):
        shortlist = identify.class_shortlist(conn, cls, chain)
        pick, reason, by = None, "No product of this chain shares a word with it.", "rules"
        if shortlist and use_ai:
            try:
                answer = next(iter(ai.link_classes(chain, [(cls, shortlist)])), None)
            except ai.AIUnavailable as e:
                out.append(f"{chain}: AI unavailable ({e}), not linked")
                continue  # tried again on the next save
            pick = next((c for c in shortlist if answer and c["id"] == answer.chain_product_id), None)
            reason, by = (answer.reason if answer else "No answer from the AI."), "ai"
            if pick and not identify.size_fits(cls, pick["size"]):
                pick, reason = None, f"{pick['name']} is more than 10% off in size."
            elif pick and not pick["size"]:
                pick, reason = None, f"{pick['name']} has no pack size we can read."
            elif pick and cls["brand"] in identify.OWN_TIERS and pick["own_brand"] \
                    and own_label_tier(pick["name"]) != cls["brand"]:
                pick, reason = None, f"{pick['name']} is a different own label tier."
        elif shortlist:
            pick, reason = identify.rules_link(cls, shortlist)
        conn.execute("INSERT OR IGNORE INTO class_links VALUES (?,?,?,'scan',?)",
                     (class_id, chain, pick["id"] if pick else None, f"{by}: {reason}"))
        out.append(f"{chain}: {pick['name'] if pick else 'none'} ({by}: {reason})")
    conn.commit()
    return out


def link_in_background(conn: sqlite3.Connection, class_id: str | None) -> None:
    """After a save: link a scan class at the other chains without holding up the shopper."""
    if not class_id or class_id in LINKING or not conn.execute(
            "SELECT 1 FROM products WHERE id = ? AND origin = 'scan'", (class_id,)).fetchone():
        return
    LINKING.add(class_id)

    def run():
        try:
            link_other_chains(conn, class_id)
        finally:
            LINKING.discard(class_id)
    threading.Thread(target=run, daemon=True).start()

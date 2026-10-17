"""Non-AI baseline: regex receipt parsing and fuzzy string matching.

This is what the AI is measured against in scripts/eval.py. It also runs in the
app when no API key is set, with a visible banner saying so.
"""

import re
from datetime import date
from difflib import SequenceMatcher

CUTOFF = 0.45  # tuned on data/eval/*_tune.json only

PRICE_LINE = re.compile(r"^(?P<name>.*?[A-Za-z].*?)\s+(?P<qty>\d+\s*[x@]\s*)?£?(?P<price>-?\d+\.\d{2})\s*[A-Z]?$")
SKIP = re.compile(r"total|subtotal|balance|change|cash|card|visa|mastercard|vat|due|paid", re.I)
LOYALTY = re.compile(r"clubcard|nectar|lidl plus|member|more card|rewards|sparks", re.I)
CHAINS = {"Tesco": r"tesco", "Sainsbury's": r"sainsbury", "Asda": r"asda", "Lidl": r"lidl", "Aldi": r"aldi",
          "Morrisons": r"morrisons", "Co-op": r"co-?op", "M&S": r"m\s*&\s*s|marks", "Iceland": r"iceland"}


def _norm(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _score(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    ratio = SequenceMatcher(None, a, b).ratio()
    wa, wb = set(a.split()), set(b.split())
    overlap = len(wa & wb) / max(len(wa), 1)
    return max(ratio, overlap)


def best_product(text: str, catalogue: list[dict]) -> tuple[dict | None, float]:
    scored = [(max(_score(text, p["name"]), _score(text, p["generic"].replace("-", " "))), p) for p in catalogue]
    # Ties go to own label: "milk" scores 1.0 against both semi-skimmed and Cadbury Dairy Milk.
    score, product = max(scored, key=lambda t: (t[0], t[1]["brand"] == "own"))
    return (product, score) if score >= CUTOFF else (None, score)


def match_list(items: list[str], catalogue: list[dict]) -> list[dict]:
    """Baseline list matcher: best fuzzy product, then accept any brand in its group."""
    out = []
    for text in items:
        product, score = best_product(text, catalogue)
        if not product:
            out.append({"input_text": text, "quantity": 1, "status": "not_in_catalogue", "generic": None,
                        "brand": None, "product_ids": [], "options": [], "note": f"no fuzzy match (best {score:.2f})"})
            continue
        group = [p for p in catalogue if p["generic"] == product["generic"]]
        words = set(_norm(text).split())
        named = [p for p in group if p["brand"] != "own" and set(_norm(p["brand"]).split()) & words]
        brand = named[0]["brand"] if named else None
        ids = [p["id"] for p in (named or group)]
        out.append({"input_text": text, "quantity": 1, "status": "matched", "generic": product["generic"],
                    "brand": brand, "product_ids": ids, "options": [], "note": f"fuzzy {score:.2f}"})
    return out


def parse_receipt_text(text: str, catalogue: list[dict]) -> dict:
    """Baseline receipt parser: one regex per line, loyalty savings attach to the line above."""
    lines = []
    for raw in text.splitlines():
        raw = raw.strip()
        m = PRICE_LINE.match(raw)
        if not m:
            continue
        price = float(m["price"])
        if price < 0 or LOYALTY.search(m["name"]):
            if lines and LOYALTY.search(m["name"]):
                lines[-1]["loyalty_discount"] = abs(price)
            continue
        if SKIP.search(m["name"]):
            continue
        product, _ = best_product(m["name"], catalogue)
        lines.append({"raw_text": m["name"].strip(), "search_terms": m["name"].strip(), "quantity": 1,
                      "line_total": price, "unit_price": price,
                      "loyalty_discount": None, "product_id": product["id"] if product else None,
                      "confidence": "low"})
    chain = next((c for c, pat in CHAINS.items() if re.search(pat, text, re.I)), None)
    return {"is_receipt": bool(lines), "reason_if_not": None if lines else "no price lines found",
            "chain": chain, "store_postcode": None, "purchase_date": None, "lines": lines, "total": None}


# ---------- shelf labels ----------

MONEY = r"(?:£\s*(\d+(?:\.\d{1,2})?)|(\d+)\s*p\b)"
SCHEMES = {"clubcard": "Clubcard", "nectar": "Nectar", "lidl plus": "Lidl Plus", "more card": "More Card",
           "member": "Co-op Membership"}
UNIT_PRICE = re.compile(MONEY + r"\s*(?:per|/)\s*(?:\d+\s*)?(?:kg|g|l|ml|litre|each|ea)\b", re.I)
MULTIBUY = re.compile(r"\b(?:any\s+)?(\d+)\s+for\s+" + MONEY, re.I)
WAS = re.compile(r"\bwas\s+" + MONEY, re.I)
ENDS = re.compile(r"\b(?:ends?|until|valid until|offer ends|expires)\s*:?\s*(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?", re.I)
SIZE = re.compile(r"\b\d+\s*x\s*\d+(?:\.\d+)?\s*(?:kg|g|ml|cl|l)\b|\b\d+(?:\.\d+)?\s*(?:kg|g|ml|cl|l|litres?|pints?|pk|pack)\b", re.I)


def _money(m: re.Match, start: int) -> float:
    pounds, pence = m.group(start), m.group(start + 1)
    return float(pounds) if pounds else int(pence) / 100


def _end_date(day: int, month: int, year: str | None, today: date) -> str | None:
    try:
        if year:
            return date(int(year) + (2000 if len(year) == 2 else 0), month, day).isoformat()
        near = [date(today.year + k, month, day) for k in (-1, 0, 1)]  # an offer that ended last week is not next year's
        return min(near, key=lambda d: abs((d - today).days)).isoformat()
    except ValueError:
        return None


def read_label_text(text: str, today: date | None = None) -> dict:
    """Baseline shelf label reader: regexes over the text printed on the label, typed by the shopper.
    Same fields as the AI read (app/ai.py ShelfLabel), so both go through the same matching and checks."""
    today = today or date.today()
    out = {"is_label": True, "reason_if_not": None, "chain": None, "product_text": "", "search_terms": "", "size": None,
           "shelf_price": None, "was_price": None, "unit_price_text": None, "loyalty_price": None,
           "loyalty_scheme": None, "multibuy_qty": None, "multibuy_price": None, "multibuy_members_only": False,
           "promo_text": None, "valid_until": None, "other_labels": 0, "unclear": []}
    out["chain"] = next((c for c, pat in CHAINS.items() if re.search(pat, text, re.I)), None)
    plain = []
    for line in [l.strip() for l in text.splitlines() if l.strip()]:
        rest = line
        scheme = next((v for k, v in SCHEMES.items() if k in line.lower()), None)
        if u := UNIT_PRICE.search(rest):
            out["unit_price_text"] = u.group(0)
            rest = rest.replace(u.group(0), " ")
        if e := ENDS.search(rest):
            out["valid_until"] = _end_date(int(e.group(1)), int(e.group(2)), e.group(3), today)
            rest = rest.replace(e.group(0), " ")
        if m := MULTIBUY.search(rest):
            out.update(multibuy_qty=int(m.group(1)), multibuy_price=_money(m, 2), promo_text=m.group(0),
                       multibuy_members_only=bool(scheme))
            rest = rest.replace(m.group(0), " ")
        if w := WAS.search(rest):
            out["was_price"] = _money(w, 1)
            rest = rest.replace(w.group(0), " ")
        prices = [_money(p, 1) for p in re.finditer(MONEY, rest, re.I)]
        if prices and scheme and out["loyalty_price"] is None:
            out.update(loyalty_price=prices[0], loyalty_scheme=scheme)
        elif prices and out["shelf_price"] is None:
            out["shelf_price"] = prices[0]
        elif not prices and re.search(r"[A-Za-z]{3}", rest) and not scheme:
            plain.append(rest.strip())
    name = " ".join(plain)
    if s := SIZE.search(name):
        out["size"] = s.group(0)
    out["product_text"] = name
    out["search_terms"] = _norm(SIZE.sub(" ", name))
    if out["shelf_price"] is None:
        out["unclear"].append("shelf price")
    return out

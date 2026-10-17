"""Non-AI baseline: regex receipt parsing and fuzzy string matching.

This is what the AI is measured against in scripts/eval.py. It also runs in the
app when no API key is set, with a visible banner saying so.
"""

import re
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

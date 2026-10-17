"""Shelf label photo: read the prices, then work out which product the label is for.

1. AI read (vision): description, size, shelf price, member price and scheme, multibuy, offer end date.
   Nothing is saved until the shopper has checked every field.
2. Shortlist (no AI): products the chain sells (Kaggle index) sharing words with the label, sized and
   priced like it (app/identify.py).
3. AI pick: exact, ask (2 to 4 options) or none. A size we can read that differs by more than 10% turns
   "exact" into "ask". Without the AI, the top 3 of the shortlist are offered.
The product picked links the price to a class shared across chains (class_links), so plans can use it.
"""

import sqlite3
from datetime import date

from . import ai, baseline, classes, db, identify


def _option(conn: sqlite3.Connection, r: dict) -> dict:
    link = conn.execute("""SELECT p.id, p.name FROM class_links l JOIN products p ON p.id = l.class_id
                           WHERE l.chain_product_id = ?""", (r["id"],)).fetchone()
    return {"id": r["id"], "name": r["name"], "price": r["price"], "seen_on": r["seen_on"],
            "own_brand": r["own_brand"], "class_id": link["id"] if link else None,
            "class_name": link["name"] if link else None}


def match(conn: sqlite3.Connection, chain: str, label: dict, use_ai: bool) -> tuple[dict, list[str]]:
    """(match, warnings). match has status exact | ask | none | no_index, options, picked, by and a note."""
    if chain not in identify.chains_indexed(conn):
        return {"status": "no_index", "options": [], "picked": None, "by": None,
                "note": f"No product list for {chain} yet. The price is saved under the name on the label."}, []
    words = " ".join(filter(None, [label.get("search_terms") or label.get("product_text"), label.get("size")]))
    candidates = identify.shortlist(conn, chain, words, label.get("shelf_price"))
    if not candidates:
        return {"status": "none", "options": [], "picked": None, "by": "search",
                "note": f"No {chain} product shares a word with this label."}, []
    by_id = {c["id"]: c for c in candidates}
    warnings = []
    if use_ai:
        try:
            pick = ai.pick_for_label(chain, label, candidates)
        except ai.AIUnavailable as e:
            warnings.append(f"AI could not pick the product ({e}). Showing the closest name matches instead.")
            pick = None
        if pick:
            ids = [i for i in pick.candidate_ids if i in by_id][:4]
            status = pick.status if ids else "none"
            if status == "exact" and len(ids) != 1:
                status = "ask"
            reason = pick.reason
            if status == "exact" and not _size_agrees(label, by_id[ids[0]]["size"]):
                status, reason = "ask", "The AI picked this, but the size on the label differs. Check it."
            return {"status": status, "options": [_option(conn, by_id[i]) for i in ids],
                    "picked": ids[0] if status == "exact" else None, "by": "ai", "note": reason}, warnings
    return {"status": "ask", "options": [_option(conn, c) for c in candidates[:3]], "picked": None, "by": "baseline",
            "note": "Closest name and price matches, not checked by AI."}, warnings


def _size_agrees(label: dict, size: str) -> bool:
    mine = classes.parse_size(f"{label.get('size') or ''} {label.get('product_text') or ''}")
    theirs = classes.parse_size(size)
    return not (set(mine) & set(theirs)) or classes.size_close(mine, theirs)


def checks(label: dict, chain: str) -> list[str]:
    """Rules on what the AI read. Each one is shown to the shopper, who fixes the field before saving."""
    out = []
    today = date.today().isoformat()
    if label.get("chain") and label["chain"] != chain:
        out.append(f"This looks like a {label['chain']} label, but the shop picked is {chain}. Check the shop.")
    if label.get("shelf_price") is None:
        out.append("The shelf price could not be read. Type it from the label.")
    if label.get("loyalty_price") is not None and label.get("shelf_price") and label["loyalty_price"] >= label["shelf_price"]:
        out.append("The member price read is not lower than the shelf price. One of them is misread.")
    scheme = db.LOYALTY_SCHEMES.get(chain)
    if label.get("loyalty_price") is not None and not scheme:
        out.append(f"{chain} has no loyalty scheme we know of. Check the member price.")
    if label.get("valid_until") and label["valid_until"] < today:
        out.append(f"The offer on this label ended on {label['valid_until']}. Plans will not use the offer price.")
    if label.get("other_labels"):
        out.append(f"{label['other_labels']} other label{'s' if label['other_labels'] > 1 else ''} in the photo. "
                   "We read the one in the middle. Check it is the right one.")
    if label.get("unclear"):
        out.append("Could not read clearly: " + ", ".join(label["unclear"]) + ". Check these.")
    return out


def read(conn: sqlite3.Connection, data: bytes, media_type: str, chain: str) -> dict:
    """Raises ai.AIUnavailable (photos need the AI) and ValueError (file type)."""
    label = ai.read_label(data, media_type, date.today().isoformat()).model_dump()
    if not label["is_label"]:
        return {"status": "not_label", "note": label["reason_if_not"] or "This does not look like a shelf label."}
    m, warnings = match(conn, chain, label, use_ai=True)
    return {"status": "read", "label": label, "match": m, "warnings": checks(label, chain) + warnings, "read_by": "ai"}


def read_typed(conn: sqlite3.Connection, text: str, chain: str) -> dict:
    """No photo or no AI: the shopper types what the label says. Rules read the prices, word search finds products."""
    label = baseline.read_label_text(text)
    m, _ = match(conn, chain, label, use_ai=False)
    return {"status": "read", "label": label, "match": m, "warnings": checks(label, chain), "read_by": "baseline"}

"""Work out the exact product behind a receipt line.

Receipts often print a vague name ("CHICKEN 4.30"). Three steps narrow it:
1. Community memory: the same line at the same price at this chain, already confirmed by shoppers.
2. Shortlist (no AI): products the chain sells (Kaggle index) that share words with the line,
   ordered by word match and by how close their 2024 price is to the price paid.
3. AI pick: Claude reads the line, the price and the shortlist and says exact, ask (2 to 4 options
   for the shopper) or none. Without the AI, the top 3 of the shortlist are offered instead.
"""

import math
import re
import sqlite3

from . import ai
from .scan import own_label_chain

SHORTLIST = 25
PRICE_BAND = (0.65, 1.7)  # paid / 2024 price. Outside this the product is ruled out.
MEMORY_TOLERANCE = 0.05   # £, same price for memory purposes


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


def _fts_query(words: str) -> str | None:
    terms = []
    for w in norm(words).split():
        if len(w) >= 2 and not w.isdigit():
            terms.append(f'"{w}"')  # the index stems words, so "thighs" also finds "thigh"
    return " OR ".join(terms) or None


def chains_indexed(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT DISTINCT chain FROM chain_products")}


def shortlist(conn: sqlite3.Connection, chain: str, words: str, paid: float | None) -> list[dict]:
    query = _fts_query(words)
    if not query:
        return []
    rows = [dict(r) for r in conn.execute(
        """SELECT cp.*, bm25(chain_products_fts) AS text_rank FROM chain_products_fts
           JOIN chain_products cp ON cp.id = chain_products_fts.rowid
           WHERE chain_products_fts MATCH ? AND cp.chain = ? ORDER BY text_rank LIMIT 400""", (query, chain))]
    if not rows:
        return []
    best, worst = rows[0]["text_rank"], rows[-1]["text_rank"]
    stems = {w.rstrip("s") for w in norm(words).split()}
    for r in rows:
        r["text_score"] = (r["text_rank"] - best) / (worst - best or 1)  # 0 best, 1 worst
        if len(stems) == 1 and norm(r["name"]).split()[-1].rstrip("s") in stems:
            r["text_score"] -= 0.5  # "eggs" is more likely "Free Range Eggs" than "Egg Poacher"
        r["price_gap"] = abs(math.log(paid / r["price"])) if paid and r["price"] else 0.0
    if paid:
        in_band = [r for r in rows if r["price"] and PRICE_BAND[0] <= paid / r["price"] <= PRICE_BAND[1]]
        rows = in_band or rows
    rows.sort(key=lambda r: r["text_score"] + 2 * r["price_gap"])
    return rows[:SHORTLIST]


def class_shortlist(conn: sqlite3.Connection, cls: dict, chain: str) -> list[dict]:
    """Products a chain sells that could be this class, best word match first. Words match as prefixes,
    so "tea" finds "Teabags". A branded class keeps only that brand. An own-label class puts own label
    first but keeps the rest, because the Kaggle flag misses sub-brands (Cowbelle is Aldi, flagged as not own)."""
    words = {w for w in norm(f"{cls['name']} {cls['generic'].replace('-', ' ')}").split() if len(w) >= 3 and not w.isdigit()}
    if not words:
        return []
    rows = [dict(r) for r in conn.execute(
        """SELECT cp.* FROM chain_products_fts JOIN chain_products cp ON cp.id = chain_products_fts.rowid
           WHERE chain_products_fts MATCH ? AND cp.chain = ? ORDER BY bm25(chain_products_fts) LIMIT 1000""",
        (" OR ".join(f'"{w}"*' for w in sorted(words)), chain))]
    if cls["brand"] == "own":
        for r in rows:
            r["own_brand"] = int(bool(r["own_brand"] or own_label_chain({"brands": r["name"]}) == chain))
        rows.sort(key=lambda r: not r["own_brand"])  # stable: word order kept inside each group
    else:
        brand = norm(cls["brand"]).replace(" ", "")
        rows = [r for r in rows if brand in norm(r["name"]).replace(" ", "")]
    return rows[:SHORTLIST]


def remembered(conn: sqlite3.Connection, chain: str, raw: str, paid: float) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT cp.*, SUM(m.confirmations) AS confirmations FROM line_memory m
           JOIN chain_products cp ON cp.id = m.chain_product_id
           WHERE m.chain = ? AND m.raw_norm = ? AND ABS(m.unit_price - ?) <= ?
           GROUP BY cp.id ORDER BY confirmations DESC""", (chain, norm(raw), paid, MEMORY_TOLERANCE))]


def remember(conn: sqlite3.Connection, chain: str, raw: str, paid: float, chain_product_id: int, day: str) -> None:
    conn.execute(
        """INSERT INTO line_memory (chain, raw_norm, unit_price, chain_product_id, confirmations, last_on)
           VALUES (?,?,?,?,1,?) ON CONFLICT DO UPDATE SET confirmations = confirmations + 1, last_on = excluded.last_on""",
        (chain, norm(raw), round(paid, 2), chain_product_id, day))


def _option(r: dict) -> dict:
    out = {k: r[k] for k in ("id", "name", "price", "seen_on", "own_brand")}
    if "confirmations" in r:
        out["confirmations"] = r["confirmations"]
    return out


def run(conn: sqlite3.Connection, chain: str | None, lines: list[dict], use_ai: bool) -> list[str]:
    """Adds a "match" dict to every line. Returns warnings to show the shopper."""
    if not chain or chain not in chains_indexed(conn):
        for l in lines:
            l["match"] = {"status": "no_index", "options": [], "picked": None, "by": None,
                          "note": f"No product list for {chain or 'this shop'} yet, so exact products cannot be named."}
        return []
    warnings, to_ai = [], []
    for i, l in enumerate(lines):
        memory = remembered(conn, chain, l["raw_text"], l["unit_price"])
        if memory:
            top = memory[0]
            l["match"] = {"status": "ask", "options": [_option(r) for r in memory[:4]], "picked": top["id"],
                          "by": "community",
                          "note": f"Confirmed by {top['confirmations']} shopper{'s' if top['confirmations'] > 1 else ''} "
                                  f"at {chain} for this line at this price."}
            continue
        candidates = shortlist(conn, chain, l.get("search_terms") or l["raw_text"], l["unit_price"])
        if not candidates:
            l["match"] = {"status": "none", "options": [], "picked": None, "by": "search",
                          "note": f"No {chain} product shares a word with this line."}
            continue
        l["_candidates"] = candidates
        to_ai.append(i)
    if to_ai and use_ai:
        try:
            picks = ai.pick_products(chain, [(i, lines[i]) for i in to_ai])
        except ai.AIUnavailable as e:
            warnings.append(f"AI could not pick exact products ({e}). Showing the closest name matches instead.")
            picks = {}
    else:
        picks = {}
    for i in to_ai:
        l = lines[i]
        candidates = {c["id"]: c for c in l.pop("_candidates")}
        pick = picks.get(i)
        if pick:
            ids = [c for c in pick.candidate_ids if c in candidates][:4]
            status = pick.status if ids or pick.status == "none" else "none"
            if status == "exact" and len(ids) != 1:
                status = "ask"
            l["match"] = {"status": status, "options": [_option(candidates[c]) for c in ids],
                          "picked": ids[0] if status == "exact" else None, "by": "ai", "note": pick.reason}
        else:
            top = list(candidates.values())[:3]
            l["match"] = {"status": "ask", "options": [_option(c) for c in top], "picked": None, "by": "baseline",
                          "note": "Closest name and price matches, not checked by AI."}
    return warnings

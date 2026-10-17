"""Shortlists of the exact products a chain sells (Kaggle index), found by word search.

Used by shelf labels (app/labels.py), to find the products a label could be for, and by
scripts/link_classes.py, to find the product that is each class at each chain.
"""

import math
import re
import sqlite3

from .scan import own_label_chain

SHORTLIST = 25
PRICE_BAND = (0.65, 1.7)  # label price / 2024 price. Outside this the product is ruled out.


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
    """paid: the shelf price read from the label, used to rule out and order products."""
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

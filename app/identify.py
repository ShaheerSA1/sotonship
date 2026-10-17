"""Shortlists of the exact products a chain sells (Kaggle index), found by word search.

Used by shelf labels (app/labels.py), to find the products a label could be for, and by
scripts/link_classes.py, to find the product that is each class at each chain.
"""

import math
import re
import sqlite3

from . import classes
from .scan import own_label_chain, own_label_tier

SHORTLIST = 25
OWN_TIERS = ("value", "own", "premium")  # class brands that mean supermarket own label
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
    return [{**r, "size": classes.pack_size(r)} for r in rows[:SHORTLIST]]


def class_shortlist(conn: sqlite3.Connection, cls: dict, chain: str) -> list[dict]:
    """Products a chain sells that could be this class, best word match first. Words match as prefixes,
    so "tea" finds "Teabags". A branded class keeps only that brand. An own-label class ("value", "own" or
    "premium") puts own label of the same tier first but keeps the rest, because the Kaggle flag misses
    sub-brands (Cowbelle is Aldi, flagged as not own)."""
    words = {w for w in norm(f"{cls['name']} {cls['generic'].replace('-', ' ')}").split() if len(w) >= 3 and not w.isdigit()}
    if not words:
        return []
    rows = [dict(r) for r in conn.execute(
        """SELECT cp.* FROM chain_products_fts JOIN chain_products cp ON cp.id = chain_products_fts.rowid
           WHERE chain_products_fts MATCH ? AND cp.chain = ? ORDER BY bm25(chain_products_fts) LIMIT 1000""",
        (" OR ".join(f'"{w}"*' for w in sorted(words)), chain))]
    if cls["brand"] in OWN_TIERS:
        for r in rows:
            r["own_brand"] = int(bool(r["own_brand"] or own_label_chain({"brands": r["name"]}) == chain))
        # stable: word order kept inside each group
        rows.sort(key=lambda r: not (r["own_brand"] and own_label_tier(r["name"]) == cls["brand"]))
    else:
        brand = norm(cls["brand"]).replace(" ", "")
        rows = [r for r in rows if brand in norm(r["name"]).replace(" ", "")]
    return [{**r, "size": classes.pack_size(r)} for r in rows[:SHORTLIST]]


def size_fits(cls: dict, size: str) -> bool:
    """size: the product's name, or its pack size worked out from the unit price (classes.pack_size)."""
    mine, theirs = classes.parse_size(cls["size"] + " " + cls["name"]), classes.parse_size(size)
    if "count" in mine and len(mine) > 1 and "count" not in theirs:
        return False  # a 6 x 25g multipack is not one 150g bag
    return not (set(mine) & set(theirs)) or classes.size_close(mine, theirs)


def rules_link(cls: dict, shortlist: list[dict]) -> tuple[dict | None, str]:
    """Rules pick for a class at one chain, used without an API key: first word match of the same tier and size."""
    want = classes.parse_size(cls["size"] + " " + cls["name"])
    for c in shortlist:
        if cls["brand"] in OWN_TIERS and (not c["own_brand"] or own_label_tier(c["name"]) != cls["brand"]):
            continue
        have = classes.parse_size(c["size"])
        if set(want) & set(have) and classes.size_close(want, have):
            return c, "First word match with the same tier and size (rules, no AI)."
    return None, "No word match with the same tier and size (rules, no AI)."

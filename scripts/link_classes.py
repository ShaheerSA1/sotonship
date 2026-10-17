"""Link each catalogue class to the product each chain sells, so every class starts with a price.

The Kaggle set (scripts/fetch_kaggle.py) has 2024 online prices for Asda, Aldi, Morrisons, Sainsbury's
and Tesco. For each class and chain, a word search shortlists that chain's products and the AI picks
the one that is the class (same variant, tier and size within 10%), or none. Own label tiers are kept
apart: a "value" class links only a value range product, an "own" class only standard own label. A pick
whose size we can read and that differs by more than 10% is dropped. Without an API key, simple rules pick
instead (first shortlist product of the same tier with a matching size) and every link says so.

Run: .venv/bin/python scripts/link_classes.py [--only CHAIN]  (--only redoes one chain, keeps the rest of the file)
Writes data/kaggle/class_links.json (committed, so the app needs no AI to load it). Check the links
there: a wrong link shows shoppers a wrong starting price. Set "by" to "team" on links you checked.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import ai, db, identify  # noqa: E402

OUT = db.DATA / "kaggle" / "class_links.json"
BATCH = 20  # classes per AI call


def main() -> None:
    conn = db.connect()
    db.init(conn)
    catalogue = [c for c in db.catalogue(conn) if c.get("origin", "catalogue") == "catalogue"]
    chains = sorted(identify.chains_indexed(conn))
    use_ai = ai.key_set()
    links, dropped = [], []
    if "--only" in sys.argv:
        chains = [sys.argv[sys.argv.index("--only") + 1]]
        links = [l for l in json.loads(OUT.read_text())["links"] if l["chain"] not in chains]
    for chain in chains:
        items = [(cls, identify.class_shortlist(conn, cls, chain)) for cls in catalogue]
        by_id = {c["id"]: c for _, sl in items for c in sl}
        shortlists = {cls["id"]: {c["id"] for c in sl} for cls, sl in items}
        if use_ai:  # in batches, or the answer for 70+ classes gets cut off
            answers = {l.class_id: l for i in range(0, len(items), BATCH)
                       for l in ai.link_classes(chain, items[i:i + BATCH])}
        for cls, shortlist in items:
            if use_ai:
                a = answers.get(cls["id"])
                pick = by_id.get(a.chain_product_id) if a and a.chain_product_id in shortlists[cls["id"]] else None
                reason, by = (a.reason if a else "No answer from the AI."), "ai"
                if pick and not identify.size_fits(cls, pick["size"]):
                    dropped.append(f"{chain}: {cls['id']} -> {pick['name']} (size differs by more than 10%)")
                    pick = None
            else:
                (pick, reason), by = identify.rules_link(cls, shortlist), "rules"
            if pick:
                links.append({"class_id": cls["id"], "chain": chain, "name": pick["name"], "price": pick["price"],
                              "seen_on": pick["seen_on"], "by": by, "reason": reason})
        n = sum(1 for l in links if l["chain"] == chain)
        print(f"{chain}: {n} of {len(catalogue)} classes linked")
    OUT.write_text(json.dumps({
        "note": "Which Kaggle product (data/kaggle/products.csv.gz) is each catalogue class at each chain. Its 2024 "
                "online price is the class's starting price there. Built by scripts/link_classes.py: a word search "
                "shortlists, then the AI picks (by: ai) or simple rules do (by: rules). Not yet checked by the team "
                "unless by: team.",
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": ai.MODEL if use_ai else None, "links": links}, indent=1))
    for d in dropped:
        print("dropped:", d)
    print(f"{len(links)} links -> {OUT}")


if __name__ == "__main__":
    main()

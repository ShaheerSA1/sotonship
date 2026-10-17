"""Give a class to every product with shelf label prices saved before label scans made classes.

Same as saving a new label (app/classes.py assign_chain_product): AI, or simple rules without a key.
Run once after deploying: .venv/bin/python scripts/classify_labels.py
On Fly: fly ssh console -C "python scripts/classify_labels.py"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import classes, db  # noqa: E402

conn = db.connect()
db.init(conn)
rows = conn.execute("""SELECT DISTINCT cp.* FROM observations o JOIN chain_products cp ON cp.id = o.chain_product_id
                       WHERE o.product_id IS NULL""").fetchall()
print(f"{len(rows)} label products without a class")
for cp in rows:
    class_id, note, warnings = classes.assign_chain_product(conn, cp)
    conn.commit()
    print(f"{cp['chain']} | {cp['name']} -> {class_id or 'none'}. {note or ''} {' '.join(warnings)}".strip())

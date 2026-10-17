"""Link every class a scan started to the same product at the other chains, where it has no link yet.

New classes are linked in the background when they are saved (app/classes.py link_other_chains). This
runs the same step once for classes made before that existed, so their starting prices show up.

Run: .venv/bin/python scripts/link_scanned.py   (on Fly: fly ssh console -C "python scripts/link_scanned.py")
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import classes, db  # noqa: E402


def main() -> None:
    conn = db.connect()
    db.init(conn)
    for row in conn.execute("SELECT id, name FROM products WHERE origin = 'scan' ORDER BY id").fetchall():
        print(f"{row['id']} ({row['name']})")
        for line in classes.link_other_chains(conn, row["id"]) or ["  already linked at every chain"]:
            print("  " + line)


if __name__ == "__main__":
    main()

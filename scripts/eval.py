"""Compare the AI against the baseline on the held-out SYNTHETIC test sets.

Task 1, receipt line mapping: does each receipt line map to the right catalogue product
(or correctly to nothing)? Test lines are grouped into one receipt per chain and sent
through the same parse path the app uses.

Task 2, list matching: does each shopping list item map to the right product group,
with the right brand restriction, or get correctly flagged ambiguous / not tracked?

Task 3, exact product: from a receipt line and the price paid, is the exact product the
shopper bought among the options offered (or picked outright)? Also counts confident wrong
picks, the error that matters most, and how many questions the shopper is asked.
Community memory is switched off so only the parser and matcher are measured.

Task 4, product class: is a scanned product put in the right class shared across chains (Tesco
and Aldi hazelnut spread 400g together), or correctly left out when no class fits? Real Open Food
Facts products. Classes are the catalogue plus classes started by an earlier scan. Counts wrong
merges (two different products priced as one, the costly error) and missed matches.

Run: .venv/bin/python scripts/eval.py            (baseline only if no API key)
Writes results to data/eval/results.json.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import ai, baseline, classes, db, identify  # noqa: E402


EVAL = db.DATA / "eval"


def receipt_text(chain: str, lines: list[dict]) -> str:
    body = "\n".join(f"{l['raw']:<36}{1.00 + i * 0.10:>6.2f}" for i, l in enumerate(lines))
    return f"*** SYNTHETIC TEST RECEIPT ***\n{chain}\nSouthampton\n\n{body}\n"


def align(expected: list[dict], parsed: list[dict]) -> list[str | None]:
    """For each expected line, the product_id the parser gave the closest raw_text, or None if skipped."""
    out = []
    for e in expected:
        best, score = None, 0.0
        for p in parsed:
            s = SequenceMatcher(None, e["raw"].lower(), p["raw_text"].lower()).ratio()
            if s > score:
                best, score = p, s
        out.append(best["product_id"] if best and score > 0.6 else None)
    return out


def eval_receipts(use_ai: bool, catalogue: list[dict]) -> dict:
    lines = json.loads((EVAL / "receipt_lines_test.json").read_text())["lines"]
    by_chain = defaultdict(list)
    for l in lines:
        by_chain[l["chain"]].append(l)
    correct, errors = 0, []
    for chain, group in by_chain.items():
        text = receipt_text(chain, group)
        if use_ai:
            parsed = [l.model_dump() for l in ai.parse_receipt(text.encode(), "text/plain", catalogue).lines]
        else:
            parsed = baseline.parse_receipt_text(text, catalogue)["lines"]
        for e, got in zip(group, align(group, parsed)):
            if got == e["product_id"]:
                correct += 1
            else:
                errors.append({"raw": e["raw"], "expected": e["product_id"], "got": got})
    return {"n": len(lines), "correct": correct, "accuracy": round(correct / len(lines), 3), "errors": errors}


def item_ok(e: dict, got: dict, catalogue: list[dict]) -> bool:
    if got["status"] not in e["status"]:
        return False
    if got["status"] != "matched":
        return True
    groups = {p["generic"] for p in catalogue if p["id"] in got["product_ids"]}
    if groups != {e["generic"]}:
        return False
    brands = {p["brand"] for p in catalogue if p["id"] in got["product_ids"]}
    all_brands = {p["brand"] for p in catalogue if p["generic"] == e["generic"]}
    if e["brand"] == "any":
        return True
    if e["brand"] is None:
        return brands == all_brands  # no brand named: every brand in the group must be allowed
    return brands == {e["brand"]}


def eval_list(use_ai: bool, catalogue: list[dict]) -> dict:
    items = json.loads((EVAL / "list_items_test.json").read_text())["items"]
    correct, errors = 0, []
    for e in items:
        got = (ai.match_list(e["text"], catalogue) if use_ai else baseline.match_list([e["text"]], catalogue))
        got = got[0] if got else {"status": "none", "product_ids": []}
        if item_ok(e, got, catalogue):
            correct += 1
        else:
            errors.append({"text": e["text"], "expected": {k: e[k] for k in ("status", "generic", "brand")},
                           "got": {k: got.get(k) for k in ("status", "generic", "brand", "product_ids")}})
    return {"n": len(items), "correct": correct, "accuracy": round(correct / len(items), 3), "errors": errors}


def eval_exact(use_ai: bool, conn, catalogue: list[dict]) -> dict:
    lines = json.loads((EVAL / "exact_lines_test.json").read_text())["lines"]
    names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM chain_products")}
    by_chain = defaultdict(list)
    for l in lines:
        by_chain[l["chain"]].append(l)
    found = top1 = confident_wrong = asked = 0
    errors = []
    for chain, group in by_chain.items():
        body = "\n".join(f"{l['raw']:<36}{l['paid']:>6.2f}" for l in group)
        text = f"*** SYNTHETIC TEST RECEIPT ***\n{chain.upper()}\nSouthampton\n\n{body}\n"
        if use_ai:
            receipt = ai.parse_receipt(text.encode(), "text/plain", catalogue).model_dump()
        else:
            receipt = baseline.parse_receipt_text(text, catalogue)
        identify.run(conn, chain, receipt["lines"], use_ai=use_ai)
        for e in group:
            best, score = None, 0.0
            for p in receipt["lines"]:
                s = SequenceMatcher(None, e["raw"].lower(), p["raw_text"].lower()).ratio()
                if s > score:
                    best, score = p, s
            m = best["match"] if best and score > 0.6 else {"status": "none", "options": [], "picked": None}
            offered = [names[o["id"]] for o in m["options"]]
            first = names.get(m["picked"]) or (offered[0] if offered else None)
            ok = (e["answer"] in offered) if e["answer"] else not offered
            found += ok
            top1 += first == e["answer"]
            asked += m["status"] == "ask"
            wrong = m["status"] == "exact" and first != e["answer"]
            confident_wrong += wrong
            if not ok or wrong:
                errors.append({"chain": chain, "raw": e["raw"], "expected": e["answer"], "status": m["status"],
                               "offered": offered})
    n = len(lines)
    return {"n": n, "correct": found, "accuracy": round(found / n, 3), "top1": round(top1 / n, 3),
            "confident_wrong": confident_wrong, "questions_asked": asked, "errors": errors}


def off_shape(p: dict) -> dict:
    return {"product_name": p["name"], "brands": p["brand"], "quantity": p["quantity"],
            "categories_tags": p["categories_tags"]}


def eval_classes(use_ai: bool, catalogue: list[dict]) -> dict:
    data = json.loads((EVAL / "class_match_test.json").read_text())
    pool = [{**c, "members": []} for c in catalogue if c.get("origin", "catalogue") == "catalogue"]
    for c in data["classes"]:
        pool.append({k: c[k] for k in ("id", "name", "brand", "size", "generic")} |
                    {"members": [classes.snapshot(off_shape(c["seed"]))]})
    match = (lambda p: classes.ai_match(p, pool)) if use_ai else (lambda p: classes.baseline_match(p, pool))
    with ThreadPoolExecutor(8) as ex:
        got = list(ex.map(match, [off_shape(i["product"]) for i in data["items"]]))
    correct = wrong_merge = missed = 0
    errors = []
    for item, g in zip(data["items"], got):
        said = g["class_id"] if g["status"] == "same" else None
        ok = said == item["answer"]
        correct += ok
        wrong_merge += said is not None and not ok
        missed += item["answer"] is not None and said is None
        if not ok:
            errors.append({"product": f"{item['product']['brand']} | {item['product']['name']} | {item['product']['quantity']}",
                           "expected": item["answer"], "status": g["status"], "got": g["class_id"], "reason": g["reason"]})
    n = len(data["items"])
    return {"n": n, "with_class": sum(1 for i in data["items"] if i["answer"]), "correct": correct,
            "accuracy": round(correct / n, 3), "wrong_merges": wrong_merge, "missed": missed, "errors": errors}


def main() -> None:

    conn = db.connect()
    db.init(conn)
    catalogue = db.catalogue(conn)
    identify.remembered = lambda *a: []  # measure the matcher, not what shoppers taught it
    results = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": ai.MODEL,
               "baseline": {"receipt_lines": eval_receipts(False, catalogue), "list_items": eval_list(False, catalogue),
                            "exact_product": eval_exact(False, conn, catalogue),
                            "product_class": eval_classes(False, catalogue)}}
    try:
        results["ai"] = {"receipt_lines": eval_receipts(True, catalogue), "list_items": eval_list(True, catalogue),
                         "exact_product": eval_exact(True, conn, catalogue),
                         "product_class": eval_classes(True, catalogue)}
    except ai.AIUnavailable as e:
        results["ai"] = {"skipped": str(e)}
    (EVAL / "results.json").write_text(json.dumps(results, indent=1))
    print(f"{'task':<16}{'n':>4}{'baseline':>10}{'ai':>10}")
    for task in ("receipt_lines", "list_items", "exact_product", "product_class"):
        b = results["baseline"][task]
        a = results["ai"].get(task)
        ai_acc = f"{a['accuracy']:.1%}" if a else "skipped"
        print(f"{task:<16}{b['n']:>4}{b['accuracy']:>10.1%}{ai_acc:>10}")
    for name, r in (("baseline", results["baseline"]), ("ai", results["ai"])):
        x = r.get("exact_product")
        if x:
            print(f"exact_product {name}: answer offered {x['correct']}/{x['n']}, first option right {x['top1']:.1%}, "
                  f"confident wrong {x['confident_wrong']}, questions asked {x['questions_asked']}")
    for name, r in (("baseline", results["baseline"]), ("ai", results["ai"])):
        x = r.get("product_class")
        if x:
            print(f"product_class {name}: right {x['correct']}/{x['n']}, wrong merges {x['wrong_merges']}, "
                  f"missed matches {x['missed']} of {x['with_class']}")
    if "skipped" in results["ai"]:
        print("AI skipped:", results["ai"]["skipped"])
    print("Details: data/eval/results.json")


if __name__ == "__main__":
    main()

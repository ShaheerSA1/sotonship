"""Compare the AI against the baseline on the held-out test sets.

Task 1, list matching: does each shopping list item map to the right product group,
with the right brand restriction, or get correctly flagged ambiguous / not tracked?

Task 2, product class: is a scanned product put in the right class shared across chains (Tesco
and Aldi hazelnut spread 400g together), or correctly left out when no class fits? Real Open Food
Facts products. Classes are the catalogue plus classes started by an earlier scan. Counts wrong
merges (two different products priced as one, the costly error) and missed matches.

Task 3, shelf label: from a photo of a shelf label (SYNTHETIC, rendered by scripts/make_labels.py), are the
prices read right (shelf, member, multibuy, was, offer end date) and is the exact product among the options
offered? The baseline gets the label's text as if typed perfectly, then regexes and word search: it cannot read
photos at all, so this flatters it. The AI gets only the photo.

Run: .venv/bin/python scripts/eval.py            (baseline only if no API key)
Writes results to data/eval/results.json. The model is MODEL in .env (default claude-haiku-5-5).
A run without a key keeps the last AI results under "ai_previous", marked with their model and date.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import ai, baseline, classes, db, labels  # noqa: E402


EVAL = db.DATA / "eval"


def item_ok(e: dict, got: dict, catalogue: list[dict]) -> bool:
    if got["status"] not in e["status"]:
        return False
    if got["status"] != "matched":
        return True
    want = set(e["generic"]) if isinstance(e["generic"], list) else {e["generic"]}  # a list: a vague item spans groups
    groups = {p["generic"] for p in catalogue if p["id"] in got["product_ids"]}
    if groups != want:
        return False
    brands = {p["brand"] for p in catalogue if p["id"] in got["product_ids"]}
    all_brands = {p["brand"] for p in catalogue if p["generic"] in want}
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


def off_shape(p: dict) -> dict:
    return {"product_name": p["name"], "brands": p["brand"], "quantity": p["quantity"],
            "categories_tags": p["categories_tags"]}


def eval_classes(use_ai: bool, catalogue: list[dict]) -> dict:
    data = json.loads((EVAL / "class_match_test.json").read_text())
    pool = [{**c, "members": []} for c in catalogue if c.get("origin", "catalogue") == "catalogue"]
    for c in data["classes"]:
        pool.append({k: c[k] for k in ("id", "name", "brand", "size", "generic")} |
                    {"members": [classes.snapshot(off_shape(c["seed"]))]})
    def match(p: dict) -> dict:
        if not use_ai:
            return classes.baseline_match(p, pool)
        try:
            return classes.ai_match(p, pool)
        except ai.AIUnavailable as e:  # counted wrong and reported, never replaced by the baseline
            return {"status": "failed", "class_id": None, "reason": str(e)}
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
            "accuracy": round(correct / n, 3), "wrong_merges": wrong_merge, "missed": missed,
            "ai_failures": sum(1 for g in got if g["status"] == "failed"), "errors": errors}


LABEL_FIELDS = ("shelf_price", "loyalty_price", "was_price", "multibuy", "valid_until")


def field_ok(field: str, truth: dict, got: dict) -> bool:
    if field == "multibuy":
        return (truth["multibuy_qty"], truth["multibuy_price"]) == (got.get("multibuy_qty"), got.get("multibuy_price"))
    a, b = truth[field], got.get(field)
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(a - b) < 0.005
    return a == b


def eval_labels(use_ai: bool, conn) -> dict:
    data = json.loads((EVAL / "label_test.json").read_text())
    names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM chain_products")}
    def run(item: dict) -> tuple[dict | None, dict, str | None]:
        conn = db.connect()  # one connection per worker thread: sqlite3 connections are not shared safely
        if not use_ai:
            label = baseline.read_label_text("\n".join(item["printed"]), date.fromisoformat(data["today"]))
            return label, labels.match(conn, item["chain"], label, use_ai=False)[0], None
        try:
            label = ai.read_label((EVAL / item["image"]).read_bytes(), "image/jpeg", data["today"]).model_dump()
            m, warnings = labels.match(conn, item["chain"], label, use_ai=True)
            if warnings:  # the match fell back to word search: not an AI result
                raise ai.AIUnavailable("; ".join(warnings))
            return label, m, None
        except ai.AIUnavailable as e:  # counted wrong and reported, never replaced by the baseline
            return None, {"status": "failed", "options": [], "picked": None}, str(e)
    with ThreadPoolExecutor(8) as ex:
        got = list(ex.map(run, data["items"]))
    fields = {f: 0 for f in LABEL_FIELDS}
    found = top1 = confident_wrong = asked = all_prices = failures = 0
    errors = []
    for item, (label, m, failed) in zip(data["items"], got):
        failures += failed is not None
        offered = [names[o["id"]] for o in m["options"]]
        first = names.get(m["picked"]) or (offered[0] if offered else None)
        ok = (item["answer"] in offered) if item["answer"] else not offered or m["status"] == "none"
        right = {f: bool(label) and field_ok(f, item["truth"], label) for f in LABEL_FIELDS}
        for f in LABEL_FIELDS:
            fields[f] += right[f]
        all_prices += all(right.values())
        found += ok
        top1 += first == item["answer"] if item["answer"] else m["status"] == "none" or not offered
        asked += m["status"] == "ask"
        wrong = m["status"] == "exact" and first != item["answer"]
        confident_wrong += wrong
        if not ok or wrong or not all(right.values()):
            errors.append({"id": item["id"], "expected": item["answer"], "status": m["status"], "offered": offered,
                           "fields_wrong": {f: {"truth": item["truth"].get(f) if f != "multibuy" else
                                                [item["truth"]["multibuy_qty"], item["truth"]["multibuy_price"]],
                                                "got": (label or {}).get(f) if f != "multibuy" else
                                                [(label or {}).get("multibuy_qty"), (label or {}).get("multibuy_price")]}
                                            for f in LABEL_FIELDS if not right[f]}, "failed": failed})
    n = len(data["items"])
    return {"n": n, "not_in_list": sum(1 for i in data["items"] if not i["answer"]), "correct": found,
            "accuracy": round(found / n, 3), "top1": round(top1 / n, 3), "confident_wrong": confident_wrong,
            "questions_asked": asked, "all_prices_right": all_prices,
            "fields": {f: round(v / n, 3) for f, v in fields.items()}, "ai_failures": failures, "errors": errors}


def main() -> None:

    conn = db.connect()
    db.init(conn)
    catalogue = db.catalogue(conn)
    results = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": ai.MODEL,
               "baseline": {"list_items": eval_list(False, catalogue),
                            "product_class": eval_classes(False, catalogue),
                            "shelf_label": eval_labels(False, conn)}}
    results["ai"] = {}
    if not ai.key_set():
        results["ai"]["skipped"] = "No ANTHROPIC_API_KEY in .env."
        old = json.loads((EVAL / "results.json").read_text()) if (EVAL / "results.json").exists() else {}
        prev = old.get("ai_previous") if "skipped" in old.get("ai", {}) else             {"model": old.get("model"), "run_at": old.get("run_at"), **old.get("ai", {})} if old.get("ai") else None
        if prev:
            results["ai_previous"] = {k: v for k, v in prev.items() if k in ("model", "run_at", *results["baseline"])}
    else:
        tasks = {"list_items": lambda: eval_list(True, catalogue),
                 "product_class": lambda: eval_classes(True, catalogue),
                 "shelf_label": lambda: eval_labels(True, conn)}
        for task, run in tasks.items():  # one failed task must not lose the others
            try:
                results["ai"][task] = run()
            except ai.AIUnavailable as e:
                results["ai"].setdefault("failed", {})[task] = str(e)
    (EVAL / "results.json").write_text(json.dumps(results, indent=1))
    print(f"{'task':<16}{'n':>4}{'baseline':>10}{'ai':>10}")
    for task in ("list_items", "product_class", "shelf_label"):
        b = results["baseline"][task]
        a = results["ai"].get(task)
        ai_acc = f"{a['accuracy']:.1%}" if a else "skipped"
        print(f"{task:<16}{b['n']:>4}{b['accuracy']:>10.1%}{ai_acc:>10}")
    for name, r in (("baseline", results["baseline"]), ("ai", results["ai"])):
        x = r.get("product_class")
        if x:
            print(f"product_class {name}: right {x['correct']}/{x['n']}, wrong merges {x['wrong_merges']}, "
                  f"missed matches {x['missed']} of {x['with_class']}")
            if x.get("ai_failures"):
                print(f"product_class {name}: {x['ai_failures']} AI calls failed and count as wrong. Rerun.")
    for name, r in (("baseline", results["baseline"]), ("ai", results["ai"])):
        x = r.get("shelf_label")
        if x:
            print(f"shelf_label {name}: product offered {x['correct']}/{x['n']}, first option right {x['top1']:.1%}, "
                  f"confident wrong {x['confident_wrong']}, questions asked {x['questions_asked']}, "
                  f"every price right {x['all_prices_right']}/{x['n']}, fields {x['fields']}")
            if x.get("ai_failures"):
                print(f"shelf_label {name}: {x['ai_failures']} AI calls failed and count as wrong. Rerun.")
    if "skipped" in results["ai"]:
        print("AI skipped:", results["ai"]["skipped"])
        if "ai_previous" in results:
            print(f"Kept the last AI results ({results['ai_previous']['model']}, {results['ai_previous']['run_at']}) "
                  "under ai_previous.")
    for task, why in results["ai"].get("failed", {}).items():
        print(f"AI {task} failed: {why}")
    print("Details: data/eval/results.json")


if __name__ == "__main__":
    main()

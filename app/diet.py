"""Allergy and diet filtering. Plain rules, never AI: a missed allergen is too costly to leave to a model.

Tags come from data/catalogue.json ('contains', 'may_contain'). They are typical for the product
type, not read from each pack, so the UI always tells the user to check the label.
"""

import json

from .db import DATA

# UK Food Information Regulations: the 14 allergens that must be declared
ALLERGENS = {
    "celery": "Celery", "gluten": "Gluten (wheat, rye, barley, oats)", "crustaceans": "Crustaceans",
    "eggs": "Eggs", "fish": "Fish", "lupin": "Lupin", "milk": "Milk", "molluscs": "Molluscs",
    "mustard": "Mustard", "tree-nuts": "Tree nuts", "peanuts": "Peanuts", "sesame": "Sesame",
    "soya": "Soya", "sulphites": "Sulphites",
}
DIETS = {
    "vegetarian": {"label": "Vegetarian", "avoid": {"meat", "fish"}},
    "vegan": {"label": "Vegan", "avoid": {"meat", "fish", "milk", "eggs", "honey"}},
    "pescatarian": {"label": "Pescatarian", "avoid": {"meat"}},
    "halal": {"label": "Halal", "avoid": {"meat"}, "why": "not certified halal (we do not track certified meat yet)"},
    "kosher": {"label": "Kosher", "avoid": {"meat"}, "why": "not certified kosher (we do not track certified meat yet)"},
}
WORD = {"meat": "meat", "fish": "fish", "milk": "milk", "eggs": "eggs", "honey": "honey"}


def _tags() -> dict[str, dict]:
    products = json.loads((DATA / "catalogue.json").read_text())["products"]
    return {p["id"]: {"contains": set(p.get("contains", [])), "may": set(p.get("may_contain", [])),
                      "non_food": p.get("non_food", False)} for p in products}


TAGS = _tags()


def check(product_id: str, allergies: set[str], diets: set[str], strict: bool) -> tuple[list[str], list[str]]:
    """Returns (reasons the product is ruled out, warnings to show). strict: 'may contain' rules it out too."""
    t = TAGS.get(product_id)
    if not t:
        return [], ["no allergen data for this product"]
    if t["non_food"]:
        return [], []
    blocked, warn = [], []
    for a in sorted(allergies):
        name = ALLERGENS.get(a, a).split(" (")[0].lower()
        if a in t["contains"]:
            blocked.append(f"contains {name}")
        elif a in t["may"]:
            (blocked if strict else warn).append(f"may contain {name}")
    for d in sorted(diets):
        rule = DIETS.get(d)
        if not rule:
            continue
        hit = rule["avoid"] & t["contains"]
        if hit:
            blocked.append(rule.get("why") or f"not {rule['label'].lower()} (contains {', '.join(WORD[h] for h in sorted(hit))})")
        elif rule["avoid"] & t["may"]:
            warn.append(f"may contain {', '.join(sorted(rule['avoid'] & t['may']))}, check if {rule['label'].lower()}")
    return blocked, warn


def apply(items: list[dict], catalogue: list[dict], allergies: set[str], diets: set[str], strict: bool) -> list[dict]:
    """Drop products that clash with the profile. An item left with no products becomes 'blocked'."""
    if not allergies and not diets:
        return items
    names = {p["id"]: p["name"] for p in catalogue}
    out = []
    for item in items:
        if item["status"] != "matched":
            out.append(item)
            continue
        kept, removed, warnings = [], [], set()
        for pid in item["product_ids"]:
            blocked, warn = check(pid, allergies, diets, strict)
            if blocked:
                removed.append(f"{names.get(pid, pid)}: {', '.join(blocked)}")
            else:
                kept.append(pid)
                warnings.update(warn)
        # a swap is a product the shopper did not name: only one with nothing to block or warn about
        swaps = [pid for pid in item.get("swap_ids", []) if check(pid, allergies, diets, strict) == ([], [])]
        item = {**item, "product_ids": kept, "swap_ids": swaps, "diet_removed": removed,
                "diet_warnings": sorted(warnings)}
        if not kept:
            item["status"] = "blocked"
            item["note"] = "Ruled out by your profile. " + "; ".join(removed)
        out.append(item)
    return out

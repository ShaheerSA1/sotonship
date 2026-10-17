"""Map an Open Food Facts product to a catalogue id. Rules, not AI.

Used by scripts/fetch_off.py for Open Prices and by the barcode scan in app/scan.py.
"""

import re

from .scan import own_label_tier

# catalogue id -> (category tags, any one is enough; brand regex; size regex or None)
# Own-label products are judged on the brands field alone, so "Twinings Everyday" is not own label.
OWN = r"tesco|sainsbury|asda|lidl|aldi|morrisons|co-?op|m&s|marks|iceland|everyday|just essentials|" \
      r"hearty food|stockwell|by sainsbury|nature's pick|milbona|crownfield|baresa|specially selected|" \
      r"deluxe|savers|cucina|harvest morn|snackrite|dairyfine|cowbelle|alesto|freshona|four seasons|" \
      r"ocean rise|the fishmonger|millville|grower's harvest|bramwells|newgate|chef select|vitasia|" \
      r"tower gate|corale|kania|w5|cien|nightingale|simply|smart price|honest value"
MAP = {
    "bananas-5pk-own": (["en:bananas"], OWN, None),
    "apples-6pk-own": (["en:apples"], OWN, r"\b6\b"),
    "onions-1kg-own": (["en:onions"], OWN, r"1\s?kg"),
    "carrots-1kg-own": (["en:carrots"], OWN, r"1\s?kg"),
    "potatoes-2.5kg-own": (["en:potatoes"], OWN, r"2[.,]5\s?kg"),
    "tomatoes-chopped-400g-own": (["en:chopped-tomatoes"], OWN, r"400\s?g"),
    "milk-semi-4pt-own": (["en:semi-skimmed-milks", "en:semi-skimmed-pasteurised-milk"], OWN, r"2[.,]27|4\s?p(in)?ts?\b|2272"),
    "eggs-free-range-6-own": (["en:eggs"], OWN, r"\b6\b"),
    "butter-salted-250g-own": (["en:salted-butters"], OWN, r"250\s?g"),
    "butter-anchor-250g": (["en:butters"], r"anchor", r"250\s?g"),
    "cheddar-mature-400g-own": (["en:cheddar-cheese"], OWN, r"400\s?g"),
    "cheddar-cathedral-350g": (["en:cheddar-cheese"], r"cathedral", r"350\s?g"),
    "yoghurt-greek-500g-own": (["en:greek-style-yogurts"], OWN, r"500\s?g"),
    "bread-white-800g-own": (["en:white-breads"], OWN, r"800\s?g"),
    "bread-warburtons-toastie-800g": (["en:breads"], r"warburtons", r"800\s?g"),
    "chicken-breast-600g-own": (["en:chicken-breasts"], OWN, r"6[05]0\s?g"),
    "beef-mince-5pc-500g-own": (["en:minced-beef-steak-with-5-fat", "en:minced-beef"], OWN, r"500\s?g"),
    "tuna-chunks-brine-145g-own": (["en:tunas"], OWN, r"1[0-4][0-9]\s?g"),
    "pasta-penne-500g-own": (["en:pastas"], OWN, r"500\s?g"),
    "rice-basmati-1kg-own": (["en:basmati-rices"], OWN, r"1\s?kg"),
    "rice-tilda-basmati-1kg": (["en:basmati-rices"], r"tilda", r"1\s?kg"),
    "beans-heinz-415g": (["en:baked-beans-in-tomato-sauce"], r"heinz", r"41[05]\s?g"),
    "beans-own-410g": (["en:baked-beans-in-tomato-sauce"], OWN, r"4[01][05]\s?g"),
    "oats-porridge-1kg-own": (["en:rolled-oats"], OWN, r"1\s?kg"),
    "oats-quaker-1kg": (["en:rolled-oats"], r"quaker", r"1\s?kg"),
    "cornflakes-kelloggs-500g": (["en:corn-flakes"], r"kellogg", r"4[5-9]0\s?g|500\s?g"),
    "cornflakes-own-500g": (["en:corn-flakes"], OWN, r"500\s?g"),
    "noodles-super-chicken-90g": (["en:instant-noodles"], r"batchelors|super ?noodles", r"9[05]\s?g"),
    "pizza-margherita-frozen-own": (["en:frozen-pizzas"], OWN, None),
    "peas-frozen-1kg-own": (["en:frozen-peas"], OWN, r"1\s?kg"),
    "crisps-walkers-sv-6pk": (["en:salt-and-vinegar-crisps", "en:crisps"], r"walkers", r"6\s?x|6 ?pack"),
    "crisps-own-sv-6pk": (["en:salt-and-vinegar-crisps", "en:crisps"], OWN, r"6\s?x|6 ?pack"),
    "crisps-walkers-co-6pk": (["en:cheese-and-onion-crisps"], r"walkers", r"6\s?x|6 ?pack"),
    "crisps-own-co-6pk": (["en:cheese-and-onion-crisps"], OWN, r"6\s?x|6 ?pack"),
    "choc-dairy-milk-110g": (["en:milk-chocolates"], r"cadbury", r"1[01][0-9]\s?g"),
    "cola-coke-2l": (["en:colas"], r"coca|coke", r"2\s?l"),
    "cola-own-2l": (["en:colas"], OWN, r"2\s?l"),
    "oj-smooth-1l-own": (["en:orange-juices"], OWN, r"1\s?l"),
    "tea-pg-80": (["en:black-teas"], r"pg tips", r"\b80\b"),
    "tea-yorkshire-80": (["en:black-teas"], r"yorkshire", r"\b80\b"),
    "tea-own-80": (["en:black-teas"], OWN, r"\b80\b"),
    "coffee-nescafe-gold-200g": (["en:instant-coffees"], r"nescaf", r"200\s?g"),
    "sugar-granulated-1kg-own": (["en:granulated-sugars"], OWN, r"1\s?kg"),
    "peanut-butter-smooth-340g-own": (["en:peanut-butters"], OWN, r"3[0-9]0\s?g"),
    "washing-up-fairy-383ml": (["en:dishwashing-liquids"], r"fairy", r"38[0-9]\s?ml"),
}
# crisps flavour is not a category tag; check the name instead
NAME_RULES = {
    "crisps-walkers-sv-6pk": r"salt.*vinegar|s/vin|s&v",
    "crisps-own-sv-6pk": r"salt.*vinegar|s/vin|s&v",
    "pizza-margherita-frozen-own": r"margh|cheese",
    "tuna-chunks-brine-145g-own": r"brine",
    "pasta-penne-500g-own": r"penne",
    "noodles-super-chicken-90g": r"chicken",
    "beef-mince-5pc-500g-own": r"\b5\s?%|beef mince$|^beef mince",
    "crisps-walkers-co-6pk": r"cheese.*onion",
    "crisps-own-co-6pk": r"cheese.*onion",
}


def map_product(p: dict) -> str | None:
    tags = set(p.get("categories_tags") or [])
    brand = (p.get("brands") or "").lower()
    name = (p.get("product_name") or "").lower()
    size = (p.get("quantity") or "").lower() + " " + name
    for pid, (need, brand_rx, size_rx) in MAP.items():
        if not set(need) & tags:
            continue
        where = brand if brand_rx == OWN else brand + " " + name
        if not re.search(brand_rx, where):
            continue
        if size_rx and not re.search(size_rx, size):
            continue
        if pid in NAME_RULES and not re.search(NAME_RULES[pid], name):
            continue
        if brand_rx == OWN:  # own label: the tier decides which class. No premium classes in the catalogue yet
            tier = own_label_tier(brand + " " + name)
            if tier == "premium":
                return None
            return pid.replace("-own", "-value") if tier == "value" else pid
        return pid
    return None

"""Build the SYNTHETIC shelf label test set: label images with known answers.

Products are real (picked at random from the Kaggle product list, data/kaggle). Everything on the label
apart from the product name is invented: today's price (the 2024 price times 1.00 to 1.25), member prices,
multibuys, was prices and end dates. Six labels are for made-up products launched "after 2024", which are
not in the product list, so the right answer is none. Each image says SYNTHETIC TEST LABEL in a corner.

Labels are drawn plainly in the colours each chain uses for offers (no logos), then photographed badly on
purpose: tilted, blurred, JPEG-compressed, sometimes with a neighbouring label at the edge. Real shelf photos
are harder (glare, angle, worn labels), so treat scores on this set as an upper bound.

The answers are known by construction, nobody labelled them. The label prompts have no examples, so there
is no tuning split.

Run: .venv/bin/pip install pillow && .venv/bin/python scripts/make_labels.py
Writes data/eval/labels/*.jpg and data/eval/label_test.json (both committed: the eval needs no Pillow).
"""

import json
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import classes, db  # noqa: E402

OUT = db.DATA / "eval" / "labels"
TODAY = date(2026, 10, 17)  # fixed so the set does not change with the day it is rebuilt
FONT = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-{}.ttf"
PER_CHAIN = 8
OWN_PREFIX = {"Tesco": "Tesco ", "Sainsbury's": "Sainsbury's ", "Asda": "ASDA ", "Morrisons": "Morrisons "}
# Offer styles per chain: (style, share). Colours are plain fills, no logos.
STYLES = {"Tesco": [("clubcard", 0.4), ("plain", 0.6)], "Sainsbury's": [("nectar", 0.4), ("plain", 0.6)],
          "Asda": [("was", 0.4), ("plain", 0.6)], "Morrisons": [("multibuy", 0.3), ("more", 0.2), ("plain", 0.5)],
          "Aldi": [("was", 0.25), ("plain", 0.75)]}
SCHEME = {"clubcard": "Clubcard", "nectar": "Nectar", "more": "More Card"}
BAND = {"clubcard": ("#ffd400", "#00539f", "Clubcard Price"), "nectar": ("#6c2c91", "#ffffff", "Nectar Prices"),
        "more": ("#00563f", "#ffd400", "More Card Price"), "was": ("#d6001c", "#ffffff", "Price drop"),
        "multibuy": ("#d6001c", "#ffffff", "Offer")}
# Made-up products, not in the 2024 product list
NEW = [("Tesco", "Tesco Pistachio Cream Spread 200g", 2.75), ("Sainsbury's", "Sainsbury's Hot Honey Halloumi Fries 250g", 3.25),
       ("Asda", "ASDA Dubai Style Chocolate Bar 90g", 2.50), ("Morrisons", "Morrisons Ube Overnight Oats 300g", 1.85),
       ("Aldi", "Specially Selected Yuzu Lemonade 750ml", 1.49), ("Tesco", "Tesco Gochujang Crunch Crisps 6x22g", 1.60)]


def price_now(rng: random.Random, old: float) -> float:
    p = old * rng.uniform(1.0, 1.25)
    return round(max(0.25, round(p * 20) / 20 - rng.choice([0, 0.01, 0.05])), 2)


def unit_text(name: str, price: float) -> str | None:
    size = classes.parse_size(name)
    if "mass" in size:
        g = size["mass"]
        return f"£{price / g * 1000:.2f} per kg" if g >= 500 else f"£{price / g * 100:.2f} per 100g"
    if "volume" in size:
        return f"£{price / size['volume'] * 1000:.2f} per litre"
    return None


def label_name(rng: random.Random, chain: str, name: str) -> str:
    """Shelf labels often drop the chain name on own label and print in capitals."""
    out = name
    prefix = OWN_PREFIX.get(chain)
    if prefix and out.startswith(prefix) and rng.random() < 0.4:
        out = out[len(prefix):]
    return out.upper() if rng.random() < 0.35 else out


def end_date(rng: random.Random) -> date:
    return TODAY + timedelta(days=rng.choice([-3, 4, 4, 11, 11, 18, 25])) if rng.random() < 0.9 else TODAY + timedelta(days=32)


def pick_products(conn, rng: random.Random) -> list[tuple[str, str, float]]:
    out = []
    for chain in STYLES:
        rows = [dict(r) for r in conn.execute(
            """SELECT name, price FROM chain_products WHERE chain = ? AND category IN
               ('food_cupboard', 'fresh_food', 'drinks', 'bakery', 'frozen') AND price BETWEEN 0.4 AND 12
               AND length(name) < 54 ORDER BY name""", (chain,))]
        rows = [r for r in rows if classes.parse_size(r["name"])]
        for r in rng.sample(rows, PER_CHAIN):
            out.append((chain, r["name"], r["price"]))
    return out


def make(rng: random.Random, chain: str, name: str, old: float, answer: str | None) -> dict:
    styles, weights = zip(*STYLES[chain])
    style = rng.choices(styles, weights)[0]
    price = price_now(rng, old)
    t = {"shelf_price": price, "was_price": None, "loyalty_price": None, "loyalty_scheme": None, "multibuy_qty": None,
         "multibuy_price": None, "multibuy_members_only": False, "valid_until": None}
    printed = label_name(rng, chain, name)
    band, big, small, ends = None, price, [], None
    if style in SCHEME:
        t["loyalty_price"] = big = round(price * rng.choice([0.7, 0.75, 0.8, 0.85]), 2)
        t["loyalty_scheme"] = SCHEME[style]
        band, small, ends = f"{BAND[style][2]} £{big:.2f}", [f"Regular price £{price:.2f}"], end_date(rng)
    elif style == "was":
        t["was_price"] = round(price + rng.choice([0.2, 0.25, 0.5, 0.3]), 2)
        band, small = f"Now £{price:.2f}", [f"Was £{t['was_price']:.2f}"]
        ends = end_date(rng) if rng.random() < 0.6 else None
    elif style == "multibuy":
        n = rng.choice([2, 3])
        t["multibuy_qty"], t["multibuy_price"] = n, round(price * n * rng.choice([0.75, 0.8, 0.85]) * 2) / 2
        band, small, ends = f"Any {n} for £{t['multibuy_price']:.2f}", [f"£{price:.2f}"], end_date(rng)
    if ends:
        t["valid_until"] = ends.isoformat()
        small.append(f"Ends {ends:%d/%m}" if rng.random() < 0.6 else f"Offer ends {ends:%d/%m/%y}")
    unit = unit_text(name, big)
    if unit:
        small.append(unit)
    printed_lines = [printed] + ([band] if band else []) + ([f"£{price:.2f}"] if style == "plain" else []) + small
    return {"chain": chain, "style": style, "printed": printed_lines, "truth": t, "answer": answer, "band": band,
            "big": big, "small": [l for l in small if not (style == "multibuy" and l.startswith("£"))],
            "neighbour": rng.random() < 0.3, "tilt": rng.uniform(-5, 5), "blur": rng.uniform(0.4, 1.3)}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT.format(kind), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=f) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def draw_label(item: dict) -> Image.Image:
    W, H = 900, 430
    img = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(img)
    style, small = item["style"], item["small"]
    d.rectangle([0, 0, W - 1, H - 1], outline="#bbbbbb", width=3)
    top = 24
    if style in BAND:
        bg, ink, text = BAND[style]
        d.rectangle([0, 0, W, 70], fill=bg)
        head = text if style in SCHEME else item["band"] if style == "multibuy" else "Price drop"
        d.text((24, 14), head, font=font("Bold", 38), fill=ink)
        top = 90
    for i, l in enumerate(wrap(d, item["printed"][0], font("Bold", 34), 470)[:3]):
        d.text((24, top + i * 42), l, font=font("Bold", 34), fill="#111111")
    d.text((W - 24, top + 10), f"£{item['big']:.2f}", font=font("Bold", 120), fill="#111111", anchor="ra")
    if style == "multibuy":
        d.text((W - 24, top + 140), "each", font=font("Regular", 28), fill="#222222", anchor="ra")
    for i, l in enumerate(small):
        d.text((24, H - 40 - (len(small) - 1 - i) * 34), l, font=font("Regular", 28), fill="#222222")
    d.text((W - 16, H - 14), "SYNTHETIC TEST LABEL", font=font("Regular", 16), fill="#999999", anchor="rs")
    return img


def photograph(label: Image.Image, item: dict, rng: random.Random, neighbour: Image.Image | None) -> Image.Image:
    shelf = Image.new("RGB", (1300, 760), rng.choice(["#6b6f73", "#8a8d90", "#5a4a3c", "#b9b4aa"]))
    if neighbour:
        shelf.paste(neighbour.resize((600, 287)), (1300 - 140, 240))
    lab = label.rotate(item["tilt"], expand=True, fillcolor=shelf.getpixel((0, 0)))
    shelf.paste(lab, ((1300 - lab.width) // 2 - (60 if neighbour else 0), (760 - lab.height) // 2))
    return shelf.filter(ImageFilter.GaussianBlur(item["blur"])).resize((1040, 608))


def main() -> None:
    rng = random.Random(20261017)
    conn = db.connect()
    db.init(conn)
    picks = [(c, n, p, n) for c, n, p in pick_products(conn, rng)] + [(c, n, p, None) for c, n, p in NEW]
    for chain, name, _ in NEW:
        assert not conn.execute("SELECT 1 FROM chain_products WHERE chain = ? AND name = ?", (chain, name)).fetchone()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.jpg"):
        old.unlink()
    items = []
    for i, (chain, name, old, answer) in enumerate(picks):
        item = make(rng, chain, name, old, answer)
        item["id"] = f"{i:02d}-{re.sub(r'[^a-z]+', '', chain.lower())}"
        label = draw_label(item)
        other = draw_label(make(rng, chain, picks[(i + 7) % len(picks)][1], 1.5, None)) if item["neighbour"] else None
        photograph(label, item, rng, other).save(OUT / f"{item['id']}.jpg", quality=72)
        item["image"] = f"labels/{item['id']}.jpg"
        item["other_labels"] = 1 if other else 0
        items.append({k: item[k] for k in ("id", "image", "chain", "style", "printed", "truth", "answer", "other_labels")})
    (db.DATA / "eval" / "label_test.json").write_text(json.dumps({
        "note": "SYNTHETIC shelf label test set, built by scripts/make_labels.py. Product names are real (Kaggle "
                "product list); prices, offers and dates are invented. answer: the Kaggle product name, or null for a "
                "made-up product that is not in the list. printed: the text on the label, given to the baseline as if "
                "typed. Rendered images are cleaner than real shelf photos. The label prompts have no examples, so "
                "there is no tuning split.", "today": TODAY.isoformat(), "items": items}, indent=1))
    print(f"{len(items)} labels -> {OUT}")


if __name__ == "__main__":
    main()

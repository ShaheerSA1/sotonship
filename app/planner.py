"""Pick which shops to visit for a list, trading basket cost against time.

Plain optimisation, no AI: the AI's job ends once list items are matched to products.
"""

import math
from itertools import combinations, permutations

import httpx

from .db import LOYALTY_SCHEMES as LOYALTY

SPEED_KMH = {"walk": 4.8, "cycle": 14.0, "bus": 12.0, "car": 22.0}  # door-to-door city averages, our assumption
ROAD_FACTOR = 1.3      # straight-line to street distance, our assumption
MINUTES_PER_SHOP = 8   # time inside each extra shop, our assumption
MAX_AGE_DAYS = 90      # older community prices are ignored
REF_MAX_AGE_DAYS = 365 # older Open Food Facts prices are ignored
STALE_DAYS = 30        # older prices are shown with a warning
CANDIDATE_STORES = 10


class LocationError(Exception):
    pass


def geocode_postcode(postcode: str) -> tuple[float, float]:
    """postcodes.io, live. Free, ONS Postcode Directory data (OGL)."""
    pc = postcode.strip().replace(" ", "")
    try:
        r = httpx.get(f"https://api.postcodes.io/postcodes/{pc}", timeout=8)
    except httpx.HTTPError as e:
        raise LocationError(f"Postcode lookup failed (postcodes.io unreachable): {e}") from e
    if r.status_code == 404:
        raise LocationError(f"Postcode {postcode!r} not found.")
    r.raise_for_status()
    res = r.json()["result"]
    return res["latitude"], res["longitude"]


def nearest_postcode(lat: float, lon: float) -> str | None:
    """postcodes.io reverse lookup, live. Used only to label a device location."""
    try:
        r = httpx.get("https://api.postcodes.io/postcodes", params={"lat": lat, "lon": lon, "limit": 1, "radius": 1000}, timeout=8)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise LocationError(f"Reverse postcode lookup failed (postcodes.io): {e}") from e
    res = r.json().get("result") or []
    return res[0]["postcode"] if res else None


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def route_minutes(home: tuple[float, float], shops: list[dict], mode: str) -> tuple[float, list[dict], float]:
    """Shortest round trip home -> shops -> home. At most 3 shops, so brute force."""
    best = None
    for order in permutations(shops):
        pts = [home, *[(s["lat"], s["lon"]) for s in order], home]
        dist = sum(km(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) * ROAD_FACTOR
        if best is None or dist < best[0]:
            best = (dist, list(order))
    dist, order = best
    minutes = dist / SPEED_KMH[mode] * 60 + MINUTES_PER_SHOP * (len(shops) - 1)
    return minutes, order, dist


def effective_price(obs: dict, loyalty: set[str], discounts: dict[str, float]) -> tuple[float, list[str]]:
    price, applied = obs["unit_price"], []
    if obs["loyalty_price"] is not None and obs["loyalty_scheme"] in loyalty:
        price = obs["loyalty_price"]
        applied.append(obs["loyalty_scheme"])
    pct = discounts.get(obs["chain"], 0)
    if pct:
        price = price * (1 - pct / 100)
        applied.append(f"your {pct:g}% {obs['chain']} discount")
    return round(price, 2), applied


def merge_prices(community: list[dict], reference: list[dict], stores: list[dict]) -> list[dict]:
    """One price per (product, store), best evidence first:
    1. a community receipt from this branch
    2. a community receipt from another branch of the same chain and format (big chains mostly price nationally)
    3. an Open Food Facts price for the chain, same format if there is one. Temporary fallback until receipts cover it.
    Every price keeps a 'source' so the UI can say where it came from."""
    out = [{**p, "source": "receipt", "borrowed_from": None} for p in community]
    have = {(p["product_id"], p["store_id"]) for p in community}
    latest_by_chain: dict[tuple, dict] = {}
    for p in community:
        key = (p["product_id"], p["chain"], p["format"])
        if key not in latest_by_chain or p["observed_on"] > latest_by_chain[key]["observed_on"]:
            latest_by_chain[key] = p
    ref: dict[tuple, dict] = {}
    for r in reference:
        ref[(r["product_id"], r["chain"], r["format"])] = r
    products = {p["product_id"] for p in community} | {r["product_id"] for r in reference}
    for s in stores:
        for pid in products:
            if (pid, s["id"]) in have:
                continue
            p = latest_by_chain.get((pid, s["chain"], s["format"]))
            if p:
                out.append({**p, "store_id": s["id"], "store_name": s["name"], "source": "receipt_other_branch",
                            "borrowed_from": p["store_name"]})
                continue
            other = "small" if s["format"] == "large" else "large"
            r = ref.get((pid, s["chain"], s["format"])) or ref.get((pid, s["chain"], other))
            if r:
                out.append({"product_id": pid, "store_id": s["id"], "store_name": s["name"], "chain": s["chain"],
                            "format": s["format"], "unit_price": r["unit_price"], "loyalty_price": r["loyalty_price"],
                            "loyalty_scheme": LOYALTY.get(s["chain"]) if r["loyalty_price"] else None,
                            "observed_on": r["observed_on"], "age_days": r["age_days"], "n_obs": r["n_obs"],
                            "synthetic": 0, "source": "openfoodfacts", "borrowed_from": r["location"],
                            "other_format": r["format"] != s["format"], "off_name": r["off_name"]})
    return out


def frontier(results: list[dict], limit: int = 7) -> list[dict]:
    """Routes nobody would rule out: each is quicker than every cheaper one. Cheapest first."""
    ordered = sorted(results, key=lambda r: (r["minutes"], r["basket"]))
    front = []
    for r in ordered:
        if not front or r["basket"] < front[-1]["basket"] - 0.005:
            front.append(r)
    front.reverse()  # cheapest first, quickest last
    if len(front) > limit:  # keep both ends, thin the middle evenly
        step = (len(front) - 1) / (limit - 1)
        front = [front[round(i * step)] for i in range(limit)]
    return front


def plan(items: list[dict], community: list[dict], reference: list[dict], stores: list[dict],
         home: tuple[float, float], *, mode: str, radius_km: float, max_shops: int,
         loyalty: set[str], discounts: dict[str, float], avoid_chains: set[str]) -> dict:
    """items: matched list items with product_ids. community: latest receipt price per (product, store).
    reference: latest Open Food Facts price per (product, chain, format)."""
    nearby = sorted(
        ({**s, "km": km(home, (s["lat"], s["lon"]))} for s in stores), key=lambda s: s["km"])
    in_range = [s for s in nearby if s["km"] <= radius_km]
    nearby = [s for s in in_range if s["chain"] not in avoid_chains]
    prices = merge_prices(community, reference, nearby)
    priced_ids = {p["store_id"] for p in prices}
    # nearest branch of each chain and format first, so the shortlist is not ten Tesco Expresses
    priced = [s for s in nearby if s["id"] in priced_ids]
    seen, candidates = set(), []
    for s in priced:
        if (s["chain"], s["format"]) not in seen:
            seen.add((s["chain"], s["format"]))
            candidates.append(s)
    candidates += [s for s in priced if s not in candidates]
    candidates = candidates[:CANDIDATE_STORES]
    if not candidates:
        skipped = f" {len(in_range) - len(nearby)} skipped because you avoid them." if len(in_range) > len(nearby) else ""
        return {"error": f"No shop with prices within {radius_km:g} km. "
                         f"{len(nearby)} shops in range have no prices yet.{skipped}"}

    # best offer per (item index, store)
    offers: dict[tuple[int, str], dict] = {}
    for idx, item in enumerate(items):
        wanted = set(item["product_ids"])
        for p in prices:
            if p["product_id"] not in wanted:
                continue
            price, applied = effective_price(p, loyalty, discounts)
            key = (idx, p["store_id"])
            if key not in offers or price < offers[key]["price"]:
                offers[key] = {**p, "price": price, "applied": applied}

    def evaluate(shops: tuple[dict, ...]) -> dict:
        lines, missing, basket = [], [], 0.0
        for idx, item in enumerate(items):
            choices = [offers[(idx, s["id"])] for s in shops if (idx, s["id"]) in offers]
            if not choices:
                missing.append(item["input_text"])
                continue
            o = min(choices, key=lambda c: c["price"])
            qty = item.get("quantity") or 1
            basket += o["price"] * qty
            lines.append({"item": item["input_text"], "quantity": qty, "product_id": o["product_id"],
                          "store_id": o["store_id"], "store": o["store_name"], "chain": o["chain"],
                          "unit_price": o["price"], "shelf_price": o["unit_price"], "applied": o["applied"],
                          "observed_on": o["observed_on"], "age_days": o["age_days"],
                          "stale": o["age_days"] > STALE_DAYS, "n_obs": o["n_obs"],
                          "source": o["source"], "borrowed_from": o["borrowed_from"],
                          "other_format": o.get("other_format", False),
                          "synthetic": bool(o["synthetic"]), "warnings": item.get("diet_warnings", [])})
        used = [s for s in shops if any(l["store_id"] == s["id"] for l in lines)]
        if not used:
            return {"covered": 0}
        minutes, order, dist = route_minutes(home, used, mode)
        return {"covered": len(lines), "missing": missing, "lines": lines, "basket": round(basket, 2),
                "minutes": round(minutes), "km": round(dist, 1),
                "shops": [{"id": s["id"], "name": s["name"], "chain": s["chain"], "km_from_home": round(s["km"], 2),
                           "address": s["address"], "lat": s["lat"], "lon": s["lon"]} for s in order]}

    results = []
    for k in range(1, max_shops + 1):
        for combo in combinations(candidates, k):
            r = evaluate(combo)
            if r["covered"] and len(r["shops"]) == k:  # skip combos with an unused shop
                results.append(r)
    top = max(r["covered"] for r in results)
    options = frontier([r for r in results if r["covered"] == top])
    return {"options": options, "routes_compared": len(results),
            "candidates_considered": len(candidates), "shops_in_radius": len(in_range),
            "shops_avoided": len(in_range) - len(nearby),
            "assumptions": {"speed_kmh": SPEED_KMH[mode], "road_factor": ROAD_FACTOR,
                            "minutes_per_extra_shop": MINUTES_PER_SHOP,
                            "max_price_age_days": MAX_AGE_DAYS, "max_reference_age_days": REF_MAX_AGE_DAYS,
                            "stale_after_days": STALE_DAYS}}

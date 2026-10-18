"""Pick which shops to visit for a list, trading basket cost against time.

Plain optimisation, no AI: the AI's job ends once list items are matched to products.
"""

import math
from collections.abc import Callable
from datetime import date
from itertools import combinations, permutations

import httpx

from . import streets
from .classes import parse_size
from .db import LOYALTY_SCHEMES as LOYALTY

SPEED_KMH = {"walk": 4.8, "cycle": 14.0, "bus": 12.0, "car": 22.0}  # door-to-door city averages, our assumption
ROAD_FACTOR = 1.3      # straight-line to street distance, our assumption. Used only off the mapped streets
MINUTES_PER_SHOP = 8   # time inside each extra shop, our assumption
MAX_AGE_DAYS = 90      # older community prices are ignored
REF_MAX_AGE_DAYS = 365 # older Open Food Facts prices are ignored
STALE_DAYS = 30        # older prices are shown with a warning
CANDIDATE_STORES = 10
SIZE_SHORT = 0.9       # packs must make at least 90% of the amount asked for
SIZE_OVER = 1.5        # and at most 150% of it: a 1kg bag is not an answer to "500g"


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


def distance_table(ends: dict[str, tuple[float, float]], stores: list[dict], mode: str) -> tuple[dict, dict, Callable]:
    """Street km between the trip ends ("start", and "end" when it differs) and every candidate shop, keyed by
    end name or store id, and path(a, b) for the map.
    Falls back to straight line x ROAD_FACTOR where streets cannot route, and says so in the routing note."""
    keys = [*ends, *[s["id"] for s in stores]]
    points = [*ends.values(), *[(s["lat"], s["lon"]) for s in stores]]
    estimate = lambda i, j: km(points[i], points[j]) * ROAD_FACTOR
    try:
        street, street_path = streets.table(points, mode)
        routing = {"source": "streets", "network": streets.NETWORK[mode], "osm_timestamp": streets.META["osm_timestamp"]}
    except streets.StreetsError as e:
        street, street_path = None, lambda i, j: None
        routing = {"source": "estimate", "error": str(e)}
    table, gaps = {}, 0
    for i, a in enumerate(keys):
        for j, b in enumerate(keys):
            d = street[i][j] / 1000 if street and street[i][j] is not None else None
            if street and d is None:
                gaps += 1
            table[a, b] = estimate(i, j) if d is None else d
    if gaps:
        routing["gaps"] = gaps  # pairs off the mapped streets, estimated instead
    at = {k: i for i, k in enumerate(keys)}
    return table, routing, lambda a, b: street_path(at[a], at[b])


def route_minutes(shops: list[dict], mode: str, dist_km: dict, end: str = "start") -> tuple[float, list[dict], float]:
    """Shortest trip start -> shops -> end. At most 3 shops, so brute force."""
    best = None
    for order in permutations(shops):
        stops = ["start", *[s["id"] for s in order], end]
        dist = sum(dist_km[stops[i], stops[i + 1]] for i in range(len(stops) - 1))
        if best is None or dist < best[0]:
            best = (dist, list(order))
    dist, order = best
    minutes = dist / SPEED_KMH[mode] * 60 + MINUTES_PER_SHOP * (len(shops) - 1)
    return minutes, order, dist


def packs_for(wanted: dict, pack: dict) -> int | None:
    """How many packs make the amount asked for, or None when no number of packs comes close.
    Weight and volume first, then counts ("12 eggs" from 6 packs)."""
    for dim in ("mass", "volume", "count"):
        if dim in wanted and dim in pack and pack[dim] > 0:
            n = max(1, math.ceil(SIZE_SHORT * wanted[dim] / pack[dim] - 1e-9))
            return n if n * pack[dim] <= SIZE_OVER * wanted[dim] else None
    return None


def fit_sizes(items: list[dict], catalogue: list[dict]) -> list[dict]:
    """Rules, no AI. For an item with a size ("1kg pasta"), how many packs of each product make that amount.
    Products that no number of packs fits are dropped, and the item says which. A product whose pack size
    we cannot read is kept as one pack and flagged."""
    by_id = {p["id"]: p for p in catalogue}
    out = []
    for item in items:
        wanted = parse_size(item.get("size_wanted") or "")
        if item["status"] != "matched" or not wanted:
            out.append(item)
            continue
        packs, dropped, unknown, bigger = {}, [], [], {}
        for pid in item["product_ids"] + item.get("swap_ids", []):
            p = by_id.get(pid, {})
            pack = parse_size(p.get("size") or "") or parse_size(p.get("name") or "")  # size "6" is a count of 6
            n = packs_for(wanted, pack)
            if n:
                packs[pid] = n
            elif set(wanted) & set(pack):
                dropped.append(p.get("name") or pid)
                if any(pack[d] > wanted[d] for d in set(wanted) & set(pack)):
                    bigger[pid] = p.get("size") or p.get("name")
            else:
                packs[pid] = 1
                unknown.append(p.get("name") or pid)
        bigger_asked = [pid for pid in item["product_ids"] if pid in bigger]
        if not any(pid in packs for pid in item["product_ids"]) and bigger_asked:
            # nothing that small: one of the smallest bigger packs, and say so
            packs.update({pid: 1 for pid in bigger})
            dropped = [d for d in dropped if d not in {by_id[pid]["name"] for pid in bigger if pid in by_id}]
            item = {**item, "size_note": f"No pack as small as {item['size_wanted']}. Priced as one "
                                         f"{', '.join(sorted(set(bigger[pid] for pid in bigger_asked)))} pack."}
        item = {**item, "packs": packs, "size_dropped": dropped, "size_unknown": unknown}
        if not any(pid in packs for pid in item["product_ids"]):
            item.update(status="no_size", note=f"No pack we track makes {item['size_wanted']}: "
                                               f"{', '.join(dropped)}.")
        else:
            item["product_ids"] = [pid for pid in item["product_ids"] if pid in packs]
            item["swap_ids"] = [pid for pid in item.get("swap_ids", []) if pid in packs]
        out.append(item)
    return out


def offer_ended(obs: dict, today: str) -> bool:
    return bool(obs.get("valid_until")) and obs["valid_until"] < today


def effective_price(obs: dict, loyalty: set[str], discounts: dict[str, float], today: str) -> tuple[float, list[str]]:
    """Price of one unit for this shopper. An offer past its end date on the label no longer counts: the
    member price is dropped, and a shelf price that was itself the offer goes back to the "was" price."""
    price, applied = obs["unit_price"], []
    ended = offer_ended(obs, today)
    if ended and obs.get("was_price") and obs.get("loyalty_price") is None and not obs.get("multibuy_qty"):
        price = obs["was_price"]
    if obs.get("loyalty_price") is not None and obs.get("loyalty_scheme") in loyalty and not ended:
        price = obs["loyalty_price"]
        applied.append(obs["loyalty_scheme"])
    pct = discounts.get(obs["chain"], 0)
    if pct:
        price = price * (1 - pct / 100)
        applied.append(f"your {pct:g}% {obs['chain']} discount")
    return round(price, 2), applied


def line_cost(obs: dict, qty: int, loyalty: set[str], discounts: dict[str, float], today: str) -> tuple[float, float, list[str]]:
    """(total for qty, unit price, offers applied). A multibuy ("3 for £5") counts when the list asks for enough,
    the offer has not ended and, if it is members only, the shopper has the card."""
    unit, applied = effective_price(obs, loyalty, discounts, today)
    total = unit * qty
    n, deal = obs.get("multibuy_qty"), obs.get("multibuy_price")
    scheme = obs.get("multibuy_scheme")
    if n and deal and qty >= n and not offer_ended(obs, today) and (not scheme or scheme in loyalty):
        pct = discounts.get(obs["chain"], 0)
        multi = (qty // n) * deal * (1 - pct / 100) + (qty % n) * unit
        if multi < total - 0.005:
            total = multi
            applied = applied + [f"{n} for £{deal:.2f}" + (f" with {scheme}" if scheme else "")]
    return round(total, 2), unit, applied


def merge_prices(community: list[dict], reference: list[dict], stores: list[dict],
                 baseline: list[dict] | None = None) -> list[dict]:
    """One price per (product, store), best evidence first:
    1. a shopper price from this branch: shelf label or barcode scan
    2. a shopper price from another branch of the same chain and format (big chains mostly price nationally)
    3. an Open Food Facts price for the chain, same format if there is one
    4. the chain's 2024 online price from the Kaggle set: the starting price every linked product has
    Every price keeps a 'source' so the UI can say where it came from."""
    out = [{**p, "source": "shopper", "borrowed_from": None} for p in community]
    have = {(p["product_id"], p["store_id"]) for p in community}
    latest_by_chain: dict[tuple, dict] = {}
    for p in community:
        key = (p["product_id"], p["chain"], p["format"])
        if key not in latest_by_chain or p["observed_on"] > latest_by_chain[key]["observed_on"]:
            latest_by_chain[key] = p
    ref: dict[tuple, dict] = {}
    for r in reference:
        ref[(r["product_id"], r["chain"], r["format"])] = r
    base = {(b["product_id"], b["chain"]): b for b in baseline or []}
    products = {p["product_id"] for p in community} | {r["product_id"] for r in reference} | {k[0] for k in base}
    for s in stores:
        for pid in products:
            if (pid, s["id"]) in have:
                continue
            p = latest_by_chain.get((pid, s["chain"], s["format"]))
            if p:
                out.append({**p, "store_id": s["id"], "store_name": s["name"], "source": "shopper_other_branch",
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
                continue
            b = base.get((pid, s["chain"]))
            if b:
                out.append({"product_id": pid, "store_id": s["id"], "store_name": s["name"], "chain": s["chain"],
                            "format": s["format"], "unit_price": b["unit_price"], "loyalty_price": None,
                            "loyalty_scheme": None, "observed_on": b["observed_on"], "age_days": b["age_days"],
                            "n_obs": 1, "synthetic": 0, "source": "online_2024", "borrowed_from": f"{s['chain']} website",
                            "chain_name": b["chain_name"], "linked_by": b["linked_by"]})
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
         start: tuple[float, float], *, mode: str, radius_km: float, max_shops: int,
         loyalty: set[str], discounts: dict[str, float], avoid_chains: set[str],
         baseline: list[dict] | None = None, end: tuple[float, float] | None = None) -> dict:
    """items: matched list items with product_ids. community: latest shopper price per (product, store).
    reference: latest Open Food Facts price per (product, chain, format). baseline: 2024 online price per
    (product, chain). The trip runs start -> shops -> end, back to start when end is None. A shop is in range
    when it is within radius_km of either end."""
    today = date.today().isoformat()
    ends = {"start": start} if end is None or end == start else {"start": start, "end": end}
    last = "end" if "end" in ends else "start"
    nearby = sorted(
        ({**s, "km": min(km(p, (s["lat"], s["lon"])) for p in ends.values())} for s in stores), key=lambda s: s["km"])
    in_range = [s for s in nearby if s["km"] <= radius_km]
    nearby = [s for s in in_range if s["chain"] not in avoid_chains]
    prices = merge_prices(community, reference, nearby, baseline)
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
    dist_km, routing, path = distance_table(ends, candidates, mode)

    # best offer per (item index, store), for the quantity on the list
    offers: dict[tuple[int, str], dict] = {}
    for idx, item in enumerate(items):
        wanted = set(item["product_ids"]) | set(item.get("swap_ids", []))
        packs = item.get("packs") or {}
        for p in prices:
            if p["product_id"] not in wanted:
                continue
            qty = (item.get("quantity") or 1) * packs.get(p["product_id"], 1)
            total, price, applied = line_cost(p, qty, loyalty, discounts, today)
            key = (idx, p["store_id"])
            if key not in offers or total < offers[key]["total"]:
                offers[key] = {**p, "price": price, "total": total, "applied": applied, "qty": qty,
                               "swap": p["product_id"] not in item["product_ids"]}

    def evaluate(shops: tuple[dict, ...]) -> dict:
        lines, missing, basket = [], [], 0.0
        for idx, item in enumerate(items):
            choices = [offers[(idx, s["id"])] for s in shops if (idx, s["id"]) in offers]
            if not choices:
                missing.append(item["input_text"])
                continue
            o = min(choices, key=lambda c: c["total"])
            basket += o["total"]
            lines.append({"item": item["input_text"], "quantity": o["qty"], "product_id": o["product_id"],
                          "item_quantity": item.get("quantity") or 1, "swap": o["swap"],
                          "size_wanted": item.get("size_wanted"),
                          "store_id": o["store_id"], "store": o["store_name"], "chain": o["chain"],
                          "unit_price": o["price"], "line_total": o["total"], "shelf_price": o["unit_price"],
                          "applied": o["applied"], "valid_until": o.get("valid_until"),
                          "offer_ended": offer_ended(o, today), "chain_name": o.get("chain_name"),
                          "observed_on": o["observed_on"], "age_days": o["age_days"],
                          "stale": o["age_days"] > STALE_DAYS and o["source"] != "online_2024", "n_obs": o["n_obs"],
                          "source": o["source"], "method": o.get("method"), "borrowed_from": o["borrowed_from"],
                          "other_format": o.get("other_format", False),
                          "synthetic": bool(o["synthetic"]), "warnings": item.get("diet_warnings", [])})
        used = [s for s in shops if any(l["store_id"] == s["id"] for l in lines)]
        if not used:
            return {"covered": 0}
        minutes, order, dist = route_minutes(used, mode, dist_km, last)
        return {"covered": len(lines), "missing": missing, "lines": lines, "basket": round(basket, 2),
                "minutes": round(minutes), "km": round(dist, 1),
                "shops": [{"id": s["id"], "name": s["name"], "chain": s["chain"], "km_from_start": round(dist_km["start", s["id"]], 2),
                           "address": s["address"], "lat": s["lat"], "lon": s["lon"]} for s in order]}

    results = []
    for k in range(1, max_shops + 1):
        for combo in combinations(candidates, k):
            r = evaluate(combo)
            if r["covered"] and len(r["shops"]) == k:  # skip combos with an unused shop
                results.append(r)
    top = max(r["covered"] for r in results)
    options = frontier([r for r in results if r["covered"] == top])
    # a quicker route left out because it cannot get everything: say so, never let "cheapest is quickest" hide it
    short = min((r for r in results if r["covered"] < top), key=lambda r: r["minutes"], default=None)
    quicker = None
    if short and short["minutes"] < options[-1]["minutes"]:
        quicker = {"shops": [s["name"] for s in short["shops"]], "minutes": short["minutes"],
                   "missing": short["missing"]}
    for o in options:  # street path for the map, start -> shops -> end. None where a leg was estimated
        stops = ["start", *[s["id"] for s in o["shops"]], last]
        legs = [path(a, b) for a, b in zip(stops, stops[1:])]
        o["path"] = None if None in legs else [p for leg in legs for p in leg]
    return {"options": options, "routes_compared": len(results), "quicker_incomplete": quicker,
            "candidates_considered": len(candidates), "shops_in_radius": len(in_range),
            "shops_avoided": len(in_range) - len(nearby), "routing": routing,
            "assumptions": {"speed_kmh": SPEED_KMH[mode], "road_factor": ROAD_FACTOR,
                            "minutes_per_extra_shop": MINUTES_PER_SHOP,
                            "max_price_age_days": MAX_AGE_DAYS, "max_reference_age_days": REF_MAX_AGE_DAYS,
                            "stale_after_days": STALE_DAYS}}

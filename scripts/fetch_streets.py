"""Fetch the Southampton street network from OpenStreetMap (Overpass API) for the planner's own routing.

Writes data/streets/streets.npz (nodes and one edge list per network) and data/streets/streets.json (source and date).
Three networks: walk, cycle and drive. Each keeps only its largest connected part, so a shop never snaps to an island.
Each edge has its length in metres and a routing cost, which is the length made longer on car park aisles and
driveways, so routes keep to streets unless a cut through is clearly shorter.
Data (c) OpenStreetMap contributors, ODbL.
Run: .venv/bin/python scripts/fetch_streets.py
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

# south, west, north, east: every shop in data/stores.json plus about 3 km round it
BBOX = (50.856, -1.511, 50.975, -1.285)
QUERY = f"""[out:json][timeout:240];
way["highway"]{BBOX}->.w;
.w out body qt;
node(w.w);
out skel qt;"""
MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter"]

ROADS = {"trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link", "tertiary",
         "tertiary_link", "unclassified", "residential", "living_street", "service", "road"}
WALK = ROADS | {"pedestrian", "footway", "path", "steps", "track", "cycleway", "bridleway", "corridor"}
CYCLE = ROADS | {"cycleway", "path", "track", "bridleway"}
DRIVE = ROADS | {"motorway", "motorway_link"}
NO = {"no", "private"}
DETOUR = {"parking_aisle": 2.0, "driveway": 2.0, "drive-through": 2.0}  # service=* tags a route should avoid
YES = {"yes", "designated", "permissive"}


def allowed(tags: dict, mode: str) -> bool:
    hw, access = tags.get("highway"), tags.get("access")
    if mode == "walk":
        return hw in WALK and tags.get("foot") not in NO and (access not in NO or tags.get("foot") in YES)
    if mode == "cycle":
        if tags.get("bicycle") in NO:
            return False
        return (hw in CYCLE or (hw in {"footway", "pedestrian"} and tags.get("bicycle") in YES)) and \
            (access not in NO or tags.get("bicycle") in YES)
    car = tags.get("motorcar") or tags.get("motor_vehicle") or access
    return hw in DRIVE and car not in NO and tags.get("service") != "emergency_access" and tags.get("area") != "yes"


def direction(tags: dict, mode: str) -> int:
    """1 one way along the drawn order, -1 against it, 0 both ways."""
    if mode == "walk":
        return 0
    oneway = tags.get("oneway")
    if mode == "cycle" and (tags.get("oneway:bicycle") == "no" or str(tags.get("cycleway", "")).startswith("opposite")):
        return 0
    if oneway == "-1":
        return -1
    if oneway in {"yes", "1", "true"} or tags.get("junction") in {"roundabout", "circular"} or \
            (mode == "drive" and tags.get("highway") in {"motorway", "motorway_link"} and oneway != "no"):
        return 1
    return 0


def cost(tags: dict) -> float:
    """How much longer than its length an edge counts when choosing a route."""
    if tags.get("highway") != "service":
        return 1.0
    return DETOUR.get(tags.get("service"), 1.2)  # plain service roads are often back lanes and yards


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def main() -> None:
    for url in MIRRORS:
        try:
            r = httpx.post(url, data={"data": QUERY}, headers={"User-Agent": "sotonship-hackathon/0.1 (student project)"},
                           timeout=300)
            r.raise_for_status()
            payload = r.json()
            break
        except (httpx.HTTPError, ValueError) as e:
            print(f"{url} failed: {e}")
    else:
        raise SystemExit("Every Overpass mirror failed.")
    coords = {el["id"]: (el["lat"], el["lon"]) for el in payload["elements"] if el["type"] == "node"}
    ways = [el for el in payload["elements"] if el["type"] == "way"]
    print(f"{len(ways)} ways, {len(coords)} nodes from Overpass")

    index: dict[int, int] = {}  # OSM node id -> our index
    edges = {m: [] for m in ("walk", "cycle", "drive")}
    for w in ways:
        tags = w.get("tags", {})
        for mode, out in edges.items():
            if not allowed(tags, mode):
                continue
            d, c = direction(tags, mode), cost(tags)
            nds = [n for n in w["nodes"] if n in coords]
            for a, b in zip(nds, nds[1:]):
                ia, ib = index.setdefault(a, len(index)), index.setdefault(b, len(index))
                length = metres(coords[a], coords[b])
                if d >= 0:
                    out.append((ia, ib, length, length * c))
                if d <= 0:
                    out.append((ib, ia, length, length * c))

    n = len(index)
    keep_nodes = np.zeros(n, bool)
    kept = {}
    for mode, out in edges.items():
        u, v, m, c = (np.array(x) for x in zip(*out))
        g = coo_matrix((m, (u, v)), shape=(n, n))
        _, labels = connected_components(g, directed=True, connection="strong")
        main_part = labels == np.bincount(labels[np.unique(np.concatenate([u, v]))]).argmax()
        ok = main_part[u] & main_part[v]
        kept[mode] = (u[ok], v[ok], m[ok], c[ok])
        keep_nodes[u[ok]] = keep_nodes[v[ok]] = True
        print(f"{mode}: {ok.sum()} edges kept of {len(u)}, {main_part.sum()} nodes in the main part")

    remap = np.full(n, -1, np.int64)
    remap[keep_nodes] = np.arange(keep_nodes.sum())
    ll = np.zeros((n, 2))
    for osm_id, i in index.items():
        ll[i] = coords[osm_id]
    ll = ll[keep_nodes]
    arrays = {"lat_e6": np.round(ll[:, 0] * 1e6).astype(np.int32), "lon_e6": np.round(ll[:, 1] * 1e6).astype(np.int32)}
    for mode, (u, v, m, c) in kept.items():
        arrays[f"{mode}_u"] = remap[u].astype(np.int32)
        arrays[f"{mode}_v"] = remap[v].astype(np.int32)
        arrays[f"{mode}_m"] = m.astype(np.float32)
        arrays[f"{mode}_c"] = c.astype(np.float32)

    folder = Path(__file__).resolve().parent.parent / "data" / "streets"
    folder.mkdir(exist_ok=True)
    np.savez_compressed(folder / "streets.npz", **arrays)
    (folder / "streets.json").write_text(json.dumps({
        "source": "OpenStreetMap via Overpass API",
        "licence": "ODbL 1.0, (c) OpenStreetMap contributors",
        "osm_timestamp": payload.get("osm3s", {}).get("timestamp_osm_base"),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bbox": BBOX,
        "nodes": int(keep_nodes.sum()),
        "edges": {mode: int(len(k[0])) for mode, k in kept.items()},
    }, indent=1))
    print(f"{keep_nodes.sum()} nodes written to {folder}")


if __name__ == "__main__":
    main()

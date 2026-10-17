"""Street routing on our own server, over the OpenStreetMap network in data/streets/ (scripts/fetch_streets.py).

No outside service: home and shop locations never leave the server, and there is no rate limit to hit.
"""

import json
import math
import threading
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

FOLDER = Path(__file__).resolve().parent.parent / "data" / "streets"
NETWORK = {"walk": "walk", "cycle": "cycle", "bus": "drive", "car": "drive"}  # buses use the road network
MAX_SNAP_M = 400  # a point further than this from any street is outside the mapped area
LAT0 = math.radians(50.91)  # Southampton, for a flat projection that is exact enough over 20 km

_lock = threading.Lock()
_nets: dict[str, dict] = {}
META = json.loads((FOLDER / "streets.json").read_text()) if (FOLDER / "streets.json").exists() else None


class StreetsError(Exception):
    pass


def _xy(lat, lon):
    return np.column_stack([np.radians(lon) * math.cos(LAT0) * 6371000, np.radians(lat) * 6371000])


def _load(network: str) -> dict:
    with _lock:
        if network in _nets:
            return _nets[network]
        if META is None:
            raise StreetsError("street network file missing (run scripts/fetch_streets.py)")
        z = np.load(FOLDER / "streets.npz")
        lat, lon = z["lat_e6"] / 1e6, z["lon_e6"] / 1e6
        u, v, m = z[f"{network}_u"], z[f"{network}_v"], z[f"{network}_m"].astype(np.float64)
        # where two ways share a segment keep the shorter, since a sparse matrix would add them
        order = np.lexsort((m, v, u))
        u, v, m = u[order], v[order], m[order]
        first = np.ones(len(u), bool)
        first[1:] = (u[1:] != u[:-1]) | (v[1:] != v[:-1])
        u, v, m = u[first], v[first], np.maximum(m[first], 0.01)  # a zero would read as no edge
        n = len(lat)
        on = np.unique(np.concatenate([u, v]))  # nodes this network uses
        _nets[network] = net = {"graph": csr_matrix((m, (u, v)), shape=(n, n)), "lat": lat, "lon": lon,
                                "on": on, "tree": cKDTree(_xy(lat[on], lon[on]))}
        return net


def table(points: list[tuple[float, float]], mode: str):
    """Street metres between every pair of points, None where a point is off the map or no route exists.
    Also returns path(i, j): the street path from point i to point j as [lat, lon] pairs."""
    net = _load(NETWORK[mode])
    pts = np.array(points)
    snap_m, k = net["tree"].query(_xy(pts[:, 0], pts[:, 1]))
    nodes = net["on"][k]
    dist, pred = dijkstra(net["graph"], indices=nodes, return_predecessors=True)
    n = len(points)
    out = [[None] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            d = dist[i, nodes[j]]
            if i == j:
                out[i][j] = 0.0
            elif snap_m[i] <= MAX_SNAP_M and snap_m[j] <= MAX_SNAP_M and np.isfinite(d):
                out[i][j] = float(d + snap_m[i] + snap_m[j])

    def path(i: int, j: int) -> list[list[float]] | None:
        if out[i][j] is None:
            return None
        seq, x = [], nodes[j]
        while x >= 0 and x != nodes[i]:
            seq.append(x)
            x = pred[i, x]
        seq.append(nodes[i])
        seq.reverse()
        line = [[round(float(net["lat"][s]), 5), round(float(net["lon"][s]), 5)] for s in seq]
        return [list(points[i]), *line, list(points[j])]

    return out, path

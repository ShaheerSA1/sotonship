"""Fetch Southampton supermarket locations from OpenStreetMap (Overpass API).

Writes data/stores.json. Data (c) OpenStreetMap contributors, ODbL.
Run: .venv/bin/python scripts/fetch_stores.py
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

BBOX = (50.88, -1.47, 50.96, -1.33)  # south, west, north, east: Southampton
QUERY = f"""[out:json][timeout:50];
(nwr["shop"~"^(supermarket|convenience)$"]{BBOX};);
out center tags;"""

# (chain, regex on brand or name). First match wins. Small format detected from the name.
CHAINS = [
    ("Tesco", r"^tesco"),
    ("Sainsbury's", r"^sainsbury"),
    ("Asda", r"^asda"),
    ("Lidl", r"^lidl"),
    ("Aldi", r"^aldi"),
    ("Morrisons", r"^morrisons"),
    ("Co-op", r"co-?op|co-operative"),
    ("M&S", r"^m&s|marks (and|&) spencer"),
    ("Iceland", r"^iceland"),
]
SMALL = re.compile(r"express|local|daily|simply food|metro|food to go", re.I)


def main() -> None:
    r = httpx.post(
        "https://overpass-api.de/api/interpreter",
        data={"data": QUERY},
        headers={"User-Agent": "sotonship-hackathon/0.1 (student project)"},
        timeout=90,
    )
    r.raise_for_status()
    payload = r.json()
    stores = []
    for el in payload["elements"]:
        tags = el.get("tags", {})
        label = tags.get("brand") or tags.get("name") or ""
        name = tags.get("name") or label
        chain = next((c for c, pat in CHAINS if re.search(pat, label, re.I) or re.search(pat, name, re.I)), None)
        if not chain:
            continue
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None:
            continue
        street = " ".join(filter(None, [tags.get("addr:housenumber"), tags.get("addr:street")]))
        stores.append({
            "id": f"osm-{el['type'][0]}{el['id']}",
            "chain": chain,
            "name": name,
            "format": "small" if SMALL.search(name) or tags.get("shop") == "convenience" else "large",
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "address": ", ".join(filter(None, [street, tags.get("addr:postcode")])) or None,
        })
    stores.sort(key=lambda s: (s["chain"], s["name"]))
    out = {
        "source": "OpenStreetMap via Overpass API",
        "licence": "ODbL 1.0, (c) OpenStreetMap contributors",
        "osm_timestamp": payload.get("osm3s", {}).get("timestamp_osm_base"),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stores": stores,
    }
    path = Path(__file__).resolve().parent.parent / "data" / "stores.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    print(f"{len(stores)} stores written to {path}")


if __name__ == "__main__":
    main()

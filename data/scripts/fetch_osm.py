"""Download OSM roads, waterways, and water bodies/wetlands for the study area (Overpass API).

Outputs in data/raw/: roads.geojson, waterways.geojson (lines) and water.geojson (polygons).
Existing files are reused unless --force is given. Data (c) OpenStreetMap contributors, ODbL.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

SOUTH, WEST, NORTH, EAST = 12.85, 80.05, 13.25, 80.35
BBOX = f"{SOUTH},{WEST},{NORTH},{EAST}"

LINES_QUERY = f"""
[out:json][timeout:90];
(
  way["highway"]({BBOX});
  way["waterway"]({BBOX});
);
out body geom;
"""

WATER_QUERY = """
[out:json][timeout:300];
(
  way["natural"="water"]({bbox});
  way["natural"="wetland"]({bbox});
  way["landuse"="reservoir"]({bbox});
  way["waterway"="riverbank"]({bbox});
  relation["natural"="water"]({bbox});
  relation["natural"="wetland"]({bbox});
  relation["landuse"="reservoir"]({bbox});
);
out body geom;
"""
WATER_TILES = 4  # the study area is queried in WATER_TILES x WATER_TILES sub-boxes (the big query times out)

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

HEADERS = {
    "User-Agent": "VellamWatchDataPipeline/1.0 (student flood-risk research project)",
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
}


def run_query(query: str, rounds: int = 3) -> dict:
    for attempt in range(rounds):
        try:
            return _run_query_once(query)
        except RuntimeError:
            if attempt == rounds - 1:
                raise
            time.sleep(20 * (attempt + 1))


def water_elements() -> dict:
    """Fetch water/wetland elements tile by tile and merge them (deduplicated by type+id)."""
    lats = [SOUTH + (NORTH - SOUTH) * i / WATER_TILES for i in range(WATER_TILES + 1)]
    lons = [WEST + (EAST - WEST) * i / WATER_TILES for i in range(WATER_TILES + 1)]
    seen, elements = set(), []
    for i in range(WATER_TILES):
        for j in range(WATER_TILES):
            bbox = f"{lats[i]},{lons[j]},{lats[i + 1]},{lons[j + 1]}"
            tile_path = RAW_DIR / "osm_water_tiles" / f"tile_{i}_{j}.json"
            if tile_path.exists():
                data = json.loads(tile_path.read_text(encoding="utf-8"))
            else:
                print(f"water tile {i},{j}: {bbox}")
                data = run_query(WATER_QUERY.format(bbox=bbox))
                tile_path.parent.mkdir(parents=True, exist_ok=True)
                tile_path.write_text(json.dumps(data), encoding="utf-8")
                time.sleep(2)
            for el in data["elements"]:
                key = (el["type"], el["id"])
                if key not in seen:
                    seen.add(key)
                    elements.append(el)
    return {"elements": elements}


def _run_query_once(query: str) -> dict:
    for url in ENDPOINTS:
        print(f"Trying: {url}")
        try:
            response = requests.post(url, data={"data": query}, headers=HEADERS, timeout=360)
            if response.status_code in (406, 429):
                print(f"Server rejected request ({response.status_code}); waiting before next endpoint.")
                time.sleep(30)
                continue
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"Request failed: {exc}")
    raise RuntimeError("All Overpass endpoints failed. No output files were created.")


def line_records(data: dict) -> gpd.GeoDataFrame:
    records = []
    for element in data.get("elements", []):
        points = element.get("geometry", [])
        if element.get("type") != "way" or len(points) < 2:
            continue
        tags = element.get("tags", {})
        records.append({
            "osm_id": element["id"],
            "feature_type": "road" if "highway" in tags else "waterway",
            "highway": tags.get("highway"),
            "waterway": tags.get("waterway"),
            "name": tags.get("name"),
            "geometry": LineString([(p["lon"], p["lat"]) for p in points]),
        })
    return gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")


def _ring_polygon(points):
    if len(points) >= 4 and points[0] == points[-1]:
        poly = Polygon([(p["lon"], p["lat"]) for p in points])
        return poly if poly.is_valid else poly.buffer(0)
    return None


def water_records(data: dict) -> gpd.GeoDataFrame:
    """Closed ways become polygons; relations are assembled from their member way geometries."""
    records = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        kind = tags.get("natural") or tags.get("landuse") or tags.get("waterway")
        geom = None
        if element["type"] == "way":
            geom = _ring_polygon(element.get("geometry", []))
        elif element["type"] == "relation":
            lines = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
                     for m in element.get("members", [])
                     if m.get("type") == "way" and len(m.get("geometry", [])) >= 2
                     and m.get("role") in ("outer", "")]
            if lines:
                polys = list(polygonize(unary_union(lines)))
                if polys:
                    geom = unary_union(polys)
        if geom is None or geom.is_empty or not isinstance(geom, (Polygon, MultiPolygon)):
            continue
        records.append({"osm_id": element["id"], "osm_type": element["type"], "kind": kind,
                        "name": tags.get("name"), "geometry": geom})
    return gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")


def main(force: bool = False):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    roads_p, ways_p, water_p = (RAW_DIR / n for n in ("roads.geojson", "waterways.geojson", "water.geojson"))

    if force or not (roads_p.exists() and ways_p.exists()):
        features = line_records(run_query(LINES_QUERY))
        if features.empty:
            raise RuntimeError("The server returned no usable road or waterway lines.")
        features[features["feature_type"] == "road"].to_file(roads_p, driver="GeoJSON")
        features[features["feature_type"] == "waterway"].to_file(ways_p, driver="GeoJSON")
        print("Road features:", int((features["feature_type"] == "road").sum()))
        print("Waterway features:", int((features["feature_type"] == "waterway").sum()))
    else:
        print("roads/waterways cached (use --force to refetch)")

    if not force and (RAW_DIR / "water_manual.geojson").exists():
        print("using manual export data/raw/water_manual.geojson (use --force to refetch)")
    elif force or not water_p.exists():
        water = water_records(water_elements())
        if water.empty:
            raise RuntimeError("The server returned no water bodies or wetlands.")
        water.to_file(water_p, driver="GeoJSON")
        print("Water/wetland polygons:", len(water))
    else:
        print("water cached (use --force to refetch)")
    print("Saved to:", RAW_DIR)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    main(force=ap.parse_args().force)
    sys.exit(0)

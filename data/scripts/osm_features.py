"""Per-cell distance and road features: dist_drain_m, dist_water_m, road_density (km of road per km2).

All geometry work happens in UTM 44N (metres). Distances are measured from the cell centre
to the nearest feature, via a KD-tree on points densified along lines / polygon outlines.

- dist_drain_m: OSM waterways (drain, canal, stream, river, ditch).
- dist_water_m: water bodies + OSM rivers/canals. Water bodies come from OSM polygons when an
  OSM water file exists; otherwise (current default, Overpass was unreachable) from ESA
  WorldCover 2021 classes 80 (permanent water) and 90 (herbaceous wetland), as 25 m pixels
  that are at least half water, with the sea (water connected to the east edge) removed. The source used is written to data/raw/water_source.txt.
- road_density: OSM highways clipped to each cell.
"""
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely import STRtree
from shapely.geometry import Point

from data.config import CELL_M, GRID_CRS, RAW_DIR
from data.scripts.builtup import water_masks
from data.scripts.grid import load_grid

DRAIN_TYPES = {"drain", "canal", "stream", "river", "ditch"}
RIVER_TYPES = {"river", "canal"}  # linear features that also count as "water" for dist_water_m
DENSIFY_M = 25.0
MAX_DIST_M = 20000.0  # cap, in case a feature class is absent from the area


def densify_points(geoms, step: float = DENSIFY_M) -> np.ndarray:
    """Points every `step` metres along line geometries (or polygon boundaries)."""
    pts = []
    for g in geoms:
        if g is None or g.is_empty:
            continue
        lines = g.boundary if g.geom_type in ("Polygon", "MultiPolygon") else g
        parts = getattr(lines, "geoms", [lines])
        for line in parts:
            n = max(int(line.length // step), 1)
            for d in np.linspace(0, line.length, n + 1):
                p = line.interpolate(d)
                pts.append((p.x, p.y))
    return np.asarray(pts, dtype="float64")


def nearest_dist(centres: np.ndarray, pts: np.ndarray) -> np.ndarray:
    if len(pts) == 0:
        return np.full(len(centres), MAX_DIST_M)
    d, _ = cKDTree(pts).query(centres, k=1)
    return np.minimum(d, MAX_DIST_M)


def road_density_km_per_km2(roads: gpd.GeoDataFrame, cells: gpd.GeoDataFrame) -> np.ndarray:
    """Road length clipped to each cell (km) divided by cell area (km2)."""
    tree = STRtree(roads.geometry.values)
    area_km2 = (CELL_M / 1000.0) ** 2
    out = np.zeros(len(cells))
    road_geoms = roads.geometry.values
    for i, poly in enumerate(cells.geometry.values):
        idx = tree.query(poly, predicate="intersects")
        if len(idx) == 0:
            continue
        length = sum(road_geoms[j].intersection(poly).length for j in idx)
        out[i] = length / 1000.0 / area_km2
    return out


def load_osm_water():
    """OSM water/wetland polygons (water.geojson from the script, or a manual overpass-turbo export
    water_manual.geojson), or None if neither exists. Only polygon geometries are kept."""
    for name in ("water.geojson", "water_manual.geojson"):
        path = RAW_DIR / name
        if path.exists():
            gdf = gpd.read_file(path)
            gdf = gdf[gdf.geometry.notna() & gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
            if not gdf.empty:
                return gdf.set_crs("EPSG:4326", allow_override=True), name
    return None, None


def worldcover_water_points() -> np.ndarray:
    """UTM centres of 25 m pixels that are inland WorldCover water or wetland (sea excluded)."""
    inland, _, (tf, _, _, _, _) = water_masks()
    rows, cols = np.nonzero(inland)
    return np.column_stack([tf.c + (cols + 0.5) * tf.a, tf.f + (rows + 0.5) * tf.e])


def compute() -> pd.DataFrame:
    cells = load_grid()
    centres = np.column_stack([cells["x"].to_numpy(), cells["y"].to_numpy()])

    roads = gpd.read_file(RAW_DIR / "roads.geojson").to_crs(GRID_CRS)
    ways = gpd.read_file(RAW_DIR / "waterways.geojson").to_crs(GRID_CRS)
    drains = ways[ways["waterway"].isin(DRAIN_TYPES)]
    d_drain = nearest_dist(centres, densify_points(drains.geometry))

    rivers = densify_points(ways[ways["waterway"].isin(RIVER_TYPES)].geometry)
    osm_water, name = load_osm_water()
    if osm_water is not None:
        water = osm_water.to_crs(GRID_CRS)
        d_water = nearest_dist(centres, np.vstack([densify_points(water.geometry), rivers]))
        tree = STRtree(water.geometry.values)
        hit, _ = tree.query([Point(x, y) for x, y in centres], predicate="within")
        d_water[np.unique(hit)] = 0.0  # centre inside a water body
        source = f"OSM water/wetland polygons ({name}) + OSM rivers/canals"
    else:
        # pixel centres: a cell centre inside water lands within half a pixel diagonal (~18 m) of one
        d_water = nearest_dist(centres, np.vstack([worldcover_water_points(), rivers]))
        source = "ESA WorldCover 2021 classes 80+90 (25 m, >=50% water, sea removed) + OSM rivers/canals"
    (RAW_DIR / "water_source.txt").write_text(source + "\n")
    print("dist_water_m source:", source)

    return pd.DataFrame({
        "cell_id": cells["cell_id"].to_numpy(),
        "dist_drain_m": d_drain,
        "dist_water_m": d_water,
        "road_density": road_density_km_per_km2(roads, cells),
    })


def main():
    df = compute()
    df.to_parquet(RAW_DIR / "osm_features.parquet", index=False)
    print(df.describe().round(2).to_string())


if __name__ == "__main__":
    main()

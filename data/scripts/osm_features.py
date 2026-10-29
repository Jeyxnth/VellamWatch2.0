"""Per-cell OSM features: dist_drain_m, dist_water_m, road_density (km of road per km2).

All geometry work happens in UTM 44N (metres). Distances are measured from the cell centre
to the nearest feature, via a KD-tree on points densified along the lines / polygon outlines.
Cells whose centre is inside a water body get dist_water_m = 0.
"""
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely import STRtree

from data.config import CELL_M, GRID_CRS, RAW_DIR
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


def compute() -> pd.DataFrame:
    cells = load_grid()
    centres = np.column_stack([cells["x"].to_numpy(), cells["y"].to_numpy()])

    roads = gpd.read_file(RAW_DIR / "roads.geojson").to_crs(GRID_CRS)
    ways = gpd.read_file(RAW_DIR / "waterways.geojson").to_crs(GRID_CRS)
    water = gpd.read_file(RAW_DIR / "water.geojson").to_crs(GRID_CRS)

    drains = ways[ways["waterway"].isin(DRAIN_TYPES)]
    d_drain = nearest_dist(centres, densify_points(drains.geometry))

    rivers = ways[ways["waterway"].isin(RIVER_TYPES)]
    water_pts = np.vstack([densify_points(water.geometry), densify_points(rivers.geometry)])
    d_water = nearest_dist(centres, water_pts)
    # inside a water body -> 0
    tree = STRtree(water.geometry.values)
    from shapely.geometry import Point
    pts = [Point(x, y) for x, y in centres]
    inside = np.zeros(len(pts), dtype=bool)
    hit_pts, _ = tree.query(pts, predicate="within")
    inside[np.unique(hit_pts)] = True
    d_water[inside] = 0.0

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

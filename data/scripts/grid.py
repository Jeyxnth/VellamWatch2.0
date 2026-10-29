"""Build the ~250 m study grid in UTM 44N and export it to WGS84.

cell_id = r{row}_c{col}; row 0 is the southernmost row, col 0 the westernmost column.
The grid is the smallest UTM-aligned rectangle covering the study bbox, so cells
may overhang the bbox by up to one cell.
"""
import math

import geopandas as gpd
import numpy as np
from pyproj import Transformer
from shapely.geometry import box

from data.config import CELL_M, EAST, GRID_CRS, NORTH, PROCESSED_DIR, SOUTH, WEST


def build_grid() -> gpd.GeoDataFrame:
    """Return the grid as a GeoDataFrame in GRID_CRS with cell_id,row,col and UTM centre x,y."""
    to_utm = Transformer.from_crs("EPSG:4326", GRID_CRS, always_xy=True)
    xs, ys = to_utm.transform([WEST, EAST, WEST, EAST], [SOUTH, SOUTH, NORTH, NORTH])
    x0, y0 = min(xs), min(ys)
    n_cols = math.ceil((max(xs) - x0) / CELL_M)
    n_rows = math.ceil((max(ys) - y0) / CELL_M)

    rows, cols = np.meshgrid(np.arange(n_rows), np.arange(n_cols), indexing="ij")
    rows, cols = rows.ravel(), cols.ravel()
    minx = x0 + cols * CELL_M
    miny = y0 + rows * CELL_M
    geoms = [box(a, b, a + CELL_M, b + CELL_M) for a, b in zip(minx, miny)]
    gdf = gpd.GeoDataFrame(
        {
            "cell_id": [f"r{r}_c{c}" for r, c in zip(rows, cols)],
            "row": rows.astype(int),
            "col": cols.astype(int),
            "x": minx + CELL_M / 2,
            "y": miny + CELL_M / 2,
        },
        geometry=geoms,
        crs=GRID_CRS,
    )
    return gdf


def add_lat_lon(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    to_wgs = Transformer.from_crs(GRID_CRS, "EPSG:4326", always_xy=True)
    lon, lat = to_wgs.transform(gdf["x"].to_numpy(), gdf["y"].to_numpy())
    out = gdf.copy()
    out["lat"], out["lon"] = lat, lon
    return out


def load_grid() -> gpd.GeoDataFrame:
    """Grid in UTM with lat/lon of centres (rebuilt deterministically; cheap)."""
    return add_lat_lon(build_grid())


def sanity_check(gdf: gpd.GeoDataFrame) -> None:
    n = len(gdf)
    if not 20000 <= n <= 26000:
        raise ValueError(f"unexpected cell count {n} (expected about 23,000)")
    if gdf["cell_id"].duplicated().any():
        raise ValueError("duplicate cell_ids")
    if (gdf["row"].min(), gdf["col"].min()) != (0, 0):
        raise ValueError("row/col must start at 0")
    if len(set(gdf["row"])) != gdf["row"].max() + 1 or len(set(gdf["col"])) != gdf["col"].max() + 1:
        raise ValueError("row/col are not contiguous")
    if gdf["lat"].min() < SOUTH - 0.01 or gdf["lat"].max() > NORTH + 0.01:
        raise ValueError("cell centres outside the study latitude range")
    if gdf["lon"].min() < WEST - 0.01 or gdf["lon"].max() > EAST + 0.01:
        raise ValueError("cell centres outside the study longitude range")


def main() -> None:
    gdf = load_grid()
    sanity_check(gdf)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = gdf.to_crs("EPSG:4326")[["cell_id", "row", "col", "geometry"]]
    out.to_file(PROCESSED_DIR / "cells.geojson", driver="GeoJSON")
    print(f"cells.geojson: {len(out)} cells, rows 0-{gdf['row'].max()}, cols 0-{gdf['col'].max()}")
    print(f"centre lat {gdf['lat'].min():.4f}-{gdf['lat'].max():.4f}, lon {gdf['lon'].min():.4f}-{gdf['lon'].max():.4f}")


if __name__ == "__main__":
    main()

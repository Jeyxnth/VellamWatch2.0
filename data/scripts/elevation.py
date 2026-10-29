"""Elevation features from Copernicus DEM GLO-30 (AWS open data, no login).

Per cell: elevation_m (mean), slope_deg (mean), relief_m (max - min within the cell),
sink_depth_m (mean depth of filled sinks: morphological fill minus original).
relief_m is not in the contract, so it goes to features_extra.parquet, not features.parquet.
Note: Copernicus GLO-30 is a surface model (includes buildings and trees).
"""
import numpy as np
import pandas as pd
import rasterio
from rasterio.merge import merge
from skimage.morphology import reconstruction

from data.config import EAST, NORTH, RAW_DIR, SOUTH, WEST
from data.scripts.common import PIXEL_M, block_reduce, crop_padding, to_cell_vector, warp_to_grid
from data.scripts.grid import load_grid

DEM_URL = ("https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_{ns}_00_{ew}_00_DEM/"
           "Copernicus_DSM_COG_10_{ns}_00_{ew}_00_DEM.tif")
DEM_PATH = RAW_DIR / "dem_cop30.tif"
PAD_DEG = 0.03


def fetch_dem():
    """Crop the study area (plus padding) out of the Copernicus COG tiles and cache it."""
    if DEM_PATH.exists():
        return DEM_PATH
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    bounds = (WEST - PAD_DEG, SOUTH - PAD_DEG, EAST + PAD_DEG, NORTH + PAD_DEG)
    tiles = [DEM_URL.format(ns=ns, ew="E080") for ns in ("N12", "N13")]
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        srcs = [rasterio.open("/vsicurl/" + t) for t in tiles]
        try:
            mosaic, tf = merge(srcs, bounds=bounds)
            profile = srcs[0].profile
        finally:
            for s in srcs:
                s.close()
    profile.update(driver="GTiff", height=mosaic.shape[1], width=mosaic.shape[2], transform=tf,
                   compress="deflate", tiled=True, blockxsize=256, blockysize=256, count=1)
    with rasterio.open(DEM_PATH, "w", **profile) as dst:
        dst.write(mosaic[0], 1)
    return DEM_PATH


def slope_degrees(dem: np.ndarray, res_m: float = PIXEL_M) -> np.ndarray:
    gy, gx = np.gradient(dem, res_m)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def sink_depth(dem: np.ndarray) -> np.ndarray:
    """Depression depth: filled surface (reconstruction by erosion) minus original, always >= 0.

    The raster border is treated as an outlet, so water can leave the padded area.
    """
    d = np.nan_to_num(dem, nan=float(np.nanmin(dem)))
    seed = d.copy()
    seed[1:-1, 1:-1] = d.max()
    filled = reconstruction(seed, d, method="erosion")
    return filled - d


def compute() -> pd.DataFrame:
    grid = load_grid()
    dem, _ = warp_to_grid(fetch_dem())
    if np.isnan(dem).mean() > 0.5:
        raise RuntimeError("DEM reprojection produced mostly nodata")
    slope = slope_degrees(dem)
    sinks = sink_depth(dem)
    dem_c, slope_c, sinks_c = crop_padding(dem), crop_padding(slope), crop_padding(sinks)
    return pd.DataFrame({
        "cell_id": grid["cell_id"].to_numpy(),
        "elevation_m": to_cell_vector(block_reduce(dem_c, np.nanmean)),
        "slope_deg": to_cell_vector(block_reduce(slope_c, np.nanmean)),
        "sink_depth_m": to_cell_vector(block_reduce(sinks_c, np.nanmean)),
        "relief_m": to_cell_vector(block_reduce(dem_c, np.nanmax) - block_reduce(dem_c, np.nanmin)),
    })


def main():
    df = compute()
    df.to_parquet(RAW_DIR / "elevation_features.parquet", index=False)
    print(df.describe().round(3).to_string())


if __name__ == "__main__":
    main()

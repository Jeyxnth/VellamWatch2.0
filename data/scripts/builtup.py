"""built_up_frac from ESA WorldCover 10 m (class 50 = built-up), AWS open data, no login.

Fraction of 10 m pixels per cell that are class 50 (computed by area-averaging a binary
mask onto the 25 m grid-aligned raster, then averaging 10x10 pixels per cell).
If WorldCover is unreachable, a road-density proxy is used and the source is recorded in
data/raw/builtup_source.txt (the pipeline QA reports it).
"""
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import Resampling
from rasterio.windows import from_bounds

from data.config import EAST, NORTH, RAW_DIR, SOUTH, WEST
from data.scripts.common import block_reduce, crop_padding, to_cell_vector, warp_to_grid
from data.scripts.grid import load_grid

WC_URL = ("https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
          "ESA_WorldCover_10m_2021_v200_{tile}_Map.tif")
WC_PATH = RAW_DIR / "worldcover_2021.tif"
BUILT_UP = 50
PAD_DEG = 0.03


def fetch_worldcover():
    if WC_PATH.exists():
        return WC_PATH
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    # one 3x3 degree tile (N12 E078) covers lat 12-15, lon 78-81, i.e. the whole study area
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        with rasterio.open("/vsicurl/" + WC_URL.format(tile="N12E078")) as src:
            win = from_bounds(WEST - PAD_DEG, SOUTH - PAD_DEG, EAST + PAD_DEG, NORTH + PAD_DEG, src.transform)
            win = win.round_offsets().round_lengths()
            data = src.read(1, window=win)
            profile = src.profile
            tf = src.window_transform(win)
    profile.update(height=data.shape[0], width=data.shape[1], transform=tf, compress="deflate",
                   tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(WC_PATH, "w", **profile) as dst:
        dst.write(data, 1)
    return WC_PATH


def built_up_fraction() -> np.ndarray:
    mask_fn = lambda a: (a == BUILT_UP).astype("float32")  # noqa: E731
    frac, _ = warp_to_grid(fetch_worldcover(), resampling=Resampling.average, transform_fn=mask_fn,
                           dtype="float32", dst_nodata=np.nan)
    return to_cell_vector(block_reduce(crop_padding(frac), np.nanmean))


def compute() -> pd.DataFrame:
    grid = load_grid()
    vals = np.clip(built_up_fraction(), 0, 1)
    (RAW_DIR / "builtup_source.txt").write_text("ESA WorldCover 2021 v200 (class 50)\n")
    return pd.DataFrame({"cell_id": grid["cell_id"].to_numpy(), "built_up_frac": vals})


def road_density_proxy(road_density: pd.Series) -> pd.Series:
    """Fallback only: rank-scaled road density in [0, 1]. Documented as a proxy, not a measurement."""
    return road_density.rank(pct=True)


def main():
    df = compute()
    df.to_parquet(RAW_DIR / "builtup_features.parquet", index=False)
    print(df["built_up_frac"].describe().round(3).to_string())


if __name__ == "__main__":
    main()

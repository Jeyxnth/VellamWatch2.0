"""Helpers shared by the data scripts: cached downloads and raster alignment to the grid."""
import json
import time
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

from data.config import CELL_M, GRID_CRS, USER_AGENT
from data.scripts.grid import build_grid

PIXEL_M = 25.0  # raster working resolution; CELL_M / PIXEL_M must be an integer
K = int(round(CELL_M / PIXEL_M))
MARGIN_PX = 40  # padding around the grid so edge cells have neighbours (sink filling, slope)


def http_get(url: str, path: Path, *, params=None, retries: int = 3, timeout: int = 120) -> Path:
    """Download url to path unless it already exists (raw-data cache)."""
    path = Path(path)
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            r.raise_for_status()
            path.write_bytes(r.content)
            return path
        except requests.RequestException as exc:
            last = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"download failed: {url}: {last}")


def cached_json(url: str, path: Path, *, params=None, sleep: float = 0.0, **kw):
    """GET json with an on-disk cache; sleeps only after a real (uncached) request."""
    path = Path(path)
    fresh = not (path.exists() and path.stat().st_size > 0)
    http_get(url, path, params=params, **kw)
    if fresh and sleep:
        time.sleep(sleep)
    return json.loads(path.read_text(encoding="utf-8"))


def padded_raster_spec(grid=None):
    """(transform, height, width, n_rows, n_cols) of a PIXEL_M raster aligned to the grid, padded."""
    grid = build_grid() if grid is None else grid
    n_rows, n_cols = int(grid["row"].max()) + 1, int(grid["col"].max()) + 1
    x0 = float(grid["x"].min()) - CELL_M / 2
    y_top = float(grid["y"].max()) + CELL_M / 2
    tf = from_origin(x0 - MARGIN_PX * PIXEL_M, y_top + MARGIN_PX * PIXEL_M, PIXEL_M, PIXEL_M)
    return tf, n_rows * K + 2 * MARGIN_PX, n_cols * K + 2 * MARGIN_PX, n_rows, n_cols


def warp_to_grid(src_path, *, resampling=Resampling.bilinear, band=1, transform_fn=None,
                 dtype="float32", dst_nodata=np.nan):
    """Reproject a raster band onto the padded, grid-aligned UTM raster. Returns (array, spec)."""
    spec = padded_raster_spec()
    tf, h, w, _, _ = spec
    dst = np.full((h, w), dst_nodata, dtype=dtype)
    with rasterio.open(src_path) as src:
        data = src.read(band)
        nodata = src.nodata
        if transform_fn is not None:
            data = transform_fn(data)
            nodata = None
        reproject(
            source=data.astype(dtype), destination=dst,
            src_transform=src.transform, src_crs=src.crs,
            dst_transform=tf, dst_crs=GRID_CRS,
            resampling=resampling,
            src_nodata=nodata, dst_nodata=dst_nodata,
        )
    return dst, spec


def crop_padding(arr: np.ndarray) -> np.ndarray:
    return arr[MARGIN_PX:-MARGIN_PX, MARGIN_PX:-MARGIN_PX]


def block_reduce(arr: np.ndarray, func=np.nanmean) -> np.ndarray:
    """Reduce (n_rows*K, n_cols*K) pixels to (n_rows, n_cols) cell values; image row 0 is north."""
    h, w = arr.shape
    blocks = arr.reshape(h // K, K, w // K, K).transpose(0, 2, 1, 3).reshape(h // K, w // K, K * K)
    with np.errstate(all="ignore"):
        return func(blocks, axis=2)


def to_cell_vector(cell_grid_north_first: np.ndarray) -> np.ndarray:
    """(n_rows, n_cols) image-ordered array -> vector in cells.geojson order (row-major, row 0 = south)."""
    return np.flipud(cell_grid_north_first).ravel()

"""Merge the per-source feature tables into data/processed/features.parquet (contract section D).

Open-sea cells (sea_frac >= 0.5 from WorldCover) are dropped from BOTH cells.geojson and
features.parquet: they are not streets, and the sea would top any low-elevation ranking.
Row/col numbering is unchanged (still contiguous; trailing all-sea columns simply disappear).

features.parquet columns (exactly): cell_id, lat, lon, elevation_m, slope_deg, sink_depth_m,
dist_drain_m, dist_water_m, road_density, built_up_frac. relief_m (not in the contract) goes to
features_extra.parquet.
"""
import pandas as pd

from data.config import PROCESSED_DIR, RAW_DIR
from data.scripts.grid import load_grid

SEA_DROP = 0.5

COLUMNS = ["cell_id", "lat", "lon", "elevation_m", "slope_deg", "sink_depth_m",
           "dist_drain_m", "dist_water_m", "road_density", "built_up_frac"]


def main():
    full = load_grid()
    grid = full[["cell_id", "lat", "lon"]]
    elev = pd.read_parquet(RAW_DIR / "elevation_features.parquet")
    osm = pd.read_parquet(RAW_DIR / "osm_features.parquet")
    built = pd.read_parquet(RAW_DIR / "builtup_features.parquet")
    sea = built.set_index("cell_id")["sea_frac"]
    built = built.drop(columns="sea_frac")
    df = grid.merge(elev.drop(columns="relief_m"), on="cell_id", how="left") \
             .merge(osm, on="cell_id", how="left").merge(built, on="cell_id", how="left")[COLUMNS]
    if df.isna().any().any():
        raise RuntimeError(f"NaNs in features: {df.isna().sum()[df.isna().sum() > 0].to_dict()}")
    if len(df) != len(grid) or df["cell_id"].duplicated().any():
        raise RuntimeError("feature table does not match the grid")
    keep = sea.reindex(df["cell_id"]).to_numpy() < SEA_DROP
    df = df[keep].reset_index(drop=True)
    cells = full[keep].to_crs("EPSG:4326")[["cell_id", "row", "col", "geometry"]]
    for c in ("row", "col"):
        if cells[c].max() != cells[c].nunique() - 1:
            raise RuntimeError(f"dropping sea cells broke {c} contiguity")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    cells.to_file(PROCESSED_DIR / "cells.geojson", driver="GeoJSON")
    df.to_parquet(PROCESSED_DIR / "features.parquet", index=False)
    elev[elev.cell_id.isin(df.cell_id)][["cell_id", "relief_m"]].to_parquet(PROCESSED_DIR / "features_extra.parquet", index=False)
    print(f"dropped {int((~keep).sum())} open-sea cells; cells.geojson + features.parquet: {len(df)} cells, "
          f"rows 0-{cells.row.max()}, cols 0-{cells.col.max()}")


if __name__ == "__main__":
    main()

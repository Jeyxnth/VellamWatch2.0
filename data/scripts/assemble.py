"""Merge the per-source feature tables into data/processed/features.parquet (contract section D).

features.parquet columns (exactly): cell_id, lat, lon, elevation_m, slope_deg, sink_depth_m,
dist_drain_m, dist_water_m, road_density, built_up_frac. relief_m (not in the contract) goes to
features_extra.parquet.
"""
import pandas as pd

from data.config import PROCESSED_DIR, RAW_DIR
from data.scripts.grid import load_grid

COLUMNS = ["cell_id", "lat", "lon", "elevation_m", "slope_deg", "sink_depth_m",
           "dist_drain_m", "dist_water_m", "road_density", "built_up_frac"]


def main():
    grid = load_grid()[["cell_id", "lat", "lon"]]
    elev = pd.read_parquet(RAW_DIR / "elevation_features.parquet")
    osm = pd.read_parquet(RAW_DIR / "osm_features.parquet")
    built = pd.read_parquet(RAW_DIR / "builtup_features.parquet")
    df = grid.merge(elev.drop(columns="relief_m"), on="cell_id", how="left") \
             .merge(osm, on="cell_id", how="left").merge(built, on="cell_id", how="left")[COLUMNS]
    if df.isna().any().any():
        raise RuntimeError(f"NaNs in features: {df.isna().sum()[df.isna().sum() > 0].to_dict()}")
    if len(df) != len(grid) or df["cell_id"].duplicated().any():
        raise RuntimeError("feature table does not match the grid")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED_DIR / "features.parquet", index=False)
    elev[["cell_id", "relief_m"]].to_parquet(PROCESSED_DIR / "features_extra.parquet", index=False)
    print(f"features.parquet: {len(df)} rows x {len(df.columns)} columns")


if __name__ == "__main__":
    main()

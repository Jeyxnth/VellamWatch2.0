"""Recall of simple "urban-ness" rankings against the hotspot labels (no training).

Hotspot labels are centroids of reported, populated localities, so a ranking that only knows
"dense city" may already find them. This prints recall at the budgets used in BACKTEST.md so the
model can be compared against that confounder. Usage: python -m ml.scripts.urban_baseline
"""
import numpy as np
import pandas as pd

from ml.features import find_data_dir, load_features, load_hotspots

BUDGETS = (0.059, 0.10, 0.20, 0.40)
RANKINGS = {
    "road_density (high first)": lambda f: f.road_density,
    "built_up_frac (high first)": lambda f: f.built_up_frac,
    "elevation (low first)": lambda f: -f.elevation_m,
}


def recall_table(feats: pd.DataFrame, hot: pd.DataFrame) -> pd.DataFrame:
    rows = []
    tie_break = np.random.default_rng(0).normal(0, 1e-9, len(feats))
    for event, h in [("all", hot)] + list(hot.groupby("event")):
        pos = feats.cell_id.isin(h.cell_id).to_numpy()
        for name, fn in RANKINGS.items():
            order = np.argsort(-(fn(feats).to_numpy() + tie_break))
            row = {"event": event, "ranking": name, "n_pos": int(pos.sum())}
            for k in BUDGETS:
                row[f"recall@{k:.1%}"] = pos[order[: int(len(feats) * k)]].sum() / max(pos.sum(), 1)
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    d = find_data_dir()
    print(recall_table(load_features(d), load_hotspots(d)).to_string(
        index=False, float_format=lambda v: f"{v:.1%}"))


if __name__ == "__main__":
    main()

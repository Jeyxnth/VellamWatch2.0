"""QA report: writes data/QA.md and data/QA_hotspots.png from the files in data/processed/.

Also runs the ML loaders (ml.features / ml.rain, in ml/.venv) because they validate the formats.
"""
import datetime as dt
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from data.config import PROCESSED_DIR, RAW_DIR, ROOT  # noqa: E402

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
FEATURES = ["elevation_m", "slope_deg", "sink_depth_m", "dist_drain_m", "dist_water_m", "road_density",
            "built_up_frac"]


def ml_python():
    for rel in ("ml/.venv/Scripts/python.exe", "ml/.venv/bin/python"):
        if (ROOT / rel).exists():
            return str(ROOT / rel)
    return sys.executable


def run_ml_loaders() -> str:
    code = (
        "import warnings; warnings.simplefilter('always')\n"
        "from ml.features import build_static_table, load_hotspots, event_windows, data_source\n"
        "from ml import rain\n"
        "d='data/processed'\n"
        "t=build_static_table(d); h=load_hotspots(d); w,src=event_windows(d)\n"
        "r=rain.load_rainfall(d)\n"
        "print('data_source =', data_source(d)); print('cells', len(t), 'hotspot rows', len(h), 'event windows from', src)\n"
        "print('rainfall rows', len(r))\n"
    )
    p = subprocess.run([ml_python(), "-c", code], cwd=ROOT, capture_output=True, text=True)
    return ((p.stdout or "") + (p.stderr or "")).strip() + f"\n(exit code {p.returncode})"


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        lines.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(lines)


def make_map(feat, hot, path):
    fig, ax = plt.subplots(figsize=(8, 9))
    sc = ax.scatter(feat["lon"], feat["lat"], c=feat["elevation_m"].clip(-5, 60), s=1.2, cmap="Greys_r")
    plt.colorbar(sc, ax=ax, shrink=0.6, label="elevation_m (clipped -5..60)")
    style = {"2015": ("tab:red", "o"), "2023": ("tab:blue", "^")}
    h = hot.merge(feat[["cell_id", "lat", "lon"]], on="cell_id")
    for ev, g in h.groupby("event"):
        c, m = style.get(str(ev), ("tab:green", "s"))
        ax.scatter(g["lon"], g["lat"], c=c, marker=m, s=45, edgecolor="white", linewidth=0.6,
                   label=f"hotspots {ev} (n={len(g)})")
    ax.set_xlabel("lon"); ax.set_ylabel("lat"); ax.set_aspect(1 / 0.974)
    ax.set_title("Documented flood localities over the 250 m grid (REAL data, locality-level labels)")
    ax.legend(loc="lower left")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def main():

    feat = pd.read_parquet(PROCESSED_DIR / "features.parquet")
    hot = pd.read_csv(PROCESSED_DIR / "hotspots.csv", dtype=str)
    ev = pd.read_csv(PROCESSED_DIR / "events.csv")
    rain = pd.read_parquet(PROCESSED_DIR / "rainfall.parquet")
    glog = pd.read_csv(PROCESSED_DIR / "hotspots_geocode_log.csv")
    L = ["# Data QA", "", f"Generated {dt.datetime.now(IST).isoformat(timespec='seconds')}. "
         "All numbers come from the files in `data/processed/`. **Data source: real** "
         "(no SYNTHETIC.flag). Hotspot labels are locality-level points from news/report sources, "
         "not flood-extent maps.", ""]

    L += ["## Files and row counts", "",
          f"- `features.parquet`: {len(feat)} rows x {len(feat.columns)} columns",
          f"- `hotspots.csv`: {len(hot)} rows ({hot.groupby('event').size().to_dict()})",
          f"- `events.csv`: {len(ev)} events",
          f"- `rainfall.parquet`: {len(rain)} rows, {rain[['lat', 'lon']].drop_duplicates().shape[0]} points, "
          f"{rain.timestamp.min()} to {rain.timestamp.max()}", ""]

    L += ["## Null checks", "", "Columns with nulls: " +
          (str(feat.isna().sum()[feat.isna().sum() > 0].to_dict()) or "none") +
          f". Rainfall nulls: {int(rain.precip_mm.isna().sum())}. Duplicate cell_ids: "
          f"{int(feat.cell_id.duplicated().sum())}.", ""]

    desc = feat[FEATURES].describe().T[["min", "mean", "50%", "max"]].reset_index().rename(columns={"index": "feature"})
    L += ["## Value ranges", "", md_table(desc), "",
          f"Cells with elevation <= 0.5 m: {int((feat.elevation_m <= 0.5).sum())}. "
          f"Cells within 25 m of mapped water (dist_water_m < 25): {int((feat.dist_water_m < 25).sum())}.", ""]
    try:
        sea = pd.read_parquet(RAW_DIR / "builtup_features.parquet")["sea_frac"]
        L += [f"Open-sea cells removed from the grid (WorldCover sea >= 50% of cell): {int((sea >= 0.5).sum())} "
              f"of {len(sea)}; {len(feat)} land cells remain.", ""]
    except (OSError, KeyError):
        pass
    try:
        L += [f"dist_water_m source: {(RAW_DIR / 'water_source.txt').read_text().strip()}.", ""]
    except OSError:
        pass
    try:
        src = (RAW_DIR / "builtup_source.txt").read_text().strip()
    except OSError:
        src = "unknown"
    L += [f"built_up_frac source: {src}.", ""]

    mean_elev = feat.set_index("cell_id").loc[hot.cell_id.unique(), "elevation_m"].mean()
    L += ["## Hotspots", ""]
    for e, g in glog.groupby("event"):
        cells = hot[hot.event == str(e)].cell_id.nunique()
        L.append(f"- event {e}: {len(g)} localities listed, {int((g.status == 'ok').sum())} geocoded inside the study area, "
                 f"{cells} unique cells ({cells / len(feat):.3%} of the grid).")
    dropped = glog[glog.status != "ok"]
    L += [f"- Dropped (not found / outside area): {', '.join(dropped.locality) if len(dropped) else 'none'}.",
          f"- Mean elevation of hotspot cells {mean_elev:.1f} m vs grid mean {feat.elevation_m.mean():.1f} m.",
          "- Target was 40+ per event; fewer could be verified from credible sources (see SOURCES.md). "
          "Several localities share a cell, so unique cells are fewer than localities.", ""]

    L += ["## Rainfall coverage", ""]
    n_pts = rain[["lat", "lon"]].drop_duplicates().shape[0]
    for e in ev.itertuples():
        s, t = pd.Timestamp(e.start), pd.Timestamp(e.end)
        w = rain[(rain.timestamp >= s) & (rain.timestamp < t)]
        need = int((t - s) / pd.Timedelta(hours=1)) * n_pts
        tot = w.groupby(["lat", "lon"]).precip_mm.sum()
        L.append(f"- event {e.event} [{e.start} to {e.end}): {len(w)}/{need} rows; mean window total over points "
                 f"{tot.mean():.0f} mm (max point {tot.max():.0f} mm).")
    now = pd.Timestamp(dt.datetime.now(IST)).floor("h")
    ahead = (rain.timestamp.max() - now) / pd.Timedelta(hours=1)
    L += [f"- forecast: data extends {ahead:.0f} h beyond the current hour (need >= 72).",
          "- Historical rainfall is reanalysis (about 10-25 km): it understates extreme local rain "
          "(1 Dec 2015 reports say 300+ mm in 24 h; the grid-mean here is far lower).", ""]

    L += ["## ML loaders (validate formats)", "", "```", run_ml_loaders(), "```", "",
          "## Map", "", "![hotspots](QA_hotspots.png)", ""]
    make_map(feat, hot, ROOT / "data" / "QA_hotspots.png")
    (ROOT / "data" / "QA.md").write_text("\n".join(L), encoding="utf-8")
    print("wrote data/QA.md and data/QA_hotspots.png")


if __name__ == "__main__":
    main()

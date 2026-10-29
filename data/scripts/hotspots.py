"""Geocode documented flood localities (data/hotspot_sources.csv) to grid cells -> hotspots.csv.

Nominatim policy: at most 1 request/second, descriptive User-Agent, results cached in
data/raw/nominatim/. Localities that cannot be found inside the study bbox are DROPPED and
listed in data/processed/hotspots_geocode_log.csv (never guessed). Each hotspot row keeps its
source URL. A locality becomes ONE cell (its geocoded point), which is a coarse label: real
flooding covered more than one cell.
"""
import hashlib
import re

import pandas as pd

from data.config import EAST, NORTH, PROCESSED_DIR, RAW_DIR, ROOT, SOUTH, WEST
from data.scripts.common import cached_json
from data.scripts.grid import points_to_cells

INPUT = ROOT / "data" / "hotspot_sources.csv"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
CACHE = RAW_DIR / "nominatim"


def geocode(query: str):
    key = hashlib.sha1(query.encode("utf-8")).hexdigest()[:16]
    params = {"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "in",
              "viewbox": f"{WEST},{NORTH},{EAST},{SOUTH}", "bounded": 1}
    res = cached_json(NOMINATIM, CACHE / f"{key}.json", params=params, sleep=1.1)
    if res:
        return float(res[0]["lat"]), float(res[0]["lon"]), res[0].get("display_name", "")
    return None


def geocode_locality(locality: str, query: str):
    base = re.sub(r"\s*\(.*?\)", "", locality).strip()
    for q in (query, f"{base}, Chennai", base):
        hit = geocode(q)
        if hit:
            return hit + (q,)
    return None


def build() -> pd.DataFrame:
    src = pd.read_csv(INPUT, dtype=str)
    rows = []
    for rec in src.itertuples():
        hit = geocode_locality(rec.locality, rec.query)
        rows.append({"event": rec.event, "locality": rec.locality, "source": rec.source, "notes": rec.notes,
                     "lat": hit[0] if hit else None, "lon": hit[1] if hit else None,
                     "matched": hit[2] if hit else "", "query_used": hit[3] if hit else ""})
    log = pd.DataFrame(rows)
    found = log["lat"].notna()
    row, col, ok = (None, None, None)
    log["cell_id"] = None
    if found.any():
        row, col, ok = points_to_cells(log.loc[found, "lat"].astype(float).to_numpy(),
                                       log.loc[found, "lon"].astype(float).to_numpy())
        ids = [f"r{r}_c{c}" if good else None for r, c, good in zip(row, col, ok)]
        log.loc[found, "cell_id"] = ids
    log["status"] = log["cell_id"].map(lambda v: "ok" if v else "dropped (not found / outside study area)")
    return log


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    log = build()
    log.to_csv(PROCESSED_DIR / "hotspots_geocode_log.csv", index=False)
    good = log[log["status"] == "ok"]
    # one row per (cell, event); localities that share a cell are merged into the notes
    out = (good.groupby(["cell_id", "event"], sort=False)
           .agg(source=("source", "first"),
                notes=("locality", lambda s: "; ".join(s)))
           .reset_index())
    out["notes"] = out.apply(lambda r: r["notes"] + " | " + "; ".join(
        good[(good.cell_id == r["cell_id"]) & (good.event == r["event"])]["notes"]), axis=1)
    out = out[["cell_id", "event", "source", "notes"]]
    out.to_csv(PROCESSED_DIR / "hotspots.csv", index=False)
    for ev, g in log.groupby("event"):
        print(f"event {ev}: {len(g)} localities, {int((g.status == 'ok').sum())} geocoded, "
              f"{out[out.event == ev].shape[0]} unique cells")
    dropped = log[log["status"] != "ok"]
    if len(dropped):
        print("dropped:", ", ".join(f"{r.event}/{r.locality}" for r in dropped.itertuples()))


if __name__ == "__main__":
    main()

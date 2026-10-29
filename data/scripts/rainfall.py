"""rainfall.parquet from Open-Meteo: historical (archive API) for each event window +/- 2 days,
and the forecast API for the next 72 h (past_days gives recent hours too).

Points: a 0.1 degree lattice over the study bbox. Times: requested in Asia/Kolkata. Open-Meteo
labels each hourly value with the END of the hour it covers ("sum of the preceding hour"), so
every timestamp is shifted back one hour to the START of the hour, as the contract requires.
Output columns: timestamp (tz +05:30), lat, lon, precip_mm. Raw JSON is cached in
data/raw/openmeteo/. Open-Meteo is CC-BY 4.0 and non-commercial on the free tier.
"""
import datetime as dt

import numpy as np
import pandas as pd

from data.config import EAST, NORTH, PROCESSED_DIR, RAW_DIR, SOUTH, WEST
from data.scripts.common import cached_json

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CACHE = RAW_DIR / "openmeteo"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
STEP = 0.1
PAD_DAYS = 2
SLEEP_S = 5.0  # be polite: multi-location requests count once per point against the free quota


def lattice():
    lats = np.round(np.arange(SOUTH, NORTH + 1e-9, STEP), 4)
    lons = np.round(np.arange(WEST, EAST + 1e-9, STEP), 4)
    return [(float(a), float(b)) for a in lats for b in lons]


def _params(points, extra):
    return {"latitude": ",".join(f"{p[0]}" for p in points), "longitude": ",".join(f"{p[1]}" for p in points),
            "hourly": "precipitation", "timezone": "Asia/Kolkata", **extra}


def _frame(payload, points) -> pd.DataFrame:
    """One frame per response item; lat/lon are our requested lattice points (not the model cell centre)."""
    items = payload if isinstance(payload, list) else [payload]
    if len(items) != len(points):
        raise RuntimeError(f"Open-Meteo returned {len(items)} locations for {len(points)} requested")
    frames = []
    for it, (plat, plon) in zip(items, points):
        t = pd.to_datetime(it["hourly"]["time"])
        t = t.tz_localize(IST) - pd.Timedelta(hours=1)  # end-of-hour label -> start-of-hour
        frames.append(pd.DataFrame({
            "timestamp": t, "lat": plat, "lon": plon,
            "precip_mm": pd.to_numeric(pd.Series(it["hourly"]["precipitation"]), errors="coerce").to_numpy(),
        }))
    return pd.concat(frames, ignore_index=True)


def historical(events: pd.DataFrame) -> pd.DataFrame:
    points = lattice()
    out = []
    for e in events.itertuples():
        start = pd.Timestamp(e.start).date() - dt.timedelta(days=PAD_DAYS)
        end = (pd.Timestamp(e.end) - pd.Timedelta(seconds=1)).date() + dt.timedelta(days=PAD_DAYS)
        payload = cached_json(ARCHIVE_URL, CACHE / f"archive_{e.event}_{start}_{end}.json",
                              params=_params(points, {"start_date": str(start), "end_date": str(end)}),
                              sleep=SLEEP_S, timeout=180)
        out.append(_frame(payload, points))
    return pd.concat(out, ignore_index=True)


def forecast() -> pd.DataFrame:
    points = lattice()
    stamp = dt.datetime.now(IST).strftime("%Y%m%d_%H")
    payload = cached_json(FORECAST_URL, CACHE / f"forecast_{stamp}.json",
                          params=_params(points, {"past_days": 3, "forecast_days": 5}),
                          sleep=SLEEP_S, timeout=180)
    return _frame(payload, points)


def main():
    events = pd.read_csv(PROCESSED_DIR / "events.csv")
    hist, fc = historical(events), forecast()
    df = pd.concat([hist, fc], ignore_index=True)
    df = df.dropna(subset=["precip_mm"]).drop_duplicates(["timestamp", "lat", "lon"], keep="first")
    df = df.sort_values(["timestamp", "lat", "lon"]).reset_index(drop=True)
    df.to_parquet(PROCESSED_DIR / "rainfall.parquet", index=False)
    print(f"rainfall.parquet: {len(df)} rows, {df[['lat', 'lon']].drop_duplicates().shape[0]} points, "
          f"{df.timestamp.min()} to {df.timestamp.max()}")
    for e in events.itertuples():
        w = df[(df.timestamp >= pd.Timestamp(e.start)) & (df.timestamp < pd.Timestamp(e.end))]
        tot = w.groupby(["lat", "lon"]).precip_mm.sum().mean()
        print(f"event {e.event}: mean-over-points window total {tot:.1f} mm")


if __name__ == "__main__":
    main()

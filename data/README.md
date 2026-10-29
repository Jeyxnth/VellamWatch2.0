# VellamWatch data pipeline

Builds the contract files (docs/contract.md section D) in `data/processed/` from real public sources. Sources, licences and decisions: [SOURCES.md](SOURCES.md). Quality report: [QA.md](QA.md).

## Setup (Windows, from the repo root)
```
python -m venv data/.venv
data/.venv/Scripts/python -m pip install -r data/requirements.txt
```
The QA step also calls the ML loaders, so set up `ml/.venv` as in [ml/README.md](../ml/README.md).

## Run
```
data/.venv/Scripts/python -m data.run_all                 # all steps
data/.venv/Scripts/python -m data.run_all --from rainfall # resume from a step
data/.venv/Scripts/python -m data.run_all --only qa       # one step
data/.venv/Scripts/python -m pytest data/tests -q
```
Steps: `grid, osm, elevation, osm_features, builtup, events, rainfall, hotspots, assemble, qa`. Raw downloads are cached in `data/raw/` (git-ignored). Delete a raw file to refetch it. The forecast is cached per hour, so re-running `rainfall` refreshes it.

## Outputs (data/processed/)
| File | Content |
|---|---|
| `cells.geojson` | 250 m grid (UTM 44N, exported to WGS84): `cell_id`, `row`, `col`; land cells only (open sea removed) |
| `features.parquet` | contract feature columns, one row per cell |
| `features_extra.parquet` | `relief_m` (not in the contract) |
| `rainfall.parquet` | hourly precipitation, hour-start timestamps in +05:30 |
| `events.csv` | event windows (2015, 2023) |
| `hotspots.csv` | flooded localities -> cells, with source URL |
| `hotspots_geocode_log.csv` | every locality, geocode result, kept/dropped |

Hand-curated input: `data/hotspot_sources.csv` (event, locality, geocoding query, source URL, notes). Add a row only if the source names that locality as flooded in that event.

## Water bodies: WorldCover now, OSM optional
Water bodies and wetlands currently come from ESA WorldCover (classes 80, 90), because the OSM water query timed out on every public Overpass server. To use OSM polygons instead:
1. Open https://overpass-turbo.eu and run:
```
[out:json][timeout:300];
(
  way["natural"="water"](12.85,80.05,13.25,80.35);
  way["natural"="wetland"](12.85,80.05,13.25,80.35);
  way["landuse"="reservoir"](12.85,80.05,13.25,80.35);
  way["waterway"="riverbank"](12.85,80.05,13.25,80.35);
  relation["natural"="water"](12.85,80.05,13.25,80.35);
  relation["natural"="wetland"](12.85,80.05,13.25,80.35);
  relation["landuse"="reservoir"](12.85,80.05,13.25,80.35);
);
out body geom;
```
2. Click Export, then GeoJSON, and save the file as `data/raw/water_manual.geojson`.
3. Re-run from `osm_features`. The pipeline uses `water.geojson` if present, else `water_manual.geojson`, else WorldCover. `data/raw/water_source.txt` and QA.md record which one was used.

## Honesty notes
- Hotspots are named localities geocoded to one cell each, not flood-extent maps; they mark where flooding was reported, not every flooded cell.
- Historical rainfall is reanalysis and understates local extremes (see QA.md).
- Everything here is labelled real data: no file in `data/processed/` is synthetic.

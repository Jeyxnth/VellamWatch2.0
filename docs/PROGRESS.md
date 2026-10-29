# VellamWatch progress log

Read this first at the start of every session. Update after every task.

## Standing rules (short)
No AI-tool mentions or co-author trailers anywhere (commits, code, docs); commits carry only the configured git identity. Honest data labelling (real vs synthetic). Secrets in `.env` only. Phase gates: tests, commit, push main, tag, short status, STOP for "next". Contract changes: propose, apply, bump version, changelog.

## Plan
- **Phase 0** Repo setup: DONE
- **Phase 1** Real data pipeline (grid, DEM, OSM, WorldCover, rainfall, events/hotspots, SOURCES, QA, real train + backtest). Tag `phase-1-data`
- **Phase 2** Backend (FastAPI, mock mode, SQLite reports). Tag `phase-2-backend`
- **Phase 3** Voice and vision (alerts EN/TA, TTS, photo verification). Tag `phase-3-voice-vision`
- **Phase 4** Frontend (React, Vite, Leaflet). Tag `phase-4-frontend`
- **Phase 5** Integration, demo, deployment bundle. Tag `phase-5-demo`

## Status
### Phase 0 (done)
- Old repo (Jeyxnth/VellamWatch) cloned, `main` fast-forwarded to `origin/data` (teammate's `data/scripts/fetch_osm.py`, history preserved).
- All ROLE.md / HANDOFF.md / AI_CONTEXT.md removed.
- Remote retargeted to https://github.com/Jeyxnth/vellamwatch2.0.
- ML verified: `ml/.venv` created, `python -m ml.bootstrap_synthetic` OK, `pytest ml/tests -q` = 84 passed.

### Phase 1 (done, tag phase-1-data)
- Grid 23,318 cells (178 x 131); 5,051 open-sea cells removed -> 18,267 land cells.
- Features: Copernicus DEM (elevation, slope, sink depth; relief in features_extra), WorldCover built-up, OSM roads/waterways, WorldCover inland water + wetland for dist_water_m.
- Rainfall: Open-Meteo, 20 points, both event windows +/- 2 days and >= 72 h forecast.
- Hotspots: 2015 = 22 localities / 21 cells; 2023 = 32 localities / 31 cells; 42 unique cells. All with source URLs.
- QA: data/QA.md + QA_hotspots.png; ML loaders accept every file (data_source = real).
- Real model trained (ml/artifacts/model), backtest in ml/BACKTEST.md.
- Backtest (honest): spatial CV recall@10% 38.1% (lift 3.8x) vs lowest-elevation 2.4%; BUT "highest road density" alone also gets 38.1% -> the model mostly learns "dense, reported city". Event hold-out: 2015->2023 recall@10% 61% (road density 45%), 2023->2015 67% (road density 38%). Replay 2023 at a 40% budget: 93.5% vs low-elev 54.8% (built-up 90%). Replay 2015 at 5.9% budget: 61.9% vs low-elev 0% (road density 29%).

## Decisions
- vellamwatch2.0 `main` already held a commit with an AI co-author trailer; per user choice, remote main was force-pushed with clean history.
- Python 3.10.11 on Windows; `ml/.venv` for ML, `data/.venv` for the data pipeline (geopandas, rasterio).
- No usable flood-extent map for either event (Copernicus EMS: none found; UNOSAT 2015 only Nov imagery; NRSC Michaung only PDF). Labels = named localities geocoded to one cell each.
- Hotspot counts are below the 40+/event target: only localities named as flooded in pages we could read were kept; unverifiable ones (e.g. Manali 2023) were dropped.
- Event "2015" = 1-2 Dec deluge window (30 Nov - 3 Dec); November spells excluded. "2023" = 3-6 Dec (Michaung).
- Open-Meteo hourly values are end-of-hour labelled; shifted -1 h to hour-start per contract.
- features.parquet keeps exactly the contract columns; relief_m goes to features_extra.parquet.
- Small processed files committed (hotspots.csv, hotspots_geocode_log.csv, events.csv); big ones stay git-ignored until the Phase 5 runtime bundle.
- OSM water query failed on every Overpass server; user chose ESA WorldCover classes 80/90 for water bodies (OSM polygons still used automatically if a water file appears).
- Open-sea cells dropped from cells.geojson/features.parquet (sea would top any low-elevation ranking). No contract change needed: row/col stay contiguous.
- Policy table NOT tuned on the backtest results.

## Open issues
- GitHub MCP connector failed to connect in the tool session (does not affect git push).
- Reanalysis rainfall understates 2015 badly (grid-mean ~45 mm on 1 Dec vs 300+ mm reported), so the 2015 replay is driven by a weak storm signal (severity 0.32, 5.9% high budget).
- Hotspots below the 40/event target; labels are locality centroids (reporting bias toward dense areas).
- Model gain over an urban-density baseline is modest; more/better labels (ward-level lists, flood-extent maps) are the main lever.

## Commands
```
data/.venv/Scripts/python -m pip install -r data/requirements.txt
data/.venv/Scripts/python -m data.run_all            # or --from STEP / --only STEP
data/.venv/Scripts/python -m pytest data/tests -q
ml/.venv/Scripts/python -m ml.bootstrap_synthetic
ml/.venv/Scripts/python -m pytest ml/tests -q
```

## Next
Phase 2: FastAPI backend (backend/) per contract section B, mock mode, SQLite reports. Waiting for the user's "next".

# VellamWatch

Street-level flood risk and "what to do" alerts for Chennai ("vellam" is Tamil for flood). Hackathon project, built solo.

Tagline: *Know your street before the water does.*

The system ranks ~250 m grid cells by flood-hotspot risk for the next 24-72 h and turns the ranking into short alerts in English and Tamil, with audio and photo-report verification.

## Honesty notes

- **Ranking, not depth.** We claim hotspot RANKING only. `risk_score` is not a probability and not a flood depth.
- **The rain stage is a policy, not a fitted model.** How much of the study area is flagged as high/medium for a given forecast is set by policy targets in `ml/config.py`. They are not learned from data.
- **Synthetic vs real.** Any model or data built from `ml/synthetic/` is a pipeline test only. Every API response and UI must show `data_source` (`real` or `synthetic`). Synthetic runs print `SYNTHETIC DATA - PIPELINE TEST ONLY - NOT RESULTS`.
- **No invented hotspots.** Every hotspot in `data/processed/hotspots.csv` must carry a real source URL; locations that cannot be verified are dropped.
- Tamil text is machine/template generated and unreviewed until a native speaker checks it.

## Layout

| Folder | What |
|---|---|
| `data/` | Real data pipeline: grid, elevation, OSM, rainfall, events, hotspots |
| `ml/` | Susceptibility model, rain-budget ranking, backtest, `predict` API |
| `backend/` | FastAPI service implementing `docs/contract.md` (Phase 2) |
| `voice_vision/` | Alert text, TTS, photo verification (Phase 3) |
| `frontend/` | React + Vite + Leaflet map (Phase 4) |
| `docs/` | `contract.md` (spec, v1.1), `PROGRESS.md` (project memory) |

## Running each part (Windows; run from the repo root)

**ML (works now, synthetic data):**
```
python -m venv ml/.venv
ml/.venv/Scripts/python -m pip install -r ml/requirements.txt
ml/.venv/Scripts/python -m ml.bootstrap_synthetic
ml/.venv/Scripts/python -m pytest ml/tests -q
```
Details: [ml/README.md](ml/README.md).

**Data:** `data/scripts/fetch_osm.py` downloads OSM roads and waterways today. The full pipeline (`python -m data.run_all`) arrives in Phase 1.

**Backend, voice/vision, frontend:** planned in Phases 2-4; run instructions will be added to each folder's README.

## Licences and attribution

OSM data is ODbL (c) OpenStreetMap contributors. Other sources will be listed in `data/SOURCES.md` once the data pipeline lands.

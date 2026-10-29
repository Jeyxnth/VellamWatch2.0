# VellamWatch progress log

Read this first at the start of every session. Update after every task.

## Standing rules (short)
No AI/Claude mentions or co-author trailers anywhere (commits, code, docs). Honest data labelling (real vs synthetic). Secrets in `.env` only. Phase gates: tests, commit, push main, tag, short status, STOP for "next". Contract changes: propose, apply, bump version, changelog.

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

## Decisions
- vellamwatch2.0 `main` already held a commit with an AI co-author trailer; per user choice, remote main was force-pushed with clean history.
- Python 3.10.11 on Windows; commands use `ml/.venv/Scripts/python`.

## Open issues
- GitHub MCP connector failed to connect in the tool session (does not affect git push).

## Commands
```
ml/.venv/Scripts/python -m ml.bootstrap_synthetic
ml/.venv/Scripts/python -m pytest ml/tests -q
```

## Next
Phase 1, step 1: grid generator (UTM 44N, ~250 m cells, 12.85-13.25 N, 80.05-80.35 E).

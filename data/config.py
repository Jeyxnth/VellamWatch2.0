"""Shared constants and paths for the data pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

# Study area (WGS84)
SOUTH, WEST, NORTH, EAST = 12.85, 80.05, 13.25, 80.35

# Grid
GRID_CRS = "EPSG:32644"  # UTM zone 44N
CELL_M = 250.0

USER_AGENT = "VellamWatchDataPipeline/1.0 (student flood-risk research project; contact via GitHub Jeyxnth)"

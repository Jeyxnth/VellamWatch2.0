"""One entry point for the whole data pipeline:  python -m data.run_all

Steps are re-runnable; raw downloads are cached in data/raw/. Use --from STEP to resume,
--only STEP to run one step. Steps: grid, osm, elevation, osm_features, builtup, events,
rainfall, hotspots, assemble, qa.
"""
import argparse

from data.scripts import (assemble, builtup, elevation, events, fetch_osm, grid, hotspots, osm_features, qa,
                          rainfall)

STEPS = [
    ("grid", grid.main),
    ("osm", fetch_osm.main),
    ("elevation", elevation.main),
    ("osm_features", osm_features.main),
    ("builtup", builtup.main),
    ("events", events.main),
    ("rainfall", rainfall.main),
    ("hotspots", hotspots.main),
    ("assemble", assemble.main),
    ("qa", qa.main),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", choices=[s for s, _ in STEPS])
    ap.add_argument("--only", choices=[s for s, _ in STEPS])
    args = ap.parse_args()
    names = [s for s, _ in STEPS]
    for name, fn in STEPS:
        if args.only and name != args.only:
            continue
        if args.start and names.index(name) < names.index(args.start):
            continue
        print(f"\n=== {name} ===")
        fn()


if __name__ == "__main__":
    main()

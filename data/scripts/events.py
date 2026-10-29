"""events.csv: the two documented flood events and their rainfall windows.

Windows are ISO 8601 with +05:30; start inclusive, end exclusive. ml.backtest replays an event
with as_of = window start, so the window starts just before the main rain.

DECISIONS (documented in data/SOURCES.md):
- "2015" is the 1-2 December 2015 deluge only (window 30 Nov 00:00 to 3 Dec 00:00 IST). Every
  hotspot source describes that spell (Adyar breach, Chembarambakkam release, 1 Dec ~300-490 mm
  in 24 h). Earlier November 2015 spells (about 8-17 Nov) also flooded parts of the city; they
  are NOT in this window, so flooding that happened only then is not represented.
- "2023" is Cyclone Michaung (3 Dec 00:00 to 6 Dec 00:00 IST): heavy rain from the evening of
  3 Dec, peak on 4 Dec (Nungambakkam about 300+ mm in 24 h), landfall in Andhra on 5 Dec; water
  stood in the city through 6-7 Dec. The start matches the demo replay as_of in the contract.
"""
import pandas as pd

from data.config import PROCESSED_DIR

EVENTS = [
    ("2015", "2015-11-30T00:00:00+05:30", "2015-12-03T00:00:00+05:30"),
    ("2023", "2023-12-03T00:00:00+05:30", "2023-12-06T00:00:00+05:30"),
]


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(EVENTS, columns=["event", "start", "end"])
    df.to_csv(PROCESSED_DIR / "events.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()

import pandas as pd

from ml.scripts.urban_baseline import recall_table


def test_recall_table_finds_dense_hotspots():
    feats = pd.DataFrame({
        "cell_id": [f"r0_c{i}" for i in range(20)],
        "road_density": list(range(20)),
        "built_up_frac": [0.0] * 20,
        "elevation_m": list(range(20)),
    })
    hot = pd.DataFrame({"cell_id": ["r0_c19", "r0_c18"], "event": ["2023", "2023"]})
    t = recall_table(feats, hot)
    road = t[(t.event == "all") & t.ranking.str.startswith("road")].iloc[0]
    low = t[(t.event == "all") & t.ranking.str.startswith("elevation")].iloc[0]
    assert road["recall@10.0%"] == 1.0 and low["recall@10.0%"] == 0.0 and road["n_pos"] == 2

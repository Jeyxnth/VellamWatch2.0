import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Polygon

from data.scripts import events, rainfall
from data.scripts.osm_features import densify_points, nearest_dist


def test_rainfall_shifts_to_hour_start_and_uses_requested_points():
    payload = [{"latitude": 12.849, "longitude": 80.05,
                "hourly": {"time": ["2023-12-04T01:00", "2023-12-04T02:00"], "precipitation": [1.5, None]}}]
    df = rainfall._frame(payload, [(12.85, 80.05)])
    assert str(df.timestamp.iloc[0]) == "2023-12-04 00:00:00+05:30"
    assert df.lat.iloc[0] == 12.85 and df.precip_mm.iloc[0] == 1.5 and np.isnan(df.precip_mm.iloc[1])


def test_rainfall_rejects_location_mismatch():
    with pytest.raises(RuntimeError):
        rainfall._frame([], [(12.85, 80.05)])


def test_lattice_spacing():
    pts = rainfall.lattice()
    assert len(pts) == 20 and pts[0] == (12.85, 80.05) and pts[-1] == (13.25, 80.35)


def test_events_are_valid_windows():
    for name, start, end in events.EVENTS:
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        assert s.utcoffset() == pd.Timedelta(hours=5, minutes=30) and e > s


def test_densify_and_nearest_distance():
    line = LineString([(0, 0), (100, 0)])
    pts = densify_points([line], step=25)
    assert len(pts) == 5
    d = nearest_dist(np.array([[50.0, 30.0]]), pts)
    assert abs(d[0] - 30.0) < 1e-9
    poly_pts = densify_points([Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])], step=5)
    assert len(poly_pts) >= 8


def test_nearest_dist_without_features_is_capped():
    from data.scripts.osm_features import MAX_DIST_M
    assert nearest_dist(np.zeros((2, 2)), np.empty((0, 2)))[0] == MAX_DIST_M

import numpy as np

from data.scripts.common import K, block_reduce, to_cell_vector
from data.scripts.elevation import sink_depth, slope_degrees


def test_sink_depth_fills_pit():
    dem = np.full((30, 30), 10.0)
    dem[10:15, 10:15] = 7.0
    d = sink_depth(dem)
    assert d[12, 12] == 3.0 and d[0, 0] == 0.0 and (d >= 0).all()


def test_sink_depth_slope_has_no_sinks():
    dem = np.add.outer(np.arange(30.0), np.zeros(30))
    assert sink_depth(dem).max() == 0.0


def test_slope_known():
    dem = np.add.outer(np.arange(20.0), np.zeros(20))  # 1 m per pixel
    s = slope_degrees(dem, res_m=1.0)
    assert abs(s[10, 10] - 45.0) < 1e-6


def test_block_reduce_and_ordering():
    arr = np.zeros((2 * K, 3 * K))
    arr[:K, :K] = 5.0  # north-west cell in image order
    blocks = block_reduce(arr)
    assert blocks.shape == (2, 3) and blocks[0, 0] == 5.0
    vec = to_cell_vector(blocks)
    # image row 0 is north -> cell row 1; vector index = row*3+col
    assert vec[1 * 3 + 0] == 5.0

from data.scripts.grid import load_grid, sanity_check


def test_grid_shape_and_ids():
    g = load_grid()
    sanity_check(g)
    assert len(g) == (g["row"].max() + 1) * (g["col"].max() + 1)
    assert g.loc[(g.row == 3) & (g.col == 7), "cell_id"].iloc[0] == "r3_c7"


def test_row0_south_col0_west():
    g = load_grid()
    assert g[g.row == 0]["lat"].mean() < g[g.row == g.row.max()]["lat"].mean()
    assert g[g.col == 0]["lon"].mean() < g[g.col == g.col.max()]["lon"].mean()


def test_cell_size_250m():
    g = load_grid()
    b = g.geometry.iloc[0].bounds
    assert abs((b[2] - b[0]) - 250) < 1e-6 and abs((b[3] - b[1]) - 250) < 1e-6

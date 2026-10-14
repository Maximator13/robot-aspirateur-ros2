import math

import numpy as np

from aspi_bot.planning import (
    boustrophedon_waypoints, cell_to_world, coverage_percent, mark_covered,
    occupancy_to_free, reachable_mask, world_to_cell,
)

RES = 0.05


def room(h, w):
    g = np.zeros((h, w), dtype=int)
    g[0, :] = g[-1, :] = 100
    g[:, 0] = g[:, -1] = 100
    return g


def free_of(g):
    h, w = g.shape
    return occupancy_to_free(g.flatten().tolist(), w, h)


def reach_of(g, start):
    return reachable_mask(free_of(g), start, RES)


def simulate_sweep(reachable, wps, radius_cells):
    covered = np.zeros_like(reachable)
    i = 0
    while i < len(wps):
        j = i
        while j + 1 < len(wps) and abs(wps[j + 1][1] - wps[i][1]) < 1e-9:
            j += 1
        _, c0 = world_to_cell(wps[i][0], wps[i][1], 0, 0, RES)
        r0, c1 = world_to_cell(wps[j][0], wps[j][1], 0, 0, RES)
        for c in range(min(c0, c1), max(c0, c1) + 1):
            mark_covered(covered, reachable, r0, c, radius_cells)
        i = j + 1
    return covered


def test_occupancy_seuils():
    free = occupancy_to_free([0, 49, 50, 100, -1, 10], 6, 1)
    assert free.tolist() == [[True, True, False, False, False, True]]


def test_occupancy_ordre_ligne_major():
    free = occupancy_to_free([0, 100, 0,
                              100, 0, 100], 3, 2)
    assert free.shape == (2, 3)
    assert free[0].tolist() == [True, False, True]
    assert free[1].tolist() == [False, True, False]


def test_world_cell_aller_retour_origine_non_nulle():
    ox, oy = -1.5, 2.0
    for row, col in [(0, 0), (3, 7), (20, 11)]:
        x, y = cell_to_world(row, col, ox, oy, RES)
        assert world_to_cell(x, y, ox, oy, RES) == (row, col)


def test_cell_to_world_centre():
    x, y = cell_to_world(0, 0, -1.0, 2.0, RES)
    assert math.isclose(x, -1.0 + 0.5 * RES)
    assert math.isclose(y, 2.0 + 0.5 * RES)


def test_world_to_cell_coordonnees_negatives():
    assert world_to_cell(-0.01, -0.01, 0.0, 0.0, RES) == (-1, -1)


def test_reachable_piece_vide():
    m = reach_of(room(60, 60), (30, 30))
    assert m[30, 30]
    assert not m[0, :].any() and not m[:, 0].any()
    assert not m[1:3, 1:59].any()
    assert m[10:50, 10:50].all()


def test_reachable_pilier():
    g = room(60, 60)
    g[28:32, 28:32] = 100
    m = reach_of(g, (10, 10))
    assert not m[28:32, 28:32].any()
    assert not m[26:34, 26:34].any()
    assert m[10, 10] and m[50, 50]


def test_reachable_couloir_en_L_connexe():
    g = np.full((60, 60), 100)
    g[10:20, 10:50] = 0
    g[10:50, 10:20] = 0
    m = reach_of(g, (15, 45))
    assert m[15, 45] and m[45, 15]
    assert m[15, 15]


def test_reachable_deux_pieces_separees():
    g = np.full((30, 70), 100)
    g[3:27, 3:30] = 0
    g[3:27, 40:67] = 0
    m = reach_of(g, (15, 15))
    assert m[15, 15]
    assert not m[:, 35:].any()


def test_reachable_depart_dans_obstacle():
    g = room(60, 60)
    g[28:32, 28:32] = 100
    m = reach_of(g, (30, 30))
    assert m.any()
    assert not m[30, 30]


def test_reachable_tout_obstacle():
    m = reach_of(np.full((20, 20), 100), (10, 10))
    assert not m.any()


def test_reachable_couloir_trop_etroit():
    g = np.full((30, 60), 100)
    g[14:16, 3:57] = 0
    assert not reach_of(g, (14, 30)).any()


def test_mark_covered_limite_a_reachable():
    reachable = np.zeros((20, 20), dtype=bool)
    reachable[5:15, 5:15] = True
    covered = np.zeros_like(reachable)
    n = mark_covered(covered, reachable, 10, 10, 3)
    assert n > 0
    assert not (covered & ~reachable).any()
    assert covered[10, 10]
    assert n == int(covered.sum())


def test_mark_covered_deuxieme_appel_zero():
    reachable = np.ones((20, 20), dtype=bool)
    covered = np.zeros_like(reachable)
    assert mark_covered(covered, reachable, 10, 10, 3) > 0
    assert mark_covered(covered, reachable, 10, 10, 3) == 0


def test_mark_covered_bord_de_grille():
    reachable = np.ones((10, 10), dtype=bool)
    covered = np.zeros_like(reachable)
    assert mark_covered(covered, reachable, 0, 0, 3) > 0
    assert mark_covered(covered, reachable, 9, 9, 3) > 0
    mark_covered(covered, reachable, -5, 20, 3)


def test_coverage_percent():
    empty = np.zeros((5, 5), dtype=bool)
    assert coverage_percent(np.zeros((5, 5), dtype=bool), empty) == 0.0
    reachable = np.zeros((5, 5), dtype=bool)
    reachable[1:3, 1:3] = True
    covered = np.zeros_like(reachable)
    covered[1, 1] = True
    assert math.isclose(coverage_percent(covered, reachable), 25.0)
    assert math.isclose(coverage_percent(reachable.copy(), reachable), 100.0)


def wp_cell(wp, ox=0.0, oy=0.0):
    return world_to_cell(wp[0], wp[1], ox, oy, RES)


def test_boustro_piece_vide():
    reachable = reach_of(room(60, 60), (30, 30))
    wps = boustrophedon_waypoints(reachable, 0.0, 0.0, RES, 0.18)
    assert len(wps) >= 4
    assert all(reachable[wp_cell(w)] for w in wps)
    yaws = [w[2] for w in wps]
    assert yaws[0] == 0.0
    assert math.isclose(yaws[-1], 0.0) or math.isclose(yaws[-1], math.pi)
    assert 0.0 in yaws and any(math.isclose(y, math.pi) for y in yaws)
    ligne_yaws = [yaws[i] for i in range(0, len(yaws), 2)]
    for a, b in zip(ligne_yaws, ligne_yaws[1:]):
        assert not math.isclose(a, b)
    ys = sorted({round(w[1], 6) for w in wps})
    for a, b in zip(ys, ys[1:]):
        assert abs((b - a) - 0.18) <= RES + 1e-6


def test_boustro_pilier():
    g = room(60, 60)
    vide = reach_of(g, (30, 30))
    n_vide = len(boustrophedon_waypoints(vide, 0.0, 0.0, RES, 0.18))
    g[26:34, 26:34] = 100
    reachable = reach_of(g, (10, 10))
    wps = boustrophedon_waypoints(reachable, 0.0, 0.0, RES, 0.18)
    assert len(wps) > n_vide
    assert all(reachable[wp_cell(w)] for w in wps)
    assert all(not (26 <= wp_cell(w)[0] < 34 and 26 <= wp_cell(w)[1] < 34) for w in wps)


def test_boustro_masque_vide():
    assert boustrophedon_waypoints(np.zeros((20, 20), dtype=bool), 0.0, 0.0, RES) == []


def test_boustro_couverture_piece_vide_95_pourcent():
    reachable = reach_of(room(60, 60), (30, 30))
    wps = boustrophedon_waypoints(reachable, 0.0, 0.0, RES, 0.18)
    covered = simulate_sweep(reachable, wps, round(0.09 / RES))
    pct = coverage_percent(covered, reachable)
    print(f'couverture pièce vide simulée : {pct:.2f} %')
    assert pct >= 95.0

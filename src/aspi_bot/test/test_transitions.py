"""Tests de plan_transitions (Python pur, sans ROS) sur de petites grilles faites à la main.

Les grilles sont directement des masques « atteignables » (True = le robot peut passer),
résolution 0.05 m, origine (0, 0) : le centre de la cellule (row, col) est en
((col + 0.5) * 0.05, (row + 0.5) * 0.05).
"""

import math

import numpy as np

from aspi_bot.planning import (
    boustrophedon_waypoints, plan_transitions, reachable_mask, occupancy_to_free,
)

RES = 0.05
MAX_STEP = 0.3
TOL = 1e-9


# ---------- helpers ----------

def centre(row, col, yaw=0.0):
    """Waypoint (x, y, yaw) au centre de la cellule (row, col)."""
    return ((col + 0.5) * RES, (row + 0.5) * RES, yaw)


def plan(mask, wps, max_step=MAX_STEP):
    return plan_transitions(mask, wps, 0.0, 0.0, RES, max_step)


def leg_in_mask(mask, p0, p1):
    """Vérifie par échantillonnage fin (pas ~3,7 mm, décalé pour éviter de tomber
    pile sur un coin de cellule) que le tronçon p0 -> p1 reste dans le masque.
    Indépendant du code testé (n'utilise pas line_of_sight)."""
    length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    n = max(2, int(length / 0.0037))
    for k in range(n + 1):
        t = min(1.0, (k + 0.3) / (n + 0.6)) if 0 < k < n else k / n
        x = p0[0] + t * (p1[0] - p0[0])
        y = p0[1] + t * (p1[1] - p0[1])
        row, col = int(math.floor(y / RES)), int(math.floor(x / RES))
        h, w = mask.shape
        if not (0 <= row < h and 0 <= col < w and mask[row, col]):
            return False
    return True


def assert_path_valid(mask, path, max_step=MAX_STEP):
    """Tous les tronçons dans le masque et aucun plus long que max_step."""
    for a, b in zip(path[:-1], path[1:]):
        assert leg_in_mask(mask, a, b), f"tronçon hors masque : {a} -> {b}"
        assert math.hypot(b[0] - a[0], b[1] - a[1]) <= max_step + 1e-6, f"tronçon trop long : {a} -> {b}"


def assert_originals_in_order(path, originals):
    """Les waypoints d'origine (avec leur yaw) apparaissent dans l'ordre."""
    i = 0
    for wp in path:
        if i < len(originals) and wp == originals[i]:
            i += 1
    assert i == len(originals), "waypoints d'origine manquants ou dans le désordre"


# ---------- tests ----------

def test_paire_en_ligne_droite_inchangee():
    mask = np.ones((10, 30), dtype=bool)
    wps = [centre(5, 2, 0.0), centre(5, 27, 0.0)]
    result, n = plan(mask, wps)
    assert result == wps
    assert n == 0


def test_pilier_entre_deux_waypoints():
    mask = np.ones((12, 30), dtype=bool)
    mask[4:8, 13:17] = False  # pilier sur la ligne 5
    wps = [centre(5, 2, 0.0), centre(5, 27, 0.0), centre(9, 27, math.pi)]
    result, n = plan(mask, wps)
    assert n == 0
    assert len(result) > len(wps)  # des points ont été insérés
    assert_path_valid(mask, result)
    assert_originals_in_order(result, wps)
    # Les points insérés sont orientés vers le point suivant.
    for (x, y, yaw), (nx, ny, _) in zip(result[:-1], result[1:]):
        if (x, y, yaw) not in wps:
            assert math.isclose(math.cos(yaw), math.cos(math.atan2(ny - y, nx - x)), abs_tol=1e-6)
            assert math.isclose(math.sin(yaw), math.sin(math.atan2(ny - y, nx - x)), abs_tol=1e-6)


def test_couloir_en_L_contourne_le_coin_interieur():
    mask = np.zeros((20, 20), dtype=bool)
    mask[0:6, :] = True   # bras horizontal
    mask[:, 0:6] = True   # bras vertical (coin intérieur en (6, 6))
    wps = [centre(2, 17, math.pi), centre(17, 2, math.pi / 2)]
    result, n = plan(mask, wps)
    assert n == 0
    assert len(result) > 2
    assert_path_valid(mask, result)
    assert_originals_in_order(result, wps)


def test_deux_zones_non_reliees():
    mask = np.ones((10, 30), dtype=bool)
    mask[:, 14:16] = False  # mur complet : deux zones séparées
    wps = [centre(5, 3, 0.0), centre(5, 25, 0.0)]
    result, n = plan(mask, wps)
    assert n == 1
    assert result == wps  # paire conservée


def test_liste_vide_et_un_seul_waypoint():
    mask = np.ones((10, 10), dtype=bool)
    assert plan(mask, []) == ([], 0)
    one = [centre(5, 5, 1.0)]
    assert plan(mask, one) == (one, 0)


def test_diagonale_par_un_coin_reste_inchangee():
    # Diagonale à 45° passant pile par le coin commun de (5,5)/(6,6), les cellules
    # (5,6) et (6,5) étant bloquées : le segment ne fait que toucher le coin, il est
    # dans le masque -> la paire doit rester inchangée.
    mask = np.ones((12, 12), dtype=bool)
    mask[5, 6] = mask[6, 5] = False
    wps = [centre(1, 1, math.pi / 4), centre(10, 10, math.pi / 4)]
    result, n = plan(mask, wps)
    assert result == wps
    assert n == 0


def test_tronçons_a_45_degres_dont_les_points_tombent_sur_des_coins():
    # Régression : avec un pilier en diagonale, le contournement contient des tronçons
    # à 45° découpés. Selon max_step, certains points tombent pile sur un coin de
    # cellule ; aucun tronçon ne doit sortir du masque, quel que soit max_step.
    mask = np.ones((14, 14), dtype=bool)
    mask[5:9, 5:9] = False
    mask[3, 6] = mask[6, 3] = False  # petits obstacles : diagonales rasant des coins
    wps = [centre(2, 2, 0.0), centre(11, 11, 0.0)]
    for max_step in (0.05, 0.1, 0.1 * math.sqrt(2), 0.15, 0.2, 0.25, 0.3, 0.5):
        result, n = plan(mask, wps, max_step=max_step)
        assert n == 0, max_step
        assert len(result) > 2, max_step
        assert_path_valid(mask, result, max_step=max_step)
        assert_originals_in_order(result, wps)


def test_piece_vide_boustrophedon_inchange():
    # Propriété : sur une pièce vide, aucune transition à résoudre -> sortie == entrée.
    h, w = 40, 50
    grid = np.zeros((h, w), dtype=int)
    grid[0, :] = grid[-1, :] = 100
    grid[:, 0] = grid[:, -1] = 100
    free = occupancy_to_free(grid.flatten().tolist(), w, h)
    mask = reachable_mask(free, (20, 25), RES)
    wps = boustrophedon_waypoints(mask, 0.0, 0.0, RES)
    assert len(wps) > 2
    result, n = plan(mask, wps)
    assert result == wps
    assert n == 0

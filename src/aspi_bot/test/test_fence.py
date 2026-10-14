import math

import numpy as np
import pytest

from aspi_bot.planning import restrict_to_rect
from aspi_bot.random_logic import fence_distance_ahead

FRONT = math.radians(30)
RECT = (0.0, 0.0, 2.0, 2.0)


@pytest.mark.parametrize('fence', [None, [], ()])
def test_barriere_desactivee_donne_inf(fence):
    assert fence_distance_ahead(5.0, 5.0, 0.0, fence, FRONT) == math.inf


def test_dedans_distance_au_bord_devant():
    assert fence_distance_ahead(1.0, 1.0, 0.0, RECT, FRONT) == pytest.approx(1.0)
    assert fence_distance_ahead(1.7, 1.0, 0.0, RECT, FRONT) == pytest.approx(0.3)


def test_dedans_cap_vers_le_haut_et_vers_le_bas():
    assert fence_distance_ahead(1.0, 1.5, math.pi / 2, RECT, FRONT) == pytest.approx(0.5)
    assert fence_distance_ahead(1.0, 0.4, -math.pi / 2, RECT, FRONT) == pytest.approx(0.4)


def test_dedans_dos_au_mur_ne_voit_pas_le_mur():
    assert fence_distance_ahead(1.9, 1.0, math.pi, RECT, FRONT) == pytest.approx(1.9)


def test_coin_le_secteur_oblique_voit_le_bord_plus_proche():
    d = fence_distance_ahead(1.9, 1.9, math.pi / 4, RECT, FRONT)
    assert d == pytest.approx(0.1 / math.sin(math.radians(75)), rel=1e-6)
    assert d < 0.1 / math.sin(math.radians(45))


def test_coin_cap_axe_le_rayon_oblique_ne_depasse_pas_le_central():
    d = fence_distance_ahead(1.9, 1.9, 0.0, RECT, FRONT)
    assert d == pytest.approx(0.1)


def test_dehors_en_s_eloignant_donne_zero():
    assert fence_distance_ahead(3.0, 1.0, 0.0, RECT, FRONT) == 0.0


def test_dehors_en_revenant_donne_inf():
    assert fence_distance_ahead(3.0, 1.0, math.pi, RECT, FRONT) == math.inf


@pytest.mark.parametrize('fence', [[0.0, 0.0, 1.0], [0, 0, 1, 1, 2],
                                   [1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 1.0, 0.0],
                                   [0.0, 0.0, 0.0, 1.0]])
def test_rectangle_mal_forme_leve_valueerror(fence):
    with pytest.raises(ValueError):
        fence_distance_ahead(0.0, 0.0, 0.0, fence, FRONT)


def test_sur_le_bord_compte_comme_dedans():
    assert fence_distance_ahead(2.0, 1.0, 0.0, RECT, FRONT) == pytest.approx(0.0)


RES = 0.5


def free_grid(h=4, w=6):
    return np.ones((h, w), dtype=bool)


@pytest.mark.parametrize('rect', [None, [], ()])
def test_restrict_vide_renvoie_une_copie(rect):
    free = free_grid()
    out = restrict_to_rect(free, 0.0, 0.0, RES, rect)
    assert np.array_equal(out, free)
    assert out is not free
    out[0, 0] = False
    assert free[0, 0]


def test_restrict_sous_rectangle_exact():
    free = free_grid()
    out = restrict_to_rect(free, 0.0, 0.0, RES, (1.0, 0.5, 2.0, 1.5))
    expected = np.zeros((4, 6), dtype=bool)
    expected[1:3, 2:4] = True
    assert np.array_equal(out, expected)


def test_restrict_garde_les_obstacles():
    free = free_grid()
    free[1, 2] = False
    out = restrict_to_rect(free, 0.0, 0.0, RES, (1.0, 0.5, 2.0, 1.5))
    assert not out[1, 2]
    assert out.sum() == 3


def test_restrict_origine_decalee():
    free = free_grid()
    out = restrict_to_rect(free, -1.0, -1.0, RES, (0.0, -1.0, 1.0, 1.0))
    assert out[:, 2:4].all() and out.sum() == 8


@pytest.mark.parametrize('rect', [(0, 0, 1), (1.0, 0.0, 0.0, 1.0), (0.0, 1.0, 1.0, 1.0)])
def test_restrict_rectangle_mal_forme(rect):
    with pytest.raises(ValueError):
        restrict_to_rect(free_grid(), 0.0, 0.0, RES, rect)

"""Tests du détecteur de faux succès (progress_check, Python pur, sans ROS)."""

import math

import pytest

from aspi_bot.progress_check import ProgressMonitor, segment_length


def test_jamais_d_alerte_si_parcouru_egal_attendu():
    m = ProgressMonitor()
    for _ in range(50):
        assert m.on_waypoint_reached(1.0, 1.0) is False
    assert m.suspects == 0


def test_vrai_succes_avec_tolerance_n_est_jamais_suspect():
    # Pire cas réel : d - 2 x 0.15 m parcourus, pour d >= 0.43 m
    m = ProgressMonitor()
    for d in (0.43, 0.5, 1.0, 2.5):
        assert m.on_waypoint_reached(d, d - 0.30) is False
        assert m.suspects == 0


def test_alerte_au_deuxieme_suspect_consecutif():
    m = ProgressMonitor()
    assert m.on_waypoint_reached(1.0, 0.0) is False
    assert m.suspects == 1
    assert m.on_waypoint_reached(1.0, 0.0) is True
    assert m.suspects == 2


def test_waypoint_normal_remet_a_zero():
    m = ProgressMonitor()
    assert m.on_waypoint_reached(1.0, 0.0) is False
    assert m.on_waypoint_reached(1.0, 1.0) is False   # normal
    assert m.suspects == 0
    assert m.on_waypoint_reached(1.0, 0.0) is False   # il faut de nouveau 2 suspects
    assert m.on_waypoint_reached(1.0, 0.0) is True


def test_waypoint_trop_proche_sans_effet():
    m = ProgressMonitor()
    assert m.on_waypoint_reached(1.0, 0.0) is False
    # trop proche (< 0.15) : ne change pas le compteur, même sans mouvement
    assert m.on_waypoint_reached(0.10, 0.0) is False
    assert m.suspects == 1
    # et ne le remet pas à zéro non plus, même avec mouvement
    assert m.on_waypoint_reached(0.10, 0.10) is False
    assert m.suspects == 1
    assert m.on_waypoint_reached(1.0, 0.0) is True


def test_waypoint_trop_proche_ne_declenche_pas_seul():
    m = ProgressMonitor()
    for _ in range(10):
        assert m.on_waypoint_reached(0.10, 0.0) is False
    assert m.suspects == 0


@pytest.mark.parametrize('exp,trav', [(math.nan, 1.0), (1.0, math.nan),
                                      (math.inf, 0.0), (1.0, math.inf)])
def test_nan_et_inf_ignores(exp, trav):
    m = ProgressMonitor()
    m.on_waypoint_reached(1.0, 0.0)
    assert m.on_waypoint_reached(exp, trav) is False
    assert m.suspects == 1   # inchangé


def test_egalite_au_seuil_non_suspecte():
    # traveled == min_ratio * expected (valeurs exactes en binaire) : pas suspect
    m = ProgressMonitor(min_ratio=0.5)
    for _ in range(5):
        assert m.on_waypoint_reached(2.0, 1.0) is False
    assert m.suspects == 0
    # juste en dessous : suspect
    m.on_waypoint_reached(2.0, 0.99)
    assert m.suspects == 1


def test_egalite_a_min_expected_est_evalue():
    # expected == min_expected n'est PAS « trop proche » (comparaison stricte <)
    m = ProgressMonitor(min_expected=0.5)
    m.on_waypoint_reached(0.5, 0.0)
    assert m.suspects == 1


def test_max_suspects_configurable():
    m = ProgressMonitor(max_suspects=3)
    assert m.on_waypoint_reached(1.0, 0.0) is False
    assert m.on_waypoint_reached(1.0, 0.0) is False
    assert m.on_waypoint_reached(1.0, 0.0) is True


def test_alerte_persistante_apres_declenchement():
    m = ProgressMonitor()
    m.on_waypoint_reached(1.0, 0.0)
    assert m.on_waypoint_reached(1.0, 0.0) is True
    assert m.on_waypoint_reached(0.05, 0.0) is True   # trop proche : état conservé


@pytest.mark.parametrize('kwargs', [
    {'min_ratio': 0.0}, {'min_ratio': -0.1}, {'min_ratio': 1.5},
    {'min_expected': -0.01}, {'max_suspects': 0}, {'max_suspects': -1}])
def test_parametres_invalides(kwargs):
    with pytest.raises(ValueError):
        ProgressMonitor(**kwargs)


def test_parametres_limites_valides():
    ProgressMonitor(min_ratio=1.0, min_expected=0.0, max_suspects=1)


def test_segment_length():
    assert segment_length((0.0, 0.0), (3.0, 4.0)) == pytest.approx(5.0)
    assert segment_length((1.0, 1.0), (1.0, 1.0)) == 0.0
    assert segment_length((-1.0, 0.0), (1.0, 0.0)) == pytest.approx(2.0)
    # éléments au-delà de x, y ignorés (yaw)
    assert segment_length((0.0, 0.0, 1.5), (3.0, 4.0, -2.0)) == pytest.approx(5.0)


# --- Critère de temps (max_elapsed) ---

def test_critere_temps_seuil():
    # 1.99 s : suspect ; 2.0 s : non suspect (comparaison stricte <)
    m = ProgressMonitor()
    m.on_waypoint_reached(1.0, 0.0, 1.99)
    assert m.suspects == 1
    m.on_waypoint_reached(1.0, 0.0, 2.0)
    assert m.suspects == 0


def test_critere_temps_deux_rapides_declenchent():
    m = ProgressMonitor()
    assert m.on_waypoint_reached(1.0, 0.0, 0.85) is False
    assert m.on_waypoint_reached(1.0, 0.0, 0.85) is True


def test_waypoint_lent_remet_a_zero():
    m = ProgressMonitor()
    assert m.on_waypoint_reached(1.0, 0.0, 0.5) is False
    assert m.suspects == 1
    assert m.on_waypoint_reached(1.0, 0.0, 30.0) is False   # lent : échec Nav2, pas suspect
    assert m.suspects == 0
    assert m.on_waypoint_reached(1.0, 0.0, 0.5) is False    # il faut de nouveau 2 suspects
    assert m.on_waypoint_reached(1.0, 0.0, 0.5) is True


@pytest.mark.parametrize('el', [None, math.nan, -1.0, -0.001])
def test_temps_invalide_ignore(el):
    # temps ignoré : comportement sans critère de temps (donc suspect si peu parcouru)
    m = ProgressMonitor()
    assert m.on_waypoint_reached(1.0, 0.0, el) is False
    assert m.suspects == 1
    assert m.on_waypoint_reached(1.0, 0.0, el) is True


def test_temps_omis_equivaut_a_none():
    m = ProgressMonitor()
    m.on_waypoint_reached(1.0, 0.0)
    assert m.on_waypoint_reached(1.0, 0.0) is True


def test_temps_infini_jamais_suspect():
    m = ProgressMonitor()
    for _ in range(5):
        assert m.on_waypoint_reached(1.0, 0.0, math.inf) is False
    assert m.suspects == 0


def test_temps_nul_est_suspect():
    m = ProgressMonitor()
    m.on_waypoint_reached(1.0, 0.0, 0.0)
    assert m.suspects == 1


def test_temps_lent_mais_mouvement_normal_remet_a_zero():
    m = ProgressMonitor()
    m.on_waypoint_reached(1.0, 0.0, 0.5)
    m.on_waypoint_reached(1.0, 1.0, 0.5)
    assert m.suspects == 0


@pytest.mark.parametrize('me', [0.0, -1.0, math.nan])
def test_max_elapsed_invalide(me):
    with pytest.raises(ValueError):
        ProgressMonitor(max_elapsed=me)


def test_max_elapsed_valide_et_inf():
    ProgressMonitor(max_elapsed=0.001)
    m = ProgressMonitor(max_elapsed=math.inf)   # tout est « rapide » : ancien comportement
    m.on_waypoint_reached(1.0, 0.0, 1e9)
    assert m.suspects == 1

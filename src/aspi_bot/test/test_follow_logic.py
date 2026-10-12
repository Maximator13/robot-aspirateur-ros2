import math

from aspi_bot.follow_logic import follow_step, wrap_angle


def test_wrap_angle():
    assert math.isclose(wrap_angle(3 * math.pi / 2), -math.pi / 2)
    assert math.isclose(wrap_angle(-3 * math.pi / 2), math.pi / 2)


def test_waypoint_atteint():
    v, w, reached, driving = follow_step(0.0, 0.0, 0.0, 0.05, 0.0, driving=True)
    assert reached and v == 0.0 and w == 0.0 and not driving


def test_rotation_sur_place_si_waypoint_derriere():
    v, w, reached, driving = follow_step(0.0, 0.0, 0.0, -1.0, -0.1, driving=False)
    assert v == 0.0 and not reached and not driving
    assert w < 0  # cible à ~-174° : tourner dans le sens horaire (chemin le plus court)


def test_avance_si_aligne():
    v, w, reached, driving = follow_step(0.0, 0.0, 0.0, 1.0, 0.0, driving=False)
    assert math.isclose(v, 0.10) and abs(w) < 1e-9 and driving and not reached


def test_hysteresis_reste_en_avance():
    # erreur de cap de 0.5 rad : > tolérance (0.35) mais < 2 x tolérance -> on continue d'avancer
    tx, ty = math.cos(0.5), math.sin(0.5)
    v, _, _, driving = follow_step(0.0, 0.0, 0.0, tx, ty, driving=True)
    assert v > 0 and driving
    v, _, _, driving = follow_step(0.0, 0.0, 0.0, tx, ty, driving=False)
    assert v == 0.0 and not driving


def test_ralentit_pres_du_waypoint():
    v, _, _, _ = follow_step(0.0, 0.0, 0.0, 0.1, 0.0, driving=True)
    assert 0.04 <= v < 0.10

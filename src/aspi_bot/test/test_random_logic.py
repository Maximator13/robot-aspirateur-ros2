import math

from aspi_bot.random_logic import FORWARD, TURN, RandomWalkerLogic, front_min_distance

INF = math.inf
NAN = math.nan
N = 360
INC = 2 * math.pi / N
FRONT = math.radians(30)


def scan(default=3.0):
    return [default] * N


def front(ranges, range_min=0.12, range_max=3.5):
    return front_min_distance(ranges, 0.0, INC, range_min, range_max, FRONT)


def test_front_secteur_avant_debut_et_fin_du_tableau():
    r = scan()
    r[5] = 1.0
    r[355] = 0.8
    assert front(r) == 0.8


def test_front_obstacle_derriere_ignore():
    r = scan()
    r[180] = 0.2
    r[90] = 0.2
    assert front(r) == 3.0


def test_front_valeurs_invalides_ignorees():
    r = scan()
    r[0], r[1], r[2], r[3] = INF, NAN, 0.05, 10.0
    r[4] = 1.5
    assert front(r) == 1.5


def test_front_tout_invalide_donne_inf():
    r = [INF] * N
    assert front(r) == INF
    assert front([NAN] * N) == INF


def test_forward_avance():
    w = RandomWalkerLogic(seed=1, forward_speed=0.15)
    assert w.update(0.0, 2.0) == (0.15, 0.0)
    assert w.state == FORWARD


def test_obstacle_declenche_turn():
    w = RandomWalkerLogic(seed=1, turn_speed=1.0, stop_distance=0.25)
    lin, ang = w.update(0.0, 0.1)
    assert w.state == TURN
    assert lin == 0.0
    assert math.isclose(abs(ang), 1.0)


def test_duree_rotation_dans_bornes():
    for seed in range(20):
        w = RandomWalkerLogic(seed=seed, turn_speed=0.5)
        w.update(10.0, 0.1)
        tmin = math.radians(90) / 0.5
        tmax = math.radians(180) / 0.5
        assert w.update(10.0 + tmin - 0.01, 2.0)[0] == 0.0
        assert w.state == TURN
        assert w.update(10.0 + tmax + 0.01, 2.0)[0] > 0.0
        assert w.state == FORWARD


def test_fin_rotation_voie_libre_forward():
    w = RandomWalkerLogic(seed=3)
    w.update(0.0, 0.1)
    assert w.update(100.0, 2.0) == (0.15, 0.0)
    assert w.state == FORWARD


def test_fin_rotation_voie_bloquee_reste_turn():
    w = RandomWalkerLogic(seed=3)
    w.update(0.0, 0.1)
    lin, ang = w.update(100.0, 0.1)
    assert w.state == TURN
    assert lin == 0.0 and ang != 0.0


def sequence(seed, n=20):
    w = RandomWalkerLogic(seed=seed)
    t, out = 0.0, []
    for _ in range(n):
        _, ang = w.update(t, 0.1)
        out.append((math.copysign(1, ang), round(w.turn_end_s - t, 9)))
        t += 1000.0
        w.update(t, 2.0)
    return out


def test_meme_seed_meme_sequence():
    assert sequence(42) == sequence(42)


def test_seeds_differentes_sequences_differentes():
    assert sequence(1) != sequence(2)

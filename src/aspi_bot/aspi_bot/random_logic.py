"""Logique de la stratégie A « bump and turn », en Python pur (aucun import ROS).

Principe : machine à deux états.
- FORWARD : on avance tout droit ; si un obstacle est vu devant à moins de
  stop_distance, on tire un angle et un sens de rotation au hasard -> TURN.
- TURN : rotation sur place pendant angle / turn_speed secondes (rotation « en temps »,
  sans odométrie), puis retour en FORWARD si la voie est libre, sinon nouveau tirage.
Complexité : O(1) par appel de update() ; O(n) par scan pour front_min_distance
(n = nombre de rayons du LiDAR).

Le hasard vient d'un random.Random(seed) local : même seed -> même suite de rotations
(expérience reproductible). Le temps est passé en argument (now_s) : aucune dépendance
à l'horloge réelle, le nœud ROS fournit le temps simulé.
"""

import math
import random

FORWARD = 'FORWARD'
TURN = 'TURN'


def normalize_angle(angle):
    """Ramène un angle (rad) dans [-pi, pi]."""
    return math.atan2(math.sin(angle), math.cos(angle))


def is_valid_range(r, range_min, range_max):
    """Une mesure LiDAR est valide si elle est finie et dans [range_min, range_max]."""
    return math.isfinite(r) and range_min <= r <= range_max


def front_min_distance(ranges, angle_min, angle_increment, range_min, range_max, front_angle):
    """Distance minimale valide dans le secteur avant [-front_angle, +front_angle].

    front_angle est en radians (le nœud convertit son paramètre front_angle_deg).
    Les angles des rayons sont normalisés dans [-pi, pi] : sur le TurtleBot3,
    le scan va de 0 à 2*pi, l'avant est donc à la fois au début et à la fin du tableau.
    Ignore inf, nan, < range_min et > range_max. Renvoie inf si aucune valeur valide.
    """
    best = math.inf
    for i, r in enumerate(ranges):
        angle = normalize_angle(angle_min + i * angle_increment)
        if abs(angle) <= front_angle and is_valid_range(r, range_min, range_max):
            best = min(best, r)
    return best


class RandomWalkerLogic:
    """Machine à états FORWARD / TURN de la marche aléatoire."""

    def __init__(self, seed, forward_speed=0.15, turn_speed=1.0, stop_distance=0.25,
                 min_turn_deg=90.0, max_turn_deg=180.0):
        if turn_speed <= 0.0:
            raise ValueError('turn_speed doit être > 0')
        self.rng = random.Random(seed)  # générateur local, indépendant du random global
        self.forward_speed = forward_speed
        self.turn_speed = turn_speed
        self.stop_distance = stop_distance
        self.min_turn = math.radians(min_turn_deg)
        self.max_turn = math.radians(max_turn_deg)
        self.state = FORWARD
        self.turn_direction = 1.0  # +1 = sens trigonométrique (gauche), -1 = droite
        self.turn_end_s = 0.0

    def start_turn(self, now_s):
        """Tire un angle dans [min, max] et un sens au hasard, passe en TURN."""
        angle = self.rng.uniform(self.min_turn, self.max_turn)
        self.turn_direction = self.rng.choice((-1.0, 1.0))
        self.turn_end_s = now_s + angle / self.turn_speed
        self.state = TURN

    def turn_command(self):
        """Commande de rotation sur place."""
        return 0.0, self.turn_direction * self.turn_speed

    def update(self, now_s, front_distance):
        """Fait avancer la machine à états et renvoie (linear_x, angular_z)."""
        blocked = front_distance < self.stop_distance
        if self.state == FORWARD:
            if blocked:
                self.start_turn(now_s)
                return self.turn_command()
            return self.forward_speed, 0.0
        # État TURN
        if now_s < self.turn_end_s:
            return self.turn_command()
        if blocked:
            self.start_turn(now_s)  # toujours bloqué : nouveau tirage
            return self.turn_command()
        self.state = FORWARD
        return self.forward_speed, 0.0

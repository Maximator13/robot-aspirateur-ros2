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


# ---------------------------------------------------------------------------
# Barrière virtuelle (robot réel) : rectangle autorisé en repère odom
# ---------------------------------------------------------------------------
# Principe : la barrière est traitée comme un « obstacle virtuel » vu par un faux LiDAR.
# - Robot DANS le rectangle : on lance n_rays rayons répartis dans le secteur avant
#   [-front_angle, +front_angle] et on calcule, pour chacun, la distance jusqu'au bord
#   (méthode des « dalles » : intersection avec les droites x = xmin/xmax, y = ymin/ymax).
#   On renvoie la plus petite : le nœud la compare à stop_distance comme une mesure LiDAR.
# - Robot HORS du rectangle : 0.0 (virage forcé) s'il s'éloigne du centre, inf s'il y revient.
# Complexité : O(n_rays), soit O(1) pour n_rays fixé.

def parse_fence(fence):
    """Valide la barrière. Renvoie (xmin, ymin, xmax, ymax) en float, ou None si désactivée.

    None ou séquence vide -> None (barrière désactivée, valeur par défaut du paramètre []).
    Une barrière mal formée lève ValueError : pour la sécurité, mieux vaut refuser de
    démarrer que de rouler en croyant la barrière active.
    """
    if fence is None or len(fence) == 0:
        return None
    if len(fence) != 4:
        raise ValueError('fence doit contenir 4 valeurs (xmin, ymin, xmax, ymax)')
    xmin, ymin, xmax, ymax = (float(v) for v in fence)
    if not (xmin < xmax and ymin < ymax):
        raise ValueError('fence invalide : il faut xmin < xmax et ymin < ymax')
    return xmin, ymin, xmax, ymax


def point_in_rect(x, y, rect):
    """True si (x, y) est dans le rectangle, bords compris."""
    xmin, ymin, xmax, ymax = rect
    return xmin <= x <= xmax and ymin <= y <= ymax


def ray_exit_distance(x, y, angle, rect):
    """Distance le long du rayon (x, y, angle) jusqu'au bord du rectangle (robot dedans).

    Sur chaque axe, le rayon sort par le bord vers lequel il avance :
    t = (bord - position) / composante de la direction. On garde le plus petit t
    des deux axes. Une composante nulle (rayon parallèle à un bord) ne limite pas
    sur cet axe : distance inf pour cet axe.
    """
    xmin, ymin, xmax, ymax = rect
    dx, dy = math.cos(angle), math.sin(angle)
    eps = 1e-12  # en dessous, le rayon est considéré parallèle à l'axe
    t_x = math.inf
    if dx > eps:
        t_x = (xmax - x) / dx
    elif dx < -eps:
        t_x = (xmin - x) / dx
    t_y = math.inf
    if dy > eps:
        t_y = (ymax - y) / dy
    elif dy < -eps:
        t_y = (ymin - y) / dy
    return max(0.0, min(t_x, t_y))  # max(0, .) : robot posé sur le bord -> 0


def ray_angles(yaw, front_angle, n_rays):
    """n_rays angles répartis régulièrement dans [yaw - front_angle, yaw + front_angle]."""
    if n_rays <= 1:
        return [yaw]  # un seul rayon : droit devant
    step = 2.0 * front_angle / (n_rays - 1)
    return [yaw - front_angle + i * step for i in range(n_rays)]


def heading_towards_center(x, y, yaw, rect):
    """True si le cap du robot pointe vers le centre du rectangle (écart < 90°)."""
    xmin, ymin, xmax, ymax = rect
    to_center = math.atan2((ymin + ymax) / 2.0 - y, (xmin + xmax) / 2.0 - x)
    return abs(normalize_angle(to_center - yaw)) < math.pi / 2.0


def fence_distance_ahead(x, y, yaw, fence, front_angle, n_rays=7):
    """Distance « vue » devant le robot jusqu'à la barrière virtuelle (m).

    x, y, yaw : pose du robot en repère odom ; fence = (xmin, ymin, xmax, ymax) en
    repère odom, None ou [] = désactivée -> inf ; front_angle en radians.
    Dedans : minimum sur n_rays rayons du secteur avant de la distance au bord.
    Dehors : 0.0 s'il s'éloigne du centre (force un virage), inf s'il revient
    vers le centre (on le laisse rentrer).
    Le nœud utilise min(distance LiDAR, distance barrière).
    """
    rect = parse_fence(fence)
    if rect is None:
        return math.inf
    if not point_in_rect(x, y, rect):
        return math.inf if heading_towards_center(x, y, yaw, rect) else 0.0
    return min(ray_exit_distance(x, y, a, rect) for a in ray_angles(yaw, front_angle, n_rays))

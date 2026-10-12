"""Suivi de waypoints « tourner puis avancer » (Python pur, testable sans ROS).

Stratégie B sans Nav2 : pour chaque waypoint du balayage boustrophédon,
  1. si le cap vers le waypoint est trop différent du cap du robot : rotation sur place ;
  2. sinon : avance en corrigeant le cap (vitesse angulaire proportionnelle à l'erreur) ;
  3. waypoint atteint quand la distance passe sous goal_tolerance.
Hystérésis : une fois en avance, on ne repasse en rotation que si l'erreur dépasse 2 x heading_tolerance
(sinon la latence Wi-Fi fait alterner rotation et avance). Complexité O(1) par pas de contrôle.
"""
import math


def wrap_angle(a):
    """Ramène un angle dans ]-pi, pi]."""
    return math.atan2(math.sin(a), math.cos(a))


def follow_step(x, y, yaw, tx, ty, driving, linear_speed=0.10, angular_speed=0.6,
                goal_tolerance=0.08, heading_tolerance=0.35):
    """Un pas de contrôle vers le waypoint (tx, ty).

    Renvoie (v, w, reached, driving) : consignes (m/s, rad/s), waypoint atteint, et nouvel état
    « en avance » (à repasser au pas suivant).
    """
    dx, dy = tx - x, ty - y
    dist = math.hypot(dx, dy)
    if dist < goal_tolerance:
        return 0.0, 0.0, True, False
    err = wrap_angle(math.atan2(dy, dx) - yaw)
    limit = 2.0 * heading_tolerance if driving else heading_tolerance
    if abs(err) > limit:
        return 0.0, math.copysign(angular_speed, err), False, False
    w = max(-angular_speed, min(angular_speed, 2.0 * err))
    # Ralentit sur les 20 derniers cm pour ne pas dépasser le waypoint (minimum 0.04 m/s)
    v = linear_speed if dist > 0.2 else max(0.04, linear_speed * dist / 0.2)
    return v, w, False, True

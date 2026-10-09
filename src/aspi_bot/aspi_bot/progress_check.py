"""Détection des « faux succès » de Nav2 (waypoint déclaré atteint sans mouvement réel).

Principe (5 lignes) :
1. Pour chaque waypoint déclaré atteint, on mesure la distance attendue (ligne droite depuis
   le précédent), la distance parcourue (odométrie) et le temps écoulé depuis la validation précédente.
2. « Suspect » = segment assez long, PEU de distance parcourue ET validation RAPIDE (< max_elapsed).
3. Un faux succès est instantané (incident 10 : 14 waypoints en 12 s, robot immobile) ; un ÉCHEC
   Nav2 (« Failed to process waypoint ») est lent (planification, recoveries) : il n'est pas suspect.
4. max_suspects suspects CONSÉCUTIFS = faux succès ; un waypoint surveillé non suspect remet à zéro.
5. Complexité : O(1) par waypoint (un compteur), aucune dépendance à ROS.
"""

import math


def segment_length(p, q):
    """Distance euclidienne entre deux points p = (x, y) et q = (x, y), en mètres.

    Les éléments au-delà de x, y (par exemple un yaw) sont ignorés.
    """
    return math.hypot(q[0] - p[0], q[1] - p[1])


class ProgressMonitor:
    """Compte les waypoints « suspects » consécutifs et signale un faux succès.

    Choix des seuils (vérifiés sur les cartes world et zone_reelle) :
    - min_ratio = 0.3 : un vrai trajet parcourt au moins d - 0.30 m (tolérance de 0.15 m
      aux deux bouts). Pour d >= 0.43 m, d - 0.30 >= 0.3 d : un vrai succès n'est JAMAIS
      suspect. En dessous (transitions de ligne de 0.20 m), un vrai succès peut l'être.
    - max_suspects = 2 consécutifs : dans le balayage, une transition courte (0.20 m) est
      toujours encadrée par des segments longs ; deux suspects d'affilée ne peuvent donc pas
      venir d'un vrai mouvement validé d'emblée par la tolérance.
    - min_expected = 0.15 m : plus courte distance entre deux waypoints du balayage = 0.20 m
      (espacement des lignes). Un waypoint plus proche ne prouve rien : il est ignoré,
      sans remettre le compteur à zéro.
    - max_elapsed = 2.0 s : faux succès mesuré sur le robot ~0.85 s par waypoint ; échecs Nav2
      mesurés en simulation : 22 à 170 s. Un waypoint validé en plus de max_elapsed n'est pas
      suspect et REMET le compteur à zéro : le temps passé montre que Nav2 a réellement
      travaillé (planification, contrôle, recoveries), ce n'est pas le blocage instantané visé.
      Ajouter une condition au « suspect » ne peut que raccourcir les séries de suspects :
      le critère reste donc sans fausse alerte partout où l'ancien l'était.
    """

    def __init__(self, min_ratio=0.3, min_expected=0.15, max_suspects=2, max_elapsed=2.0):
        # Garde-fous : des paramètres absurdes rendraient le détecteur muet ou hystérique.
        if not 0.0 < min_ratio <= 1.0:
            raise ValueError('min_ratio doit être dans ]0, 1]')
        if min_expected < 0.0:
            raise ValueError('min_expected doit être >= 0')
        if max_suspects < 1:
            raise ValueError('max_suspects doit être >= 1')
        if not max_elapsed > 0.0:   # rejette aussi NaN
            raise ValueError('max_elapsed doit être > 0')
        self.min_ratio = float(min_ratio)
        self.min_expected = float(min_expected)
        self.max_suspects = int(max_suspects)
        self.max_elapsed = float(max_elapsed)
        self._suspects = 0  # nombre de waypoints suspects CONSÉCUTIFS

    def on_waypoint_reached(self, expected_dist: float, traveled_dist: float,
                            elapsed_s=None) -> bool:
        """Appelé à chaque waypoint déclaré atteint par Nav2.

        expected_dist : distance en ligne droite depuis le waypoint précédent (m) ;
        traveled_dist : distance réellement parcourue (odométrie) depuis le waypoint précédent (m) ;
        elapsed_s : temps écoulé depuis la validation précédente (s), ou None si inconnu.
        Un waypoint est « suspect » si expected_dist >= min_expected,
        traveled_dist < min_ratio * expected_dist ET (elapsed_s is None ou elapsed_s < max_elapsed).
        elapsed_s None, NaN ou négatif : critère de temps ignoré (comportement sans le temps) ;
        elapsed_s = +inf : validation « infiniment lente », donc jamais suspecte.
        Renvoie True (faux succès détecté) quand max_suspects waypoints suspects CONSÉCUTIFS
        sont atteints ; un waypoint normal remet le compteur à zéro ; un waypoint trop proche
        (expected < min_expected) ne change rien.
        """
        # Mesure inexploitable (NaN, inf) : on ne conclut rien, le compteur reste tel quel.
        if not (math.isfinite(expected_dist) and math.isfinite(traveled_dist)):
            return self._suspects >= self.max_suspects
        # Waypoint trop proche du précédent : la tolérance d'arrivée suffit à le valider
        # sans bouger, il ne prouve donc rien dans un sens comme dans l'autre.
        if expected_dist < self.min_expected:
            return self._suspects >= self.max_suspects
        too_little = traveled_dist < self.min_ratio * expected_dist
        # Temps inconnu ou mesure absurde (None, NaN, < 0) : on ne s'en sert pas.
        time_known = (elapsed_s is not None and not math.isnan(elapsed_s)
                      and elapsed_s >= 0.0)
        too_fast = (not time_known) or elapsed_s < self.max_elapsed
        if too_little and too_fast:
            self._suspects += 1   # suspect : succès annoncé vite, sans le mouvement attendu
        else:
            # Mouvement cohérent, OU validation lente (échec Nav2 après planification et
            # recoveries) : ce n'est pas le blocage instantané recherché, on repart de zéro.
            self._suspects = 0
        return self._suspects >= self.max_suspects

    @property
    def suspects(self) -> int:
        """Nombre actuel de waypoints suspects consécutifs."""
        return self._suspects

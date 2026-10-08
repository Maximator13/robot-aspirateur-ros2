# Perspectives

Prochains incréments, petits et concrets. Chacun part d'un problème mesuré (chiffres de `docs/JOURNAL.md`), propose une action, estime l'effort et fixe une mesure de succès.
Les efforts sont des estimations, pas des mesures. Les gains attendus sont des hypothèses à vérifier, pas des résultats.

Protocole de mesure commun : même monde, même départ, 600 s simulées, même tracker, au moins 3 runs par configuration.

---

## Classement gain / effort

| Rang | Incrément | Gain attendu | Effort | Risque |
|---|---|---|---|---|
| 1 | P1. Plus de runs, et seed en entrée de B | Élevé (conclusions solides) | 0,5 jour | Faible |
| 2 | P2. Réduire les rotations sur place | Moyen à élevé | 0,5 à 1 jour | Faible |
| 3 | P3. Espacement de balayage effectif | Moyen | 0,5 jour | Faible |
| 4 | P4. Diagnostiquer le gel de `map → odom` | Élevé (fiabilité, mode accéléré) | 1 jour | Moyen |
| 5 | P5. Coverage server de Nav2 comme référence | Moyen (comparaison) | 1 jour | Moyen |
| 6 | P6. Spirale ou aléatoire amélioré pour A | Moyen | 0,5 jour | Faible |
| 7 | P7. Décomposition cellulaire de Choset | Élevé en théorie | 3 jours ou plus | Élevé |
| 8 | P8. Une autre pièce | Moyen (généralité) | 1 jour | Moyen |
| 9 | P9. Essai sur robot réel | Élevé (crédibilité) | 2 jours ou plus | Élevé |

---

## P1. Plus de runs et deuxième jeu de mesures

- **Problème mesuré.** Les réglages T0 à T5 reposent sur un run par configuration. T5 contre T3 : 59.7 % contre 54.1 % à 600 s, avec des seeds différentes (5 et 1). A vaut 51.0 ± 6.7 % sur 3 seeds : l'écart-type est supérieur à la moitié de la différence A/B. Aucune conclusion statistique n'est possible aujourd'hui.
- **Proposition.** 5 runs de B (config T5) et 5 runs de A (mode accéléré, déjà validé), seeds fixées. Fournir au launch de B un vrai lien seed → nom du CSV et garder les rosbags. Reporter moyenne, min et max.
- **Effort.** Une demi-journée, surtout du temps machine (B en temps réel : environ 10 min par run, A accéléré : environ 3.5 min).
- **Mesure de succès.** Intervalle min-max de B publié, avec un test simple : les intervalles de A et de B se recouvrent-ils ou non à 600 s ?
- **Note.** B est déterministe en planification, mais pas en exécution (AMCL, timing de Nav2). La dispersion de B n'est pas nulle : à mesurer, pas à supposer.

## P2. Réduire les rotations sur place

- **Problème mesuré.** Environ 18 % du temps de B (T5, 600 s) est passé en rotation sur place, 18 % aussi en T3. En T3 à 300 s : environ 48 s de rotation. Chaque extrémité de ligne impose un demi-tour, et un arrêt d'environ 30 s a été observé sur les petits segments entre lignes.
- **Proposition, par ordre croissant d'effort.**
  1. Orienter chaque waypoint vers le waypoint suivant (et non dans le sens de passage de sa ligne), pour que la rotation soit faite en arrivant.
  2. Régler `rotate_to_heading_min_angle` (0.785 rad aujourd'hui) : en dessous de ce seuil, le contrôleur Regulated Pure Pursuit tourne en avançant. Tester 1.2 rad et 1.57 rad.
  3. Envoyer chaque ligne comme un `Path` suivi par l'action `FollowPath` du contrôleur, au lieu d'une liste de waypoints. Le `waypoint_follower` et le `bt_navigator` sont alors court-circuités. Risque : perte de la gestion des waypoints sautés, à reprogrammer dans l'executor.
- **Effort.** 1 : 2 heures. 2 : 2 heures, une run de 300 s par valeur. 3 : une journée.
- **Mesure de succès.** Part du temps en rotation sur place sous 10 %, sans baisse du nombre de waypoints atteints (73 en T5) ni hausse des « controller patience exceeded » (2 en T5). Gain visé : couverture à 600 s supérieure à 59.7 %.

## P3. Espacement de balayage effectif et largeur nettoyée

- **Problème mesuré.** `sweep_spacing` vaut 0.18 m. Sur une grille de 0.05 m, il est arrondi à 4 cellules, soit 0.20 m effectifs. Le rayon de nettoyage du tracker est de 0.09 m : largeur nettoyée de 0.18 m. Une bande de 0.02 m reste non couverte entre lignes parfaites, même en exécution idéale. Le test sur pièce vide donne 100 % en simulation de grille, mais les bords ne sont couverts que si le rayon de nettoyage vaut au moins la moitié de l'espacement (JOURNAL, « dernière bande non couverte »).
- **Proposition.** Arrondir l'espacement vers le bas (3 cellules, 0.15 m) ou choisir `sweep_spacing` compatible avec la résolution (0.15 ou 0.20 avec `cleaning_radius` à 0.10). Comparer le coût en distance à la couverture gagnée.
- **Effort.** Une demi-journée : une ligne de configuration, un test unitaire, 3 runs.
- **Mesure de succès.** Couverture maximale en exécution parfaite (simulation sur grille) : 100 % dans les deux cas. Sur le simulateur, écart de couverture finale à 600 s. Contrepartie à chiffrer : distance et nombre de waypoints (112 aujourd'hui).
- **Limite.** L'espacement 0.15 m multiplie le nombre de lignes et allonge le trajet. Le gain n'est pas garanti : à mesurer.

## P4. Diagnostiquer le gel de la TF `map → odom` dans Nav2

- **Problème mesuré.** En mode accéléré, la TF `map → odom` d'AMCL reste figée à 89 s simulées (2 292 messages « Transform data too old »). Résultat : 8 waypoints atteints contre 69, 85 incidents contre 1, 510 m parcourus contre 61.9 m. Le mode accéléré est inutilisable pour B, ce qui interdit de diviser par 2 le temps des runs de B. Un blocage de démarrage a aussi été observé : 2 lancements sur 5, avant le correctif de l'executor. Le gel a aussi été constaté en temps réel. B3 (run officiel ; journal) : TF vue par le conteneur Nav2 figée à environ 135 s simulées, 4 329 « Transform data too old », 71 « Behavior Tree tick rate exceeded », alors que le rosbag montre AMCL publiant `map → odom` sans interruption (5 Hz, aucun trou supérieur à 1 s). T1 (essai de réglage ; rapport du test-engineer, non consigné dans le journal) : figée à environ 234 s simulées, 739 messages sur tout le log. Mode accéléré (vérification croisée ; journal) : figée à 89 s, 2 292 messages. Fréquence : 1 run officiel sur 3, et 3 occurrences sur environ 10 runs de B (dont 1 en accéléré).
- **Proposition.** Trier les hypothèses une par une, en gardant un run de 300 s par hypothèse :
  1. Charge CPU sous WSL : mesurer l'usage CPU de `amcl` et de `gzserver` pendant le gel.
  2. Découverte et transport DDS : essayer un autre RMW ou le profil DDS en mode local.
  3. `transform_tolerance` d'AMCL et des costmaps : valeur actuelle, puis plus grande.
  4. Pile composée contre non composée : lancer Nav2 avec `use_composition:=False` pour isoler un défaut de conteneur.
- **Effort.** Une journée.
- **Mesure de succès.** Aucun gel de la TF sur 5 runs de 600 s en temps réel. Bonus : le critère C1 de la vérification croisée (fréquence de `/cmd_vel_nav` dans ± 10 % de 10 Hz) respecté en mode accéléré, ce qui rend possible P1 en moitié de temps.
- **Limite.** L'origine exacte du gel n'est pas démontrée aujourd'hui. Ce n'est qu'une liste d'hypothèses.

## P5. Coverage server de Nav2 (opennav_coverage) comme référence

- **Problème mesuré.** Notre balayage est un boustrophédon simple : 112 waypoints, contournements laissés au planificateur de Nav2, 59.7 % en 600 s sous T5. Sans autre implémentation de référence, impossible de dire si ce résultat est limité par l'algorithme ou par l'exécution.
- **Proposition.** Installer ou compiler le coverage server (`opennav_coverage`, Open Navigation) et lui fournir le même polygone de la pièce, la même largeur de passage. Exécuter son trajet sur le même robot, avec le même tracker.
- **Effort.** Une journée. Point dur : la disponibilité du paquet pour Humble n'est pas vérifiée. À contrôler avant de s'engager, car le paquet cible des distributions plus récentes. Si indisponible, abandon documenté.
- **Mesure de succès.** Courbe de couverture du coverage server à côté de A et de B, sur 3 runs.

## P6. Spirale ou aléatoire amélioré pour la stratégie A

- **Problème mesuré.** A atteint 51.0 ± 6.7 % à 600 s, avec des plateaux : le robot repasse sur des zones couvertes (JOURNAL, premier résultat A). Aucune des variantes classiques de robots du commerce (spirale locale suivie de rebonds, suivi de mur) n'a été testée.
- **Proposition.** Ajouter à `random_logic.py` une variante : spirale d'Archimède au départ, puis rebonds comme aujourd'hui. Variante 2 : angle de rebond non uniforme. Garder le même tracker.
- **Effort.** Une demi-journée par variante (Python pur, tests pytest, 3 runs accélérés de 3.5 min).
- **Mesure de succès.** Moyenne sur 3 seeds supérieure à celle de A (51.0 %) de plus d'un écart-type (6.7 points). Sinon : résultat négatif documenté.

## P7. Décomposition cellulaire de Choset

- **Problème mesuré.** Un pilier coupe une ligne : le robot finit le segment, puis fait un contournement par Nav2 (environ 13 s au pilier en T3). La carte compte 9 piliers. L'essai T4 (contournements calculés par le planner) a échoué : 22.3 % contre 28.5 % à 300 s, car les points intermédiaires multipliaient arrêts et rotations (38 % du temps).
- **Proposition.** Remplacer l'enchaînement de segments par une décomposition cellulaire : cellules sans obstacle, une ligne de balayage par cellule, passage de cellule à cellule par un chemin simple. Commencer par un cas à un pilier, en Python pur, avec tests sur la grille en L.
- **Effort.** Trois jours ou plus. Le plus gros incrément de la liste.
- **Mesure de succès.** Couverture finale supérieure à celle de T5, avec une distance totale inférieure (69.8 m en T5), et moins de transitions : critères à fixer avant le run.
- **Limite.** Gain non démontré. T4 a montré qu'une amélioration « évidente » peut être négative.

## P8. Une autre pièce

- **Problème mesuré.** Un seul monde (`turtlebot3_world`, 5564 cellules atteignables, 13.9 m²). Les réglages T0 à T5 sont adaptés à ce monde.
- **Proposition.** Ajouter un second monde (par exemple `turtlebot3_house`, ou une pièce à couloir en L) avec sa carte de référence, sans changer les paramètres.
- **Effort.** Une journée : cartographier (par `random_walker`, comme pour la première carte), 3 runs par stratégie.
- **Mesure de succès.** Classement A contre B inchangé, ou écart documenté. Détection des paramètres qui dépendent du monde.

## P9. Essai sur robot réel

- **Problème mesuré.** Tout est simulé. L'odométrie simulée est quasi idéale, le LiDAR sans bruit réel, et la TF `map → odom` identique à la vérité. Aucun chiffre ne dit comment B se comporte sur un vrai robot.
- **Proposition.** Un essai court du `random_walker` seul (A) sur un TurtleBot3 réel :
  1. connexion Wi-Fi au Raspberry Pi, même `ROS_DOMAIN_ID` ;
  2. WSL en mode réseau « mirrored » (sinon les paquets multicast DDS ne passent pas) ;
  3. `ROS_LOCALHOST_ONLY` désactivé pour cet essai ;
  4. `use_sim_time` à False.
  Ensuite seulement, essayer B.
- **Effort.** Deux jours ou plus. Les points durs sont le réseau (multicast, latence) et le recalage de la carte.
- **Mesure de succès.** Niveau 1 : `/scan` et `/cmd_vel` échangés avec le robot réel, sans perte, depuis WSL. Niveau 2 : A tourne 5 minutes sans collision.
- **Limite.** Risque matériel et réseau. À ne tenter qu'après P1 et P2.

---

## Ce qui n'est pas proposé

- Aucune promesse de « couverture complète » : B n'a pas dépassé 60 % sur un run en 600 s, 80 % n'est atteint par aucune stratégie.
- Pas d'apprentissage par renforcement, hors périmètre du temps et des sources vérifiées.

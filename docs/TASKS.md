# Tickets — Robot aspirateur (CCPP)

Statuts : `À FAIRE` · `EN COURS` · `REVUE` · `FINI` · `BLOQUÉ`
« Fini » = compile + tests OK + tourne en simu + relu + noté au journal.

## Jour 1 — Socle + stratégie A (MVP)

| Id | Description | Responsable | Dépend de | Critère de fini | Statut |
|---|---|---|---|---|---|
| J1-01 | Vérification de l'environnement (section 4) | chef de projet | — | Tableau rapporté à l'étudiant | FINI |
| J1-02 | Mise en place : `git init`, `.gitignore`, squelette `aspi_bot` | chef de projet | — | Arborescence créée | FINI |
| J1-03 | Carte de référence `maps/world.{yaml,pgm}` (Cartographer + exploration par `random_walker`, au lieu de la téléop prévue) **depuis le spawn** | chef de projet (exploration par random_walker) | — | Carte fermée, visible dans RViz | FINI |
| J1-04 | `planning.py` (masque libre, érosion, composante connexe, marquage de disque, % couvert, boustrophédon) + `random_logic.py` | ingénieur algorithmes | — | Python pur, importable sans ROS, docstrings | FINI |
| J1-05 | `aspi_interfaces` (`CoverageStatus.msg`), `random_walker_node.py`, `coverage_tracker_node.py`, `rviz/aspi.rviz` | développeur ROS | contrats ci-dessous | `colcon build` OK | FINI |
| J1-06 | État de l'art (`docs/ETAT_DE_L_ART.md`) | rédacteur technique | — | 6 approches, sources réelles | FINI |
| J1-07 | Tests pytest de `planning.py` et `random_logic.py` | ingénieur test | J1-04 | `pytest` vert | FINI |
| J1-08 | `launch/aspi_random.launch.py` | chef de projet | J1-03, J1-05 | Lance Gazebo + map_server + TF + nœuds + RViz | FINI |
| J1-09 | Revue de J1-04/05/07/08 | relecteur | J1-04..08 | Aucun BLOQUANT | FINI |
| J1-10 | Premier run A (seed 1), premier CSV | ingénieur test | J1-09 | CSV dans `results/` | FINI |
| J1-11 | `scripts/plot_results.py`, première courbe | analyste résultats | J1-10 | `results/coverage_vs_time.png` | FINI |
| J1-12 | Journal du jour 1 | opérateur / scribe | toutes | Entrées au format du brief | FINI |
| J1-13 | Mode headless + accéléré, validation par critères (seed 1 temps réel vs accéléré) | chef de projet + ingénieur test | J1-10 | 5 critères OK | FINI |
| J1-14 | Runs A seeds 2 et 3 (accéléré) | ingénieur test | J1-13 | CSV + courbe 3 runs | FINI |

## Jour 2 — Stratégie B (planifiée, Nav2)

| Id | Description | Responsable | Dépend de | Critère de fini | Statut |
|---|---|---|---|---|---|
| J2-01 | `config/nav2_params.yaml` (copie de `turtlebot3_navigation2/param/humble/burger.yaml`, écarts documentés) | développeur ROS | — | YAML valide, écarts commentés | FINI |
| J2-02 | `coverage_planner_node.py` (`/map` → `/coverage_path`) + displays Nav2 dans `rviz/aspi.rviz` | développeur ROS | — | build OK, trajet visible dans RViz | FINI |
| J2-03 | `coverage_executor_node.py` (BasicNavigator, `followWaypoints`) + arrêt propre du `random_walker` | développeur ROS | — | build OK | FINI |
| J2-04 | `launch/sim.launch.py` (Gazebo commun A/B), `aspi_random` l'inclut, `aspi_planned.launch.py` | chef de projet | J2-01..03 | Les deux launch démarrent | FINI |
| J2-05 | `docs/ARCHITECTURE.md` + `docs/ALGORIGRAMMES.md` (A maintenant, B une fois le code écrit) | rédacteur technique | — | Mermaid fidèle au code | FINI |
| J2-06 | Revue J2-01..04 | relecteur | J2-01..04 | Aucun BLOQUANT | FINI |
| J2-07 | Nav2 seul : un goal manuel atteint (par script, temps réel) | ingénieur test | J2-06 | Goal atteint, AMCL localisé | FINI |
| J2-08 | Run B complet en temps réel + non-régression de A (smoke test du launch refactorisé) | ingénieur test | J2-07 | CSV BOUSTROPHEDON | FINI |
| J2-09 | Vérification croisée B temps réel vs accéléré (mêmes critères que A) | ingénieur test | J2-08 | Décision chiffrée | FINI (KO : B en temps réel) |
| J2-11 | Essais de réglage B T0–T4 (300 s) : loop_rate, inflation, contrôleur RPP, contournements du planner | ingénieur test + développeur ROS + ingénieur algorithmes | J2-08 | Réglage retenu chiffré | FINI (T3 retenu, T4 négatif) |
| J2-12 | Essai T5 : suppression du ralentissement d'approche (approach_velocity_scaling_dist 0.2) et de la pause aux waypoints | développeur ROS + ingénieur test | J2-09 | Gain mesuré | FINI (59.7 % vs 54.1 % à 600 s, T5 retenu) |
| J2-13 | Protocole B (600 s, 3 runs, temps réel, config T5) + comparaison A/B | ingénieur test + analyste résultats | J2-09, J2-12 | Courbe A vs B | FINI (A 51.0 ± 6.7 %, B 44.1 ± 23.4 % dont B3 bloqué) |
| J2-10 | Journal du jour 2 | opérateur / scribe | toutes | Entrées au format du brief | FINI |

## Jour 3 — Évaluation et livrables (code gelé)

Code gelé : seuls des correctifs de documentation. Pas de vidéo (décision de l'étudiant) : les figures de
`results/` servent de captures de démo.

| Id | Description | Responsable | Dépend de | Critère de fini | Statut |
|---|---|---|---|---|---|
| J3-01 | Audit de cohérence de tous les documents (chiffres identiques partout et conformes aux CSV, hypothèse ≠ fait, références) | relecteur | — | Liste d'écarts BLOQUANT / À CORRIGER | FINI (6 bloquants, ≈ 25 à corriger) |
| J3-02 | Plan des slides (10 min, sans code) + préparation des questions du jury | rédacteur technique | — | `docs/PLAN_SOUTENANCE.md` | FINI |
| J3-03 | `README.md` : construire, lancer A et B, tester, tracer les courbes | chef de projet | — | Commandes vérifiées | FINI |
| J3-04 | Corrections issues de l'audit, par les propriétaires des fichiers | propriétaires des fichiers | J3-01 | Aucun écart restant | FINI |
| J3-05 | Journal du jour 3 | opérateur / scribe | toutes | Entrées au format du brief | FINI |

## Préparation du robot réel (bonus, sans robot)

| Id | Description | Responsable | Dépend de | Critère de fini | Statut |
|---|---|---|---|---|---|
| R-01 | Barrière virtuelle (rectangle en repère odom) : fonction pure dans `random_logic.py` | ingénieur algorithmes | — | Python pur, testable | FINI |
| R-02 | `random_walker` : abonnement `/odom` + paramètre `fence` (désactivé par défaut) ; `config/nav2_params_real.yaml` ; keepout filter Nav2 (masque + config) ; script d'arrêt | développeur ROS | R-01 (contrat) | build OK | FINI |
| R-03 | `aspi_real_random.launch.py`, `aspi_real_planned.launch.py` (sans Gazebo, `use_sim_time` false par défaut) | chef de projet | R-02 | Launch valides | FINI |
| R-04 | `docs/JOUR_ROBOT.md` : réseau WSL2 (procédure seulement), plan B partage de connexion, checklist du jour | rédacteur technique | — | Commandes exactes, quoi faire si échec | FINI |
| R-05 | Tests en simulation de tout ce qui peut l'être (launch réels avec `use_sim_time:=true` + Gazebo, barrière, keepout) + tests pytest | ingénieur test | R-01..R-03 | Résultats rapportés | FINI |
| R-06 | Revue | relecteur | R-01..R-05 | Aucun BLOQUANT | FINI |
| R-07 | Journal + commit | opérateur / scribe, chef de projet | toutes | Entrée au journal | FINI |

## Séances robot réel (2026-10-09 et 2026-10-12) et clôture

| Id | Description | Responsable | Dépend de | Critère de fini | Statut |
|---|---|---|---|---|---|
| S-01 | Séance du 9/10 : carte réelle, runs A avec AMCL, incidents | étudiant + chef de projet | R-07 | Journal + RESULTATS 7.1–7.5 | FINI |
| S-02 | Phase 0 sans robot : détecteur de progression, mode static, diag_b.sh | ingénieur algorithmes + développeur ROS + ingénieur test | S-01 | Testé en simulation | FINI |
| S-03 | Séance du 12/10 : impasse Nav2 réel, suiveur coverage_follower, runs A et B (static) | étudiant + chef de projet | S-02 | 2 runs A + 2 runs B valides | FINI |
| S-04 | Revue du suiveur et des scripts de la séance, corrections de sécurité | relecteur + développeur ROS | S-03 | Aucun BLOQUANT | EN COURS |
| S-05 | Journal et RESULTATS (comparaison A/B réelle, limites de la localisation par odométrie) | opérateur / scribe + analyste résultats | S-03 | Chiffres recalculés depuis les CSV | FINI |
| S-06 | Architecture et algorigramme du suiveur | rédacteur technique | S-04 | Fidèle au code | EN COURS |
| S-07 | Simulation Gazebo avec fenêtres et captures d'écran (A puis B) pour les slides | chef de projet + ingénieur test | S-04 | Captures dans results/figures/ | À FAIRE |
| S-08 | Plan de soutenance : slides « Robot réel » et « Limites », question « pourquoi pas Nav2 sur le robot ? » | rédacteur technique | S-05, S-07 | PLAN_SOUTENANCE à jour | À FAIRE |

### Contrats robot réel (fixés par l'architecte)

- **Sécurité** : vitesse d'avance par défaut 0.10 m/s (A : `forward_speed`, B : RPP `desired_linear_vel`), rotation 0.6 rad/s.
  Arrêt : Ctrl+C du launch (le `random_walker` publie un Twist nul à l'arrêt ; l'executor annule le but) puis
  `scripts/stop_robot.sh` (publie un Twist nul sur `/cmd_vel` plusieurs fois).
- **LiDAR** : LDS-01 `range_min` 0.12 m, LDS-02 ≈ 0.16 m → `near_collision_distance` 0.20 m sur le robot réel
  (sinon métrique toujours nulle avec un LDS-02, même piège qu'au jour 1).
- **Barrière virtuelle A** — `random_logic.fence_distance_ahead(x, y, yaw, fence, front_angle) -> float` :
  `fence = (xmin, ymin, xmax, ymax)` en repère odom ; robot DANS le rectangle → distance minimale au bord le long de
  rayons du secteur avant [-front_angle, +front_angle] ; robot HORS du rectangle → 0.0 s'il s'éloigne du centre
  (force un virage), inf s'il revient vers le centre (|écart de cap vers le centre| < 90°). Le nœud prend
  `min(distance LiDAR, distance barrière)`. Paramètre `fence` = [] (désactivé) par défaut.
- **Mesure A sur le robot réel** : la carte sert de vérité terrain ; `map → odom` vient d'AMCL (localisation seule,
  pose initiale (0, 0, 0) fixée par paramètre) — le robot, lui, n'utilise pas la carte. Repli : TF statique identité
  (`localization:=static`) si AMCL pose problème (odométrie réelle qui dérive : limite).
- **Keepout B** : masque `maps/keepout.{yaml,pgm}` généré à partir de la carte et d'un rectangle autorisé
  (`scripts/make_keepout_mask.py`) ; `costmap_filter_info_server` + `map_server` du masque ; plugin
  `nav2_costmap_2d::KeepoutFilter` dans les costmaps global et local ; désactivé par défaut (`keepout:=false`).
  Le planner de couverture doit aussi exclure la zone interdite (même rectangle passé en paramètre, sinon des
  waypoints tomberaient dans la zone).

### Contrats jour 2 (fixés par l'architecte)

- **`coverage_planner`** — paramètres : `robot_radius` (0.105), `safety_margin` (0.05), `sweep_spacing` (0.18),
  `start_x` (0.0), `start_y` (0.0) (départ = origine de la carte = spawn). S'abonne à `/map` (RELIABLE +
  TRANSIENT_LOCAL), calcule `reachable_mask` puis `boustrophedon_waypoints` (fonctions de `planning.py`, les
  mêmes que le tracker), publie **une fois par carte reçue** `/coverage_path` (`nav_msgs/Path`, frame `map`,
  RELIABLE + TRANSIENT_LOCAL pour un abonné tardif). Log : nb de cellules atteignables et de waypoints.
- **`coverage_planner` (ajout jour 2)** — `plan_transitions` (False : essai T4 négatif), `transition_step` (0.3 m).
- **`coverage_executor`** — paramètres : `initial_x` (0.0), `initial_y` (0.0), `initial_yaw` (0.0),
  `max_duration` (0.0 = illimité ; le launch le règle à `run_duration + 10` s : arrêt propre après la mesure).
  Structure séquentielle (pas de callback bloquant) : `BasicNavigator` → attendre `/coverage_path` → pose initiale
  → attente de Nav2 **avec délais** (amcl actif → pose initiale republiée jusqu'à `/amcl_pose` → bt_navigator actif
  → waypoint_follower actif → serveur d'action prêt ; `waitUntilNav2Active` n'est PAS utilisé : attente sans délai,
  voir JOURNAL) → `followWaypoints` (5 essais si refus) → boucle de suivi `spin_once` + test du résultat (pas
  `isTaskComplete`, fuite mémoire, voir JOURNAL) ; sorties : but terminé, `max_duration`, serveur perdu depuis 3 s
  (temps monotone), arrêt. Waypoints manqués loggués.
- **Nav2** : `waypoint_follower.stop_on_failure: false` (waypoint inaccessible = sauté, conforme au brief).
  Tolérance d'arrivée `xy_goal_tolerance` abaissée de 0.25 à 0.15 m : avec un espacement de balayage de 0.18 m,
  0.25 m permettrait de « couper » les extrémités des lignes.
  Réglage retenu après essais T0–T4 : `loop_rate` 20, inflation 0.30 m / `cost_scaling_factor` 10, contrôleur
  Regulated Pure Pursuit à 0.15 m/s (= vitesse du random_walker) à la place de DWB ; essai T5 :
  `approach_velocity_scaling_dist` 0.2 et `waypoint_pause_duration` 0 (config finale).
- **Tracker** : inchangé, lancé avec `strategy: BOUSTROPHEDON`. Mesure à partir du 1er déplacement (le temps
  d'activation de Nav2 n'est pas compté).

## Contrats d'interface (fixés par l'architecte)

### `aspi_bot/planning.py` — Python pur (numpy), aucun import ROS

Convention : grille numpy `(height, width)`, indexée `[row, col]`, `row` = y croissant
(même ordre que `OccupancyGrid.data` ligne-major, origine en bas à gauche). Rotation de l'origine ignorée (= 0 pour map_server).

```python
occupancy_to_free(data, width, height, occupied_threshold=50) -> np.ndarray[bool]
    # True = libre ; -1 (inconnu) et >= seuil = obstacle
world_to_cell(x, y, origin_x, origin_y, resolution) -> (row, col)
cell_to_world(row, col, origin_x, origin_y, resolution) -> (x, y)   # centre de la cellule
reachable_mask(free, start_cell, resolution, robot_radius=0.105, safety_margin=0.05) -> np.ndarray[bool]
    # érosion par un disque de (robot_radius + safety_margin), puis composante connexe (4-voisinage)
    # contenant start_cell ; si start_cell n'est pas libre après érosion : cellule érodée libre la plus proche ;
    # masque vide si aucune.
disk_offsets(radius_cells) -> np.ndarray (N, 2)                    # décalages (drow, dcol) d'un disque
mark_covered(covered, reachable, row, col, radius_cells) -> int     # marque dans `covered` les cellules du disque
                                                                    # ∩ reachable ; renvoie le nb de nouvelles cellules
coverage_percent(covered, reachable) -> float                       # 0..100, 0 si reachable vide
boustrophedon_waypoints(reachable, origin_x, origin_y, resolution, sweep_spacing=0.18) -> list[(x, y, yaw)]
    # lignes horizontales tous les sweep_spacing, segments libres, sens alterné,
    # waypoints = extrémités de segments, yaw = sens de passage
```

### `aspi_bot/random_logic.py` — Python pur

```python
front_min_distance(ranges, angle_min, angle_increment, range_min, range_max, front_angle) -> float
    # min des distances valides dans [-front_angle, +front_angle] (angles normalisés dans [-pi, pi]) ;
    # ignore inf, nan, < range_min, > range_max ; renvoie inf si aucune valeur valide
class RandomWalkerLogic:
    def __init__(self, seed, forward_speed=0.15, turn_speed=1.0, stop_distance=0.25,
                 min_turn_deg=90.0, max_turn_deg=180.0)
    state: str                                      # 'FORWARD' ou 'TURN'
    def update(self, now_s: float, front_distance: float) -> (linear_x, angular_z)
    # FORWARD : avance ; si front_distance < stop_distance -> TURN d'un angle aléatoire dans
    #   [min,max] et de sens aléatoire (random.Random(seed)), fin de rotation = now + angle / turn_speed
    # TURN : tourne jusqu'à la fin de rotation, puis FORWARD si front_distance >= stop_distance,
    #   sinon nouveau tirage de rotation
```
Rotation **en temps** (pas d'odométrie) : le nœud n'a besoin que de `/scan` et de l'horloge ROS (sim time).

### Nœuds (interfaces fines)

| Nœud | Paramètres (défaut) |
|---|---|
| `random_walker` | `seed` (1), `forward_speed` (0.15), `turn_speed` (1.0), `stop_distance` (0.25), `front_angle_deg` (30.0), `control_rate` (10.0) |
| `coverage_tracker` | `strategy` ("RANDOM"), `seed` (0), `start_motion_threshold` (0.01), `robot_radius` (0.105), `safety_margin` (0.05), `cleaning_radius` (0.09), `near_collision_distance` (0.15), `pose_rate` (10.0), `run_duration` (600.0), `output_dir` ("~/ros2_ws/results"), `map_frame` ("map"), `base_frame` ("base_footprint") |

**Décision `near_collision_distance`** : le LiDAR simulé a `range_min = 0.12 m` > `robot_radius = 0.105 m`,
donc « obstacle < robot_radius » vaudrait toujours 0. Seuil paramétrable à 0.15 m, compté sur **front montant**
(un passage sous le seuil = 1 événement), sur 360°.

**Tracker** : le masque atteignable est calculé une fois, à la 1re pose reçue (TF `map → base_footprint`).
Numérateur = cellules couvertes ∩ masque atteignable (donc % ≤ 100). Distance = somme des déplacements entre poses.
Après `run_duration` s (temps simulé), le tracker écrit la dernière ligne, le log « fin du run » et cesse de mesurer.
CSV : `results/<strategy>_<seed>_<AAAAMMJJ-HHMMSS>.csv`, colonnes `time,coverage_percent,distance,near_collisions`.

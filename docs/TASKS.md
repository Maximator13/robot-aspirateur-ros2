# Tickets — Robot aspirateur (CCPP)

Statuts : `À FAIRE` · `EN COURS` · `REVUE` · `FINI` · `BLOQUÉ`
« Fini » = compile + tests OK + tourne en simu + relu + noté au journal.

## Jour 1 — Socle + stratégie A (MVP)

| Id | Description | Responsable | Dépend de | Critère de fini | Statut |
|---|---|---|---|---|---|
| J1-01 | Vérification de l'environnement (section 4) | chef de projet | — | Tableau rapporté à l'étudiant | FINI |
| J1-02 | Mise en place : `git init`, `.gitignore`, squelette `aspi_bot` | chef de projet | — | Arborescence créée | FINI |
| J1-03 | Carte de référence `maps/world.{yaml,pgm}` (Cartographer + téléop) **depuis le spawn** | chef de projet (exploration par random_walker) | — | Carte fermée, visible dans RViz | FINI |
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
| `coverage_tracker` | `strategy` ("RANDOM"), `seed` (0), `robot_radius` (0.105), `safety_margin` (0.05), `cleaning_radius` (0.09), `near_collision_distance` (0.15), `pose_rate` (10.0), `run_duration` (600.0), `output_dir` ("~/ros2_ws/results"), `map_frame` ("map"), `base_frame` ("base_footprint") |

**Décision `near_collision_distance`** : le LiDAR simulé a `range_min = 0.12 m` > `robot_radius = 0.105 m`,
donc « obstacle < robot_radius » vaudrait toujours 0. Seuil paramétrable à 0.15 m, compté sur **front montant**
(un passage sous le seuil = 1 événement), sur 360°.

**Tracker** : le masque atteignable est calculé une fois, à la 1re pose reçue (TF `map → base_footprint`).
Numérateur = cellules couvertes ∩ masque atteignable (donc % ≤ 100). Distance = somme des déplacements entre poses.
Après `run_duration` s (temps simulé), le tracker écrit la dernière ligne, le log « fin du run » et cesse de mesurer.
CSV : `results/<strategy>_<seed>_<AAAAMMJJ-HHMMSS>.csv`, colonnes `time,coverage_percent,distance,near_collisions`.

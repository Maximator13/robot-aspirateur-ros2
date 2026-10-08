# Architecture système

Version du jour 2. Stratégies A et B relues contre le code.

Sources vérifiées : `launch/sim.launch.py`, `launch/aspi_random.launch.py`, `launch/aspi_planned.launch.py`,
`random_walker_node.py`, `coverage_planner_node.py`, `coverage_executor_node.py`, `coverage_tracker_node.py`,
`config/nav2_params.yaml`, `aspi_interfaces/msg/CoverageStatus.msg`, `turtlebot3_burger/model.sdf` (plugins Gazebo),
`rviz/aspi.rviz`, et le `bringup_launch.py` / `navigation_launch.py` de `nav2_bringup` (Humble, installé).

---

## 1. Stratégie A : aléatoire (bump and turn)

Le robot n'utilise pas la carte. Elle sert uniquement de vérité terrain au tracker.

### 1.1 Schéma nœuds et topics

```mermaid
flowchart LR
    subgraph GZ["gzserver (Gazebo)"]
        direction TB
        DD["plugin diff_drive"]
        LIDAR["plugin LiDAR ray_sensor"]
    end
    RSP["robot_state_publisher"]
    MS["map_server<br/>lifecycle_manager_map"]
    RW["random_walker"]
    TR["coverage_tracker"]
    RV["rviz2"]
    CSV[("CSV<br/>results/")]

    LIDAR -- "/scan<br/>sensor_msgs/LaserScan<br/>BEST_EFFORT" --> RW
    LIDAR -- "/scan" --> TR
    RW -- "/cmd_vel<br/>geometry_msgs/Twist" --> DD
    DD -- "/odom<br/>nav_msgs/Odometry" --> RV
    MS -- "/map<br/>nav_msgs/OccupancyGrid<br/>TRANSIENT_LOCAL" --> TR
    MS -- "/map" --> RV
    TR -- "/coverage_map<br/>nav_msgs/OccupancyGrid<br/>TRANSIENT_LOCAL" --> RV
    TR -- "/coverage_status<br/>aspi_interfaces/CoverageStatus" --> OUT(["rosbag, analyse"])
    TR --> CSV
    RSP -- "/robot_description<br/>std_msgs/String" --> RV
```

Points à retenir :

- `/clock` (`rosgraph_msgs/Clock`, BEST_EFFORT) est publié par gzserver. Tous les nœuds ont `use_sim_time = True`. Il n'est pas dessiné pour la lisibilité.
- Le LiDAR publie à 5 Hz. `random_walker` commande à 10 Hz (timer). Le tracker lit la pose à 10 Hz et publie à 1 Hz.
- `spawn_entity.py` (nœud éphémère) insère le burger dans Gazebo, puis se termine. Timeout de 120 s.
- Le plugin `joint_state` publie aussi `/joint_states` (utilisé par `robot_state_publisher`) et l'IMU publie `/imu`. Non utilisés par nos nœuds.
- `/coverage_status` est enregistré dans le rosbag du run avec `/odom` et `/tf`.
- `gzclient` et `rviz2` sont absents en mode `headless:=true`.

### 1.2 Arbre TF

```mermaid
flowchart LR
    MAP["map"] -- "statique, translation 2.0 ; 0.5<br/>static_transform_publisher" --> ODOM["odom"]
    ODOM -- "dynamique<br/>plugin diff_drive Gazebo" --> BF["base_footprint"]
    BF -- "statique, /tf_static<br/>robot_state_publisher" --> BL["base_link"]
    BL -- "statique, /tf_static<br/>robot_state_publisher" --> BS["base_scan"]
```

Pourquoi `map → odom` vaut (2.0, 0.5) et non l'identité :

- Le plugin `diff_drive` publie `odom` dans le repère du monde Gazebo. Au spawn, `odom → base_footprint` vaut (-2.0, -0.5).
- La carte de référence a son origine au spawn.
- `map → odom` est donc la translation de moins la position de spawn. Le launch la calcule : `-spawn_x`, `-spawn_y`.
- Vérifié par lecture de `/odom` (voir JOURNAL, bug du premier run A).
- Limite : la dérive d'odométrie est négligée en simulation. Un décalage résiduel d'environ 4 cm existe (origine Cartographer), inférieur à une cellule de 5 cm.

Le tracker lit `map → base_footprint` (composée de la chaîne ci-dessus).

### 1.3 Launch : `aspi_random.launch.py`

La simulation (Gazebo, robot) vient de `sim.launch.py`, commun aux deux stratégies (voir section 3).

```mermaid
flowchart TB
    L["aspi_random.launch.py"]
    L --> SIM["sim.launch.py<br/>Gazebo + robot (section 3)"]
    L --> N3["map_server<br/>+ lifecycle_manager_map"]
    L --> N4["static_transform_publisher<br/>map vers odom"]
    L --> N5["random_walker"]
    L --> N6["coverage_tracker<br/>strategy = RANDOM"]
    L --> N7["rviz2<br/>sauf headless"]
```

Arguments du launch :

| Argument | Défaut | Rôle |
|---|---|---|
| `seed` | 1 | Graine du tirage aléatoire (walker, nom du CSV par le tracker, et gzserver) |
| `run_duration` | 600.0 | Durée du run en secondes simulées (typé float) |
| `headless` | false | `true` : ni gzclient ni RViz (transmis à `sim.launch.py`) |
| `fast` | false | `true` : monde accéléré (transmis à `sim.launch.py`) |
| `spawn_x`, `spawn_y` | -2.0, -0.5 | Position de spawn ; sert aussi à calculer `map → odom` |
| `map` | `maps/world.yaml` | Carte de référence (vérité terrain) |

### 1.4 Message `aspi_interfaces/msg/CoverageStatus`

| Champ | Type | Sens |
|---|---|---|
| `stamp` | `builtin_interfaces/Time` | Horodatage (temps simulé) |
| `strategy` | `string` | `RANDOM` ou `BOUSTROPHEDON` |
| `coverage_percent` | `float32` | Cellules couvertes / cellules atteignables |
| `distance_travelled` | `float32` | Mètres |
| `elapsed_time` | `float32` | Secondes depuis le début de la mesure |
| `near_collisions` | `uint32` | Passages sous `near_collision_distance` (0.15 m), front montant, LiDAR 360° |

### 1.5 CSV écrit par le tracker

- Fichier : `results/<strategie>_<seed>_<AAAAMMJJ-HHMMSS>.csv`.
- Colonnes : `time,coverage_percent,distance,near_collisions`.
- Une ligne par seconde simulée, à partir du début de la mesure (1er déplacement supérieur à 1 cm).
- Le fichier n'est ouvert qu'à ce moment : pas de CSV vide.
- Le tracker cesse de mesurer après `run_duration` et ferme le fichier.

---

## 2. Stratégie B : planifiée avec Nav2

Le robot utilise la carte : AMCL le localise, le planner calcule le balayage, Nav2 l'exécute.
`random_walker` n'est pas lancé. Le schéma est découpé en trois : nœuds du projet, intérieur de Nav2, TF.

### 2.1 Schéma des nœuds du projet

```mermaid
flowchart LR
    GZ["gzserver<br/>diff_drive + LiDAR"]
    MS["map_server<br/>(dans Nav2)"]
    PL["coverage_planner"]
    EX["coverage_executor<br/>BasicNavigator"]
    NAV["Nav2<br/>(détail en 2.2)"]
    AMCL["amcl"]
    TR["coverage_tracker<br/>strategy = BOUSTROPHEDON"]
    RV["rviz2"]
    OUT(["CSV, rosbag"])

    MS -- "/map<br/>nav_msgs/OccupancyGrid<br/>RELIABLE + TRANSIENT_LOCAL" --> PL
    MS -- "/map" --> TR
    PL -- "/coverage_path<br/>nav_msgs/Path<br/>RELIABLE + TRANSIENT_LOCAL" --> EX
    PL -- "/coverage_path" --> RV
    EX -- "/initialpose<br/>geometry_msgs/PoseWithCovarianceStamped" --> AMCL
    AMCL -- "/amcl_pose<br/>geometry_msgs/PoseWithCovarianceStamped" --> EX
    EX -- "action /follow_waypoints<br/>nav2_msgs/action/FollowWaypoints" --> NAV
    GZ -- "/scan<br/>sensor_msgs/LaserScan" --> TR
    NAV -- "/cmd_vel<br/>geometry_msgs/Twist" --> GZ
    TR -- "/coverage_map<br/>nav_msgs/OccupancyGrid" --> RV
    TR -- "/coverage_status<br/>aspi_interfaces/CoverageStatus" --> OUT
```

Rôles :

- `coverage_planner` : une publication par carte reçue. Départ de calcul en (0, 0), l'origine de la carte (spawn). Logique dans `planning.py`.
- `coverage_executor` : un `BasicNavigator` qui enchaîne pose initiale, attente de Nav2, `FollowWaypoints`, suivi. Il s'arrête de lui-même à `max_duration` (= `run_duration` + 10 s).
- `coverage_tracker` : identique à A, seul `strategy` change.
- `amcl` est dessiné à part du bloc Nav2 car l'executor dialogue directement avec lui (pose initiale, lecture de `/amcl_pose`).
- `/scan` va aussi vers AMCL et les costmaps de Nav2 (non dessiné ici, voir 2.2).

### 2.2 Intérieur de Nav2 (chaîne de commande)

```mermaid
flowchart LR
    EX["coverage_executor"]
    WF["waypoint_follower"]
    BT["bt_navigator"]
    PS["planner_server<br/>NavFn"]
    CS["controller_server<br/>Regulated Pure Pursuit"]
    VS["velocity_smoother"]
    BH["behavior_server<br/>spin, backup, wait"]
    GZ["gzserver<br/>diff_drive"]

    EX -- "action /follow_waypoints<br/>FollowWaypoints" --> WF
    WF -- "action navigate_to_pose<br/>NavigateToPose" --> BT
    BT -- "action compute_path_to_pose<br/>ComputePathToPose" --> PS
    PS -- "/plan<br/>nav_msgs/Path" --> RVZ(["rviz2"])
    BT -- "action follow_path<br/>FollowPath" --> CS
    BT -- "actions de recovery" --> BH
    CS -- "/cmd_vel_nav<br/>geometry_msgs/Twist" --> VS
    VS -- "/cmd_vel<br/>geometry_msgs/Twist" --> GZ
    BH -- "/cmd_vel<br/>(sans passer par le smoother)" --> GZ
```

Points à retenir :

- Les noms `/cmd_vel_nav` (sortie du contrôleur) et `/cmd_vel` (sortie du smoother) viennent des remappings de `navigation_launch.py` (vérifié, et mesuré : JOURNAL, « Mesure de la fréquence de contrôle »).
- Le smoother tourne à 20 Hz. `/cmd_vel` est donc à environ 21 Hz, alors que le contrôleur est à 10 Hz.
- Les nœuds `map_server`, `amcl`, `planner_server`, `controller_server`, `bt_navigator`, `waypoint_follower`, `smoother_server`, `behavior_server`, `velocity_smoother` et les deux lifecycle managers sont chargés comme composants dans un conteneur `nav2_container` (`component_container_isolated`, `use_composition` vaut True par défaut dans `bringup_launch.py`).
- Les costmaps locale et globale (couches obstacle, voxel, inflation) vivent dans `controller_server` et `planner_server`. Elles lisent `/scan` (non dessiné).
- Le contrôleur est Regulated Pure Pursuit (essai T3, retenu). Le planner global est NavFn, non modifié.
- `waypoint_follower.stop_on_failure` est à false : un waypoint en échec est sauté puis listé dans `missed_waypoints`.
- L'algorigramme du `coverage_executor` est dans `ALGORIGRAMMES.md`, section 3 (la fonction d'attente de Nav2 y est signalée « à vérifier »).

### 2.3 Arbre TF

```mermaid
flowchart LR
    MAP["map"] -- "dynamique<br/>amcl (localisation de Monte-Carlo)" --> ODOM["odom"]
    ODOM -- "dynamique<br/>plugin diff_drive" --> BF["base_footprint"]
    BF -- "statique<br/>robot_state_publisher" --> BL["base_link"]
    BL -- "statique<br/>robot_state_publisher" --> BS["base_scan"]
```

Différence avec A : `map → odom` vient d'AMCL, pas d'un TF statique.

- AMCL est un filtre particulaire (500 à 2000 particules, modèle de mesure `likelihood_field`) : localisation de Monte-Carlo, pas du scan matching.
- Il estime la pose du robot sur la carte, et publie la correction `map → odom`.
- Avant la pose initiale (fixée par l'executor via `/initialpose`), AMCL ne publie pas cette TF : le tracker attend.
- Le tracker lit le même `map → base_footprint` qu'en A.
- Fragilité observée : en mode accéléré, cette TF reste figée (« Transform data too old »). Voir section 4.

### 2.4 Launch : `aspi_planned.launch.py`

```mermaid
flowchart TB
    L["aspi_planned.launch.py"]
    L --> SIM["sim.launch.py<br/>Gazebo + robot (section 3)"]
    L --> NV["nav2_bringup / bringup_launch.py<br/>carte + params_file = nav2_params<br/>autostart, use_sim_time"]
    L --> P["coverage_planner<br/>start 0, 0 ; plan_transitions"]
    L --> E["coverage_executor<br/>pose initiale 0, 0, 0<br/>max_duration = run_duration + 10"]
    L --> T["coverage_tracker<br/>strategy = BOUSTROPHEDON"]
    L --> R["rviz2<br/>sauf headless"]
```

Arguments du launch :

| Argument | Défaut | Rôle |
|---|---|---|
| `seed` | 1 | Numéro du run : nomme le CSV (le balayage est déterministe) |
| `map` | `maps/world.yaml` | Carte pour Nav2 et vérité terrain du tracker |
| `nav2_params` | `config/nav2_params.yaml` | Paramètres Nav2. Nommé ainsi car `params_file` fuit vers `gzserver.launch.py` (JOURNAL, incidents d'exploitation) |
| `run_duration` | 600.0 | Durée du run en secondes simulées |
| `headless` | false | `true` : ni gzclient ni RViz |
| `fast` | false | `true` : monde accéléré. **Déconseillé pour B** (section 4) |
| `plan_transitions` | false | `true` : contournements calculés par le planner. Désactivé (essai T4 négatif) |
| `spawn_x`, `spawn_y` | -2.0, -0.5 | Position de spawn (transmise à `sim.launch.py`) |

### 2.5 Config Nav2 : écarts avec le `burger.yaml` de Humble

Base : `/opt/ros/humble/share/turtlebot3_navigation2/param/humble/burger.yaml`. Copie dans `src/aspi_bot/config/nav2_params.yaml` (jamais de modification de `/opt/ros`). Chaque écart est marqué `# aspi` dans le fichier. Les essais sont détaillés dans `docs/JOURNAL.md`.

| # | Paramètre | Original | aspi | Pourquoi |
|---|---|---|---|---|
| 1 | `use_sim_time` | selon nœud | True partout | Simulation Gazebo |
| 2 | `general_goal_checker.xy_goal_tolerance` | 0.25 m | 0.15 m | Espacement de balayage effectif de 0.20 m (0.18 arrondi sur la grille de 0.05) : 0.25 couperait les extrémités des lignes |
| 3 | `waypoint_follower.loop_rate` | 2000 | 20 | 2000 Hz saturait le CPU (37 000 lignes « Processing waypoint ») ; 20 est le défaut Nav2. Essai T1 |
| 4 | inflation des deux costmaps | rayon 1.0 (locale) et 0.55 (globale), échelle 3.0 | rayon 0.30, échelle 10.0 | Le planner garantit déjà une marge de 0.155 m. Une large inflation repousse les lignes vers l'intérieur. Essai T2 |
| 5 | `controller_server.FollowPath` | DWB | Regulated Pure Pursuit, vitesse 0.15 m/s, visée fixe 0.3 m, rotation sur place à 1.0 rad/s | DWB restait bloqué devant un pilier. Vitesses alignées sur `random_walker` pour une comparaison équitable. Essai T3 retenu : 28.5 % à 300 s contre 21.9 % |

Vérifiés sans changement : `amcl.robot_model_type = nav2_amcl::DifferentialMotionModel`, `waypoint_follower.stop_on_failure = false`.
La section `recoveries_server` est ignorée en Humble (le serveur s'appelle `behavior_server`) : valeurs par défaut appliquées.

Essais T0 à T4 : T0 original, T1 loop_rate, T2 inflation, T3 Regulated Pure Pursuit (retenu), T4 contournements du planner (impasse).
Essai T5 (approche et pause aux waypoints) : fichier `config/nav2_params_t5.yaml`, ticket J2-12 à faire. Non retenu à ce jour.

---

## 3. Launch commun : `sim.launch.py`

Inclus par `aspi_random.launch.py` et `aspi_planned.launch.py`. Les deux stratégies tournent ainsi dans le même monde, avec le même robot, au même point de départ.

```mermaid
flowchart TB
    S["sim.launch.py<br/>arguments : headless, fast, spawn_x, spawn_y"]
    S --> G1["gzserver.launch.py<br/>monde turtlebot3_world<br/>si fast = false"]
    S --> G2["gzserver.launch.py<br/>monde accéléré, lockstep<br/>si fast = true"]
    S --> G3["gzclient.launch.py<br/>sauf headless"]
    S --> R["robot_state_publisher.launch.py<br/>use_sim_time = true"]
    S --> SP["spawn_entity.py<br/>burger en spawn_x, spawn_y<br/>timeout 120 s"]
```

Le monde accéléré est une copie de `turtlebot3_world` dans `aspi_bot/worlds/`, avec `real_time_update_rate = 0`.

---

## 4. Modes de simulation

Deux modes existent. Le critère reste le temps simulé : le % couvert est tracé en fonction de l'horloge `/clock`.

| | Stratégie A | Stratégie B |
|---|---|---|
| Mode retenu | Accéléré (`fast:=true`, headless) | Temps réel |
| Validation | 5 critères fixés avant les runs, tous OK | 5 critères fixés avant les runs, 3 KO |
| Facteur | environ 2.8 (600 s simulées en 3.5 min) | non applicable |

**A en accéléré.** Critères : `/scan` à 5 Hz, `/cmd_vel` à 10 Hz, vitesse moyenne, near_collisions, % final.
Mesures : 5.00 Hz, 9.99 Hz, 0.120 m/s, 24 contre 27, 54.4 % contre 58.1 %. Les courbes sont superposées jusqu'à environ 5 min, puis divergent (marche aléatoire).

**B en temps réel.** Même vérification croisée (seed 1, 600 s) :

- Fréquence de `/cmd_vel_nav` : 4.42 Hz en accéléré contre 9.56 Hz en temps réel (critère KO).
- En accéléré, la TF `map → odom` d'AMCL reste figée à 89 s simulées (2 292 messages « Transform data too old »). AMCL décroche.
- Waypoints atteints : 8 contre 69 (KO). Incidents : 85 contre 1 (KO).
- Le % final paraît proche (56.8 % contre 54.1 %) mais les courbes divergent (53.6 % contre 29.0 % à 300 s) : le critère seul est trompeur.
- Cause probable (non démontrée) : les boucles de Nav2 sont cadencées en temps mural.

**Conséquence pour la comparaison.** A et B sont comparées en temps simulé, chacune dans un mode dont la fidélité est vérifiée.
Limites : modes différents, un seul run de B, facteur d'accélération dépendant de la charge de la machine.
Run de référence B (T3, seed 1, 600 s, temps réel) : 54.1 % de couverture, 61.9 m, 1 near_collision, 69 waypoints sur 112. A (3 seeds) : 51.0 ± 6.7 %.
Détails : `docs/JOURNAL.md`, entrées « Décision : simulation accélérée » et « vérification croisée ».

---

## 5. Pourquoi le tracker est commun aux deux stratégies

- Une comparaison honnête exige la même règle de mesure pour A et B.
- Même source de pose : TF `map → base_footprint`.
- Même dénominateur : le masque atteignable calculé par la même fonction de `planning.py`.
- Même rayon de nettoyage (0.09 m) et même seuil de quasi-collision (0.15 m).
- Même début de mesure : le premier déplacement. L'activation de Nav2 en B n'est donc pas comptée.
- Seul le champ `strategy` change, et il nomme le CSV.

## 6. Choix de conception

- **Python pur testable, nœuds fins.** Les algorithmes (`planning.py`, `random_logic.py`) n'importent pas ROS. Ils sont testés avec `pytest` sur de petites grilles. Un nœud = une responsabilité, simple à expliquer.
- **Masque atteignable partagé.** Le planner l'utilise pour tracer le balayage, le tracker pour le dénominateur. Le pourcentage est donc au plus 100 % et comparable.
- **Début de mesure au premier déplacement.** Les temps de démarrage varient sous WSL (spawn, activation de Nav2). Le temps du CSV ne les inclut pas.
- **Rotation du random_walker en temps.** Le nœud n'a que `/scan` en entrée, avec l'horloge simulée.
- **Carte figée au premier `/map`.** La vérité terrain ne change pas pendant un run.
- **Simulation commune.** `sim.launch.py` évite toute divergence de monde ou de robot entre A et B.

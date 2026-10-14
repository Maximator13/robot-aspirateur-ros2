# Robot aspirateur autonome — couverture d'une pièce (ROS 2 Humble, TurtleBot3 Burger)

> Projet réalisé seul en 12 h, en école d'ingénieur (IMT Mines Alès, cours ROS 2).

Un TurtleBot3 Burger doit couvrir la surface libre d'une pièce, en simulation (Gazebo) puis sur le
vrai robot avec son LiDAR. Deux stratégies sont comparées avec **la même mesure** :

- **A — aléatoire** (« bump and turn ») : sans carte, avance et tourne d'un angle aléatoire devant un obstacle ;
- **B — planifiée** : balayage boustrophédon calculé sur la carte, exécuté par Nav2 en simulation et par un
  suiveur de points de passage (`coverage_follower`) sur le robot réel.

Sur le robot réel, B atteint 80 % de couverture en environ 2 min (96,5 et 98,4 % en fin de trajet), contre
73 à 75 % en 5 min pour A.

Diaporama de soutenance : [`livrables/Robot_aspirateur_CCPP_ROS2.pptx`](livrables/Robot_aspirateur_CCPP_ROS2.pptx).
Résultats, démarche et limites : [`docs/RESULTATS.md`](docs/RESULTATS.md).
Architecture : [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · Algorigrammes : [`docs/ALGORIGRAMMES.md`](docs/ALGORIGRAMMES.md) ·
État de l'art : [`docs/ETAT_DE_L_ART.md`](docs/ETAT_DE_L_ART.md) · Journal d'ingénierie : [`docs/JOURNAL.md`](docs/JOURNAL.md) ·
Perspectives : [`docs/PERSPECTIVES.md`](docs/PERSPECTIVES.md).

## Contenu

| Chemin | Rôle |
|---|---|
| `src/aspi_interfaces/` | Message `CoverageStatus` (% couvert, distance, temps, near_collisions) |
| `src/aspi_bot/aspi_bot/planning.py` | Python pur : masque atteignable, mesure de couverture, boustrophédon |
| `src/aspi_bot/aspi_bot/random_logic.py` | Python pur : machine à états du robot aléatoire |
| `src/aspi_bot/aspi_bot/*_node.py` | Nœuds ROS 2 : `random_walker`, `coverage_planner`, `coverage_executor`, `coverage_follower`, `coverage_tracker` |
| `src/aspi_bot/launch/` | `sim.launch.py` (Gazebo commun), `aspi_random.launch.py` (A), `aspi_planned.launch.py` (B) ; robot réel : `aspi_real_random.launch.py`, `aspi_real_follow.launch.py` |
| `livrables/` | Diaporama de soutenance et documents en PDF |
| `src/aspi_bot/config/nav2_params.yaml` | Configuration Nav2 retenue (essais de réglage : `nav2_params_t*.yaml`) |
| `src/aspi_bot/maps/` | Carte de référence `turtlebot3_world` |
| `src/aspi_bot/test/` | Tests pytest des modules Python purs |
| `scripts/plot_results.py` | Courbes et tableau récapitulatif à partir des CSV |
| `results/` | CSV des runs officiels, figures, `summary.md` ; essais dans les sous-dossiers |

## Construire

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select aspi_interfaces aspi_bot
source install/setup.bash
```

## Tester (sans ROS)

```bash
cd ~/ros2_ws/src/aspi_bot && python3 -m pytest test/ -q
```

## Lancer

Stratégie A (aléatoire), avec fenêtres Gazebo et RViz :

```bash
ros2 launch aspi_bot aspi_random.launch.py seed:=1
```

Stratégie B (boustrophédon + Nav2) :

```bash
ros2 launch aspi_bot aspi_planned.launch.py seed:=1
```

Arguments utiles :

| Argument | Défaut | Rôle |
|---|---|---|
| `seed` | 1 | Graine (A) ; numéro du run dans le nom du CSV (A et B) |
| `run_duration` | 600.0 | Durée de la mesure, en secondes simulées |
| `headless` | false | `true` : ni fenêtre Gazebo ni RViz |
| `fast` | false | `true` : simulation accélérée — **validée pour A uniquement** |
| `nav2_params` | `config/nav2_params.yaml` | (B) fichier de paramètres Nav2 |
| `plan_transitions` | false | (B) contournements calculés par le planner (essai T4, négatif) |

Chaque run écrit `results/<STRATEGIE>_<seed>_<date>.csv` (colonnes `time, coverage_percent, distance, near_collisions`).

Protocole utilisé pour les résultats officiels (détails dans `docs/RESULTATS.md`) :

```bash
# A : 3 seeds, mode accéléré
ros2 launch aspi_bot aspi_random.launch.py seed:=<N> headless:=true fast:=true
# B : 3 runs, temps réel
ros2 launch aspi_bot aspi_planned.launch.py seed:=<N> headless:=true
```

## Tracer les résultats

```bash
cd ~/ros2_ws && python3 scripts/plot_results.py
# -> results/coverage_vs_time.png, results/coverage_vs_time_runs.png, results/summary.md
```

## Pièges connus (WSL)

- Si Gazebo reste noir : `export LIBGL_ALWAYS_SOFTWARE=1` avant le lancement.
- Le conteneur Nav2 survit parfois à Ctrl+C : vérifier avec `ps` et l'arrêter par son PID.
- Si Nav2 n'est pas actif après environ 90 s (log « Nav2 actif » absent), arrêter et relancer.

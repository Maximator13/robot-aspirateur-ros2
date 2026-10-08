# Journal d'ingénierie — Robot aspirateur (CCPP)

Format de chaque entrée : date · contexte · options envisagées · choix · justification · résultat / leçon.

### 2026-10-08 · Vérification de l'environnement

- **Contexte** : contrôle de l'installation ROS 2 Humble, TurtleBot3 burger et outils Python avant d'écrire du code.
- **Options envisagées** : aucune (simple vérification de conformité).
- **Choix** : aucune installation ; contrôle seul.
- **Justification** : les attendus de la section 4 du brief doivent être vérifiés avant tout développement.
- **Résultat-leçon** : tout est conforme. Ubuntu 22.04.5, `ROS_DISTRO=humble`, `TURTLEBOT3_MODEL=burger`, `ROS_DOMAIN_ID=30`, `ROS_LOCALHOST_ONLY=1`, setup de Gazebo sourcé dans `.bashrc`. 7 paquets TurtleBot3/Nav2 présents. numpy 1.21.5, matplotlib 3.5.1, pytest 6.2.5. setuptools 59.6.0 (version système, non concernée par le bug `canonicalize_version`, donc non modifiée). WSLg opérationnel (`WAYLAND_DISPLAY=wayland-0`, `DISPLAY=:0`).

### 2026-10-08 · Métrique near_collisions

- **Contexte** : la spécification « obstacle à moins de `robot_radius` » ne peut pas être mesurée avec le LiDAR simulé. Le `range_min` du burger (`model.sdf`) vaut 0.12 m, supérieur à `robot_radius` = 0.105 m. Les mesures inférieures à `range_min` sont invalides, donc la métrique serait toujours nulle.
- **Options envisagées** : garder la définition (métrique toujours nulle) ; seuil paramétrable plus grand ; contact physique via Gazebo (plus complexe).
- **Choix** : paramètre `near_collision_distance` = 0.15 m, sur 360°, compté sur front montant.
- **Justification** : métrique non triviale et comparable entre A et B.
- **Résultat-leçon** : confronter une spécification aux caractéristiques réelles du capteur.

### 2026-10-08 · Dénominateur de couverture et rotation du random walker

- **Contexte** : définition du pourcentage couvert et de la rotation de la stratégie A.
- **Choix (couverture)** : le % couvert = cellules couvertes ∩ masque atteignable / masque atteignable. Le masque est l'espace libre érodé de `robot_radius` + `safety_margin`, restreint à la composante connexe du départ, et fonction partagée dans `planning.py`. Le % est donc ≤ 100 et le dénominateur est le même pour A et B.
- **Choix (rotation)** : la rotation du random walker est faite en temps (angle / vitesse angulaire, horloge simulée) et non par odométrie, pour que le nœud n'ait que `/scan` en entrée.
- **Justification** : une comparaison A/B honnête exige le même dénominateur. Un nœud à entrée unique reste simple à expliquer.
- **Résultat-leçon** : limite notée : la rotation réelle peut différer légèrement de l'angle tiré (accélérations). Sans importance pour une stratégie aléatoire.

### 2026-10-08 · Revue de code du jour 1

- **Contexte** : relecture du livrable du jour 1 avant commit.
- **Options envisagées** : non applicable (revue, pas de choix d'architecture).
- **Choix** : un bloquant corrigé ; trois améliorations appliquées.
- **Justification** :
  - Bloquant : passer `run_duration:=600` au launch fait lire la valeur comme un entier. Le nœud plantait (`InvalidParameterTypeException`, paramètre déclaré en double). Correction : typage explicite avec `ParameterValue(value_type=float)`, et `int` pour `seed`.
  - Carte de vérité terrain figée à la première réception de `/map`.
  - `near_collisions` et CSV écrits seulement pendant la mesure (plus de CSV vides).
  - Début de la mesure au premier déplacement supérieur à 1 cm (paramètre `start_motion_threshold`). En stratégie B, l'activation de Nav2 ne consomme ainsi pas le temps de nettoyage. A et B sont mesurés à partir du même événement.
- **Résultat-leçon** : les arguments de launch sont typés par un parseur YAML. Typer explicitement les paramètres.

### 2026-10-08 · Balayage : dernière bande non couverte

- **Contexte** : en pièce vide, la répartition des lignes de balayage laissait la bande du haut non couverte. Le maximum en exécution parfaite était de 98 %.
- **Options envisagées** :
  - Ajouter une ligne en haut, proposée par le relecteur. Elle crée une ligne à une seule cellule de la précédente et casse le test d'espacement.
  - Recalculer le nombre de lignes et centrer le bloc de lignes.
- **Choix** : centrer le bloc, espacement constant.
- **Justification** : garde l'espacement constant et le test d'espacement valide.
- **Résultat-leçon** : 100 % en pièce vide simulée sur grille, 31 tests verts. Limite : les bords ne sont couverts que si le rayon de nettoyage est au moins égal à la moitié de l'espacement. Avec 0.09 m pour 0.18 m d'espacement, c'est juste suffisant.

### 2026-10-08 · Création de la carte de référence

- **Contexte** : l'étudiant ne pouvait pas piloter le robot en téléopération clavier. Il fallait une carte de la pièce pour la stratégie B et la vérité terrain.
- **Options envisagées** : téléopération clavier ; exploration par notre `random_walker` (seed 42) pendant environ 390 s simulées, avec Cartographer.
- **Choix** : `random_walker`.
- **Justification** : exploration automatique et reproductible. Premier test du nœud en simulation : 44 changements d'état, aucun blocage.
- **Résultat-leçon** :
  - Carte de 124 × 116 cellules à 0.05 m. L'hexagone est fermé et les 9 piliers sont nets.
  - Masque atteignable calculé par `planning.py` : 5564 cellules, soit 13.9 m².
  - Balayage boustrophédon : 112 waypoints.
  - Simulation proche du temps réel : 10 s simulées pour 10 s murales.

### 2026-10-08 · Incidents opérationnels

- **Contexte** : trois incidents pendant la création de la carte.
- **Options envisagées** : non applicable.
- **Choix** : aucun choix technique ; procédure corrigée.
- **Justification** : incidents sans conséquence sur les données, mais instructifs.
  - (a) `map_saver_cli` a échoué une fois sans message clair, puis réussi au second essai. La carte n'était probablement pas encore reçue dans le délai.
  - (b) Un `kill %1` a arrêté Cartographer au lieu d'un processus de test. Relancé sans conséquence, car le robot n'avait pas bougé.
  - (c) `pkill -f <motif>` a tué le shell qui l'exécutait, car le motif apparaissait dans sa propre ligne de commande.
- **Résultat-leçon** : réessayer avant de chercher plus loin. Arrêter les processus par PID, jamais par `kill %n` ni `pkill -f`.

### 2026-10-08 · Limite : origine de la carte

- **Contexte** : la TF `map → base_footprint` au départ vaut environ (0.037, 0.009) m, et non (0, 0). Cartographer prend son repère de suivi (IMU) comme origine.
- **Options envisagées** : non détaillées dans les sources.
- **Choix** : accepté et documenté.
- **Justification** : en stratégie A, le TF statique identité `map → odom` introduit un décalage d'environ 4 cm. Ce décalage est inférieur à une cellule (5 cm).
- **Résultat-leçon** : limite à mentionner dans `docs/RESULTATS.md`.

### 2026-10-08 · Bug majeur : premier run A invalide (repère odom)

- **Contexte** : run RANDOM seed 1, terminé sans plantage. Le masque atteignable ne compte que 754 cellules au lieu de 5564. Le % reste en paliers : 0 % de progression pendant plus de 5 min, alors que la distance croît.
- **Options envisagées** : non consignées.
- **Choix** :
  - Diagnostic : le plugin `diff_drive` de Gazebo publie `odom` dans le repère monde. Au spawn, `odom → base_footprint` vaut (-2.0, -0.5), vérifié en lisant `/odom`. La carte Cartographer a son origine au spawn. Le TF statique identité `map → odom` prévu par le brief décalait donc la trajectoire de 2 m, hors de la pièce.
  - Second bug, qui masquait le premier : `map_server` relisait les pixels inconnus (gris 205, p = 0.196) comme libres, car `free_thresh = 0.25`. L'extérieur de l'hexagone était donc « libre », et le tracker s'y est raccroché (cellule libre la plus proche).
  - Corrections : TF statique `map → odom` = (2.0, 0.5), calculé dans le launch à partir de la position de spawn. `free_thresh = 0.19` dans `world.yaml`.
  - Le run invalide est conservé dans `results/invalides/` pour traçabilité.
- **Justification** : le diagnostic repose sur une mesure (lecture de `/odom`), pas sur l'hypothèse du brief. Le contrôle de cohérence (nombre de cellules atteignables attendu) a révélé le bug.
- **Résultat-leçon** :
  - Une hypothèse du cahier des charges (« `map → odom` identité ») doit être vérifiée par une mesure.
  - Un contrôle de cohérence simple détecte les erreurs silencieuses.
  - Deux bugs peuvent se masquer mutuellement : corriger le premier ne suffit pas à révéler le second.

### 2026-10-08 · Incident : échec du spawn du robot sous WSL

- **Contexte** : à deux reprises, `spawn_entity.py` a abandonné après 30 s avec « Service /spawn_entity unavailable ». Gazebo démarrait trop lentement.
- **Options envisagées** : non applicable (incident d'exécution).
- **Choix** : contournement par spawn manuel avec les mêmes arguments (x = -2.0, y = -0.5). Action prévue : rendre le launch robuste, avec un délai ou un timeout de spawn plus long.
- **Justification** : le tracker démarre la mesure au premier déplacement. Le temps du CSV reste donc correct malgré le spawn tardif.
- **Résultat-leçon** : sous WSL, les temps de démarrage sont variables. Prévoir des marges dans les launch files.

### 2026-10-08 · Premier résultat de la stratégie A (MVP jour 1)

- **Contexte** : run RANDOM seed 1, 600 s simulées. Vérifications de démarrage OK : masque de 5564 cellules, `map → odom` = (2.0, 0.5).
- **Options envisagées** : non applicable (mesure).
- **Choix** : conservation du run comme premier résultat de référence.
- **Justification** : premier CSV et première courbe du MVP, produits avec le protocole de la section 6.
- **Résultat-leçon** :
  - Couverture finale : 58.1 %. 80 % non atteint. Distance : 72.0 m (0.12 m/s en moyenne). near_collisions : 27.
  - Couverture à 60 / 120 / 180 / 300 / 450 / 600 s : 10.6 / 14.1 / 19.6 / 25.2 / 36.5 / 58.1 %.
  - Croissance irrégulière, avec des plateaux : le robot repasse sur des zones déjà couvertes. La couverture accélère en 2e moitié, quand il atteint de nouvelles zones.
  - Simulation environ 1.4 fois plus lente que le temps réel. Sans conséquence, car tout est en temps simulé.
  - Fichiers : `results/coverage_vs_time.png`, `results/summary.md`, rosbag de 24 Mo.
  - Limite : un seul run, donc aucune conclusion statistique pour l'instant.

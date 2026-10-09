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
- **Résultat-leçon** : 100 % en pièce vide simulée sur grille, 31 tests verts. Limite : les bords ne sont couverts que si le rayon de nettoyage est au moins égal à la moitié de l'espacement. Le rayon demandé (0.09 m) est arrondi à 2 cellules (0.10 m) et l'espacement demandé (0.18 m) à 4 cellules (0.20 m) : la condition rayon ≥ espacement/2 est remplie grâce à ces arrondis.

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

### 2026-10-08 · Décision : simulation accélérée pour le protocole de la stratégie A

- **Contexte** : un run de 600 s simulées prenait environ 14 min murales (simulation à environ 0.7 × le temps réel sous WSL, fenêtres ouvertes). Le protocole demande plusieurs runs.
- **Options envisagées** : rester en temps réel avec fenêtres ; mode headless seul ; headless avec monde accéléré.
- **Choix** : launch avec deux arguments.
  - `headless:=true` : ni gzclient ni RViz.
  - `fast:=true` : copie du monde `turtlebot3_world` dans `aspi_bot/worlds/`, avec `real_time_update_rate = 0`. gzserver tourne en lockstep, pour que la physique attende la mise à jour des capteurs.
  - Spawn rendu robuste : timeout de 120 s au lieu de 30 s.
- **Justification** : méthode de validation avec des critères fixés avant le run. Même seed (1) en accéléré et run de référence en temps réel. Une courbe identique n'est pas attendue : une marche aléatoire diverge à la moindre différence de timing. On juge donc la fidélité du contrôle en temps simulé.
  - C1 : fréquence de `/scan` à 5 Hz ± 10 %.
  - C2 : fréquence de `/cmd_vel` à 10 Hz ± 10 %.
  - C3 : vitesse moyenne ± 15 %.
  - C4 : near_collisions du même ordre (rapport < 2).
  - C5 : % final ± 15 points.
- **Résultat-leçon** :
  - Résultats : C1 5.00 Hz OK ; C2 9.99 Hz OK ; C3 0.120 contre 0.12 m/s OK ; C4 24 contre 27 OK ; C5 54.4 % contre 58.1 % (écart de 3.7 points) OK.
  - Les deux courbes sont quasi superposées jusqu'à environ 5 min (écart inférieur à 1 point à 60, 180 et 300 s), puis divergent (30.1 contre 36.5 % à 450 s).
  - Facteur d'accélération de ×2.84 : 600 s simulées en environ 3.5 min murales, contre environ 14 min.
  - Décision : tous les runs officiels de la stratégie A sont en mode accéléré (le seed 1 officiel est le run accéléré). Le run temps réel est conservé dans `results/comparaison_vitesse/` comme référence de validation.
  - Vérifié en revue : `/clock` est publié à 10 Hz en temps simulé (pas de 0.1 s simulée, quelle que soit l'accélération), donc la granularité des timers ne change pas. Le lockstep ne synchronise pas les nœuds ROS : les fréquences sont donc vérifiées en temps simulé.
  - La graine du launch est aussi transmise à Gazebo (`gzserver.launch.py` déclare un argument `seed`). Choix assumé, pour une meilleure reproductibilité.
  - Limites : le facteur d'accélération dépend de la charge de la machine, à noter pour chaque run. Ne pas appliquer ce mode à Nav2 (stratégie B) sans une vérification croisée identique : la boucle de contrôle de Nav2 est probablement cadencée en temps mural. Elle serait alors ralentie en temps simulé, ce qui pénaliserait B.
  - Leçon : valider un changement de banc de test par des critères chiffrés fixés à l'avance.

### 2026-10-08 · Incidents mineurs : /clock et boucle d'attente

- **Contexte** : deux incidents pendant la mise au point du mode accéléré.
  - (a) Un abonné à `/clock` en QoS par défaut ne recevait aucun message.
  - (b) Une boucle d'attente laissée en arrière-plan par un run précédent a dû être arrêtée.
- **Options envisagées** : non applicable (incidents d'exécution).
- **Choix** :
  - (a) `/clock` est publié en BEST_EFFORT. L'abonnement utilise donc `qos_profile_sensor_data`.
  - (b) Aucune boucle d'attente ne doit rester en arrière-plan après un run.
- **Justification** : (a) une QoS incompatible entre éditeur et abonné empêche toute réception, sans message d'erreur explicite. (b) une boucle restante consomme des ressources et peut perturber le run suivant.
- **Résultat-leçon** : vérifier la QoS de chaque topic avant de s'abonner. Ne jamais laisser de boucle d'attente derrière soi.

### 2026-10-08 · Lancement du jour 2

- **Contexte** : début du jour 2, stratégie B planifiée (balayage boustrophédon exécuté par Nav2). Le travail est découpé en 10 tickets, J2-01 à J2-10, dans `docs/TASKS.md`.
- **Options envisagées** : config Nav2 issue du `burger.yaml` racine du paquet installé ; config issue de `turtlebot3_navigation2/param/humble/burger.yaml`. Pour Nav2 : simulation en temps réel ou en mode accéléré.
- **Choix** : base `turtlebot3_navigation2/param/humble/burger.yaml`. Nav2 testé d'abord en temps réel ; mode accéléré seulement après vérification croisée.
- **Justification** : le `burger.yaml` racine du paquet installé contient des éléments Jazzy (opennav_docking), inutilisables en Humble. La boucle de contrôle de Nav2 est probablement cadencée en temps mural : une accélération la pénaliserait, ce qui reste à vérifier.
- **Résultat-leçon** : écarts prévus, à documenter dans la config. `xy_goal_tolerance` passe de 0.25 à 0.15 m (espacement de balayage de 0.18 m). `stop_on_failure` est déjà à false et `robot_model_type` déjà à DifferentialMotionModel dans cette version : aucun changement nécessaire sur ces deux points.

### 2026-10-08 · Premier run B (réglage T0) : résultat décevant

- **Contexte** : premier run complet de la stratégie B (balayage boustrophédon exécuté par Nav2), en temps réel, 600 s.
  - Mise en route : Nav2 actif en environ 12 s ; planner et tracker d'accord (5564 cellules, 112 waypoints) ; pose de départ d'environ (0, 0).
  - Non-régression de la stratégie A après refactoring du launch : 10.5 % à 60 s (référence 10.46 %), OK.
  - Résultat B : 33.2 % couvert (A : 51.0 ± 6.7 %), 40.9 m parcourus (A : 70.8 m), 13 near_collisions. Balayage arrêté au waypoint 44/112, avec 1 waypoint manqué (indice 41).
  - Paliers : couverture bloquée entre 17 et 22 % de 3 à 8 min. Certains waypoints prennent 50 à 75 s (n° 20, 30, 32, 44), contre 3 à 20 s pour les autres.
  - Log Nav2 : 22 « Failed to make progress », 28 « Controller patience exceeded », recoveries (spin, backup), « Control loop missed its desired rate 10 Hz » répété. Facteur temps réel 0.91.
- **Options envisagées** :
  - Diagnostic (chef de projet, à confirmer par les runs de réglage) :
    - (1) La config TurtleBot3 règle `waypoint_follower.loop_rate` à 2000 Hz (défaut Nav2 : 20). Résultat : 37 000 lignes « Processing waypoint » dans le log, CPU saturé.
    - (2) Les waypoints bloquants sont tous près d'un pilier ou d'un mur. La costmap locale gonfle les obstacles de 1.0 m (globale : 0.55 m), alors que le planner place volontairement les lignes à au moins 0.155 m des obstacles. Le contrôleur DWB n'avance plus et déclenche les recoveries.
  - Corriger les deux causes d'un coup, ou un seul facteur à la fois avec mesure après chaque correction.
- **Choix** : un facteur à la fois, runs de réglage de 300 s pour gagner du temps, protocole final à 600 s.
  - T1 : `loop_rate` à 20 seul.
  - T2 : T1 + inflation à 0.30 m et `cost_scaling` à 10 dans les deux costmaps.
  - Run T0 conservé dans `results/reglages_B/`.
- **Justification** : mesurer chaque correction séparément permet d'attribuer l'effet de chacune.
- **Résultat-leçon** : une config « officielle » peut contenir des valeurs inadaptées. Les paramètres de sécurité de Nav2 (inflation) sont pensés pour la navigation point à point, pas pour la couverture, qui longe volontairement les obstacles.

### 2026-10-08 · Mesure de la fréquence de contrôle de Nav2

- **Contexte** : `/cmd_vel` est publié à 21 Hz en temps simulé. Cette fréquence n'est pas celle du contrôleur (10 Hz configuré).
- **Options envisagées** : non applicable (mesure).
- **Choix** : pour mesurer le contrôleur, enregistrer `/cmd_vel_nav`.
- **Justification** : `nav2_bringup` remappe la sortie du `controller_server` sur `/cmd_vel_nav` et ajoute un `velocity_smoother` (20 Hz) qui publie `/cmd_vel`. Le 21 Hz mesuré sur `/cmd_vel` vient donc du smoother.
- **Résultat-leçon** : lire le launch de bringup avant d'interpréter un topic.

### 2026-10-08 · Incidents d'exploitation sur la stratégie B

- **Contexte** : trois incidents lors des essais de la stratégie B.
  - (a) À l'arrêt, `component_container_isolated` (conteneur Nav2) survit à SIGINT et SIGTERM.
  - (b) À l'arrêt, `coverage_executor` levait une exception.
  - (c) L'argument de launch `params_file` fuyait vers `gzserver`.
- **Options envisagées** : non applicable (incidents d'exécution).
- **Choix** :
  - (a) arrêt par SIGKILL sur le PID du conteneur ;
  - (b) exception corrigée ;
  - (c) argument renommé `nav2_params`.
- **Justification** : (c) les arguments de launch ne sont pas cloisonnés entre nœuds inclus en ROS 2 Humble.
- **Résultat-leçon** : les arguments de launch sont partagés entre les nœuds inclus : leur donner des noms spécifiques. Un conteneur Nav2 peut survivre à l'arrêt normal : vérifier son PID après chaque run.

### 2026-10-08 · Stratégie B : réglages T1 et T2 (surcharge CPU et inflation)

- **Contexte** : essais de 300 s en temps réel sur la stratégie B. Pourcentage couvert à 180 s / 300 s : T0 17.4 / 19.5 ; T1 17.5 / 18.2 ; T2 21.9 / 21.9.
- **Options envisagées** : un facteur à la fois, chacun mesuré séparément. T1 : `loop_rate` à 20. T2 : T1 plus inflation à 0.30 m et `cost_scaling` à 10 dans les deux costmaps.
- **Choix** : T1 et T2 testés successivement, sans les cumuler sans mesure.
- **Justification** : T1 supprime la surcharge CPU (« Processing waypoint » : 18 741 → 215 lignes ; contrôleur à 10.15 Hz en temps simulé, facteur temps réel 0.90) mais ne change pas le comportement. T2 accélère le début (+4 points à 180 s) mais le robot reste bloqué de 177 s à la fin.
- **Résultat-leçon** : cause localisée du blocage : une ligne de balayage coupée par un pilier (waypoints (3.52, -0.67) puis (2.77, -0.67) ; pilier en x 2.96–3.27, y -0.72 à -0.42). Le robot finit le premier segment face au pilier à 0.25 m. DWB oscille (vx ≈ 0, wz ±0.03 à 0.18 rad/s) sans contourner. La surcharge CPU était un vrai défaut, mais pas la cause du blocage. Mesurer chaque correction séparément évite de conclure trop vite. Pendant T1, la TF map→odom vue par le conteneur Nav2 est restée figée à ≈ 234 s simulées (739 messages « Transform data too old » sur tout le log) alors que le flux était publié ; phénomène non reproduit en T0 ni T2, puis revu en mode accéléré et au run officiel B3.

### 2026-10-08 · Stratégie B : contrôleur Regulated Pure Pursuit (T3)

- **Contexte** : le contrôleur DWB reste bloqué au pilier (entrée précédente). Essai d'un autre contrôleur de Nav2, Regulated Pure Pursuit (RPP).
- **Options envisagées** :
  - changer de contrôleur ;
  - calculer les contournements dans notre planner (T4) ;
  - décomposition cellulaire de Choset (trop long pour 3 jours).
- **Choix** : changer de contrôleur (T3). Réglages alignés sur la stratégie A pour une comparaison équitable : vitesse de 0.15 m/s (celle de `random_walker` ; DWB autorisait 0.22 m/s), rotation sur place à 1.0 rad/s (celle de `random_walker`), pas de ralentissement près des obstacles.
- **Justification** : le changement de contrôleur (DWB → RPP, avec une vitesse ramenée de 0.22 à 0.15 m/s) a supprimé le blocage ; DWB n'a pas été testé à 0.15 m/s, on ne peut donc pas attribuer le gain au seul algorithme. RPP n'a pas été comparé à d'autres contrôleurs.
- **Résultat-leçon** : à 300 s, T3 atteint 28.5 % de couverture (T2 : 21.9 %), 30.5 m parcourus, 1 near_collision (T2 : 5), 0 « Failed to make progress » (T2 : 13), 0 recovery. Dernier waypoint : 37/112 démarré (36 atteints) (T2 : 19). Le passage du pilier prend environ 13 s : rotation sur place puis contournement par le sud. Limites restantes : la vitesse (0.15 m/s) et les rotations sur place (environ 48 s sur 300 s).

### 2026-10-08 · Stratégie B : contournements calculés par le planner (T4, impasse)

- **Contexte** : après T3, les lignes de balayage restent coupées par les obstacles. Essai de contournements calculés par notre planner.
- **Options envisagées** : garder T3 seul ; ajouter des points de contournement calculés par le planner (T4).
- **Choix** : T3 retenu. `plan_transitions` est conservé, testé, et désactivé par défaut (argument de launch).
- **Justification** : principe de `plan_transitions` : fonction pure, Dijkstra sur le 8-voisinage du masque atteignable, simplification par visibilité, tronçons ≤ 0.3 m. Résultat : 112 → 245 waypoints, 49 transitions corrigées, 0 point hors masque, 8 tests unitaires (39 tests au total). Bug trouvé pendant le développement : des tronçons à 45° passaient exactement sur un coin de cellule, et l'arrondi les rangeait hors masque. Correction par un test exact de segment. Résultat T4 (T3 plus contournements) à 300 s : 22.4 % contre 28.5 % pour T3 ; 25 à 26 waypoints d'origine atteints contre 36 ; 43 « collision ahead » (RPP), 8 « patience exceeded », 3 recoveries. Les points intermédiaires consomment 38 % du temps, car chaque but déclenche une replanification et une rotation.
- **Résultat-leçon** : avec RPP, Nav2 contourne déjà les obstacles. Cause non démontrée : notre marge (0.155 m) est au-dessus du rayon inscrit (0.10 m), donc hors zone létale ; une hypothèse est que les plans NavFn entre points intermédiaires rasent les piliers à 0.10–0.15 m. Une amélioration algorithmique « évidente » doit être mesurée : elle peut être contre-productive selon le reste de la chaîne.

### 2026-10-08 · Bug : fuite mémoire de coverage_executor

- **Contexte** : un executor orphelin occupait 4.8 Go de RAM (80 %) et survivait à SIGINT.
- **Options envisagées** : non consignées.
- **Choix** : boucle `spin_once` avec test du future. Sortie si rclpy n'est plus ok ou si le serveur d'action disparaît. Annulation avec délai. Paramètre `max_duration`, réglé par le launch à `run_duration` + 10 s.
- **Justification** : cause, par lecture du code de rclpy et de `nav2_simple_commander` (Humble) : le gestionnaire de signal de rclpy éteint le contexte sans lever `KeyboardInterrupt`. La boucle `while not isTaskComplete()` ne testait pas `rclpy.ok()` et tournait à vide. Chaque appel à `spin_until_future_complete` ajoutait un callback au même future, jamais résolu.
- **Résultat-leçon** : vérifié pendant T4, mémoire stable (74.7 → 74.9 Mo en 4 min). Une boucle d'attente doit toujours tester l'état du contexte ROS et avoir une sortie explicite.

### 2026-10-08 · Écart de 245 / 247 waypoints entre le nœud et le calcul hors ligne

- **Contexte** : le nœud produit 245 waypoints, le calcul hors ligne 247 pour la même carte.
- **Options envisagées** : non applicable (explication d'un écart constaté).
- **Choix** : aucune correction ; les deux résultats sont valides (0 transition non résolue, 0 tronçon hors masque).
- **Justification** : la résolution de `nav_msgs/OccupancyGrid` est un float32 (0.05 devient 0.05000000074…). Cet arrondi minime déplace quelques points de simplification situés exactement sur des frontières de cellules.
- **Résultat-leçon** : connaître les types des messages ROS (float32) quand on compare un calcul hors ligne et un calcul en ligne.

### 2026-10-08 · Stratégie B : vérification croisée temps réel / accéléré (négative)

- **Contexte** : même vérification que pour la stratégie A, appliquée à la stratégie B (config T3, seed 1, 600 s). Le risque avait été identifié en revue : les boucles de Nav2 sont peut-être cadencées en temps mural.
- **Options envisagées** : accepter le mode accéléré pour B ; mesurer B en temps réel uniquement. Critères fixés avant les runs :
  - C1 : fréquence de `/cmd_vel_nav` à 10 Hz ± 10 % en temps simulé ;
  - C2 : fréquence de `/scan` à 5 Hz ± 10 % ;
  - C3 : % final ± 5 points ;
  - C4 : nombre de waypoints atteints ± 10 % ;
  - C5 : nombre d'incidents ≤ valeur en temps réel + 3.
- **Choix** : mesure de B en temps réel uniquement. La stratégie A reste en mode accéléré, validé par ses propres critères.
- **Justification** : ce qui est comparé est le % couvert en fonction du temps simulé. Chaque stratégie doit donc être mesurée dans un mode où son comportement en temps simulé est vérifié fidèle.
- **Résultats** (valeurs F = accéléré, R = temps réel) :
  - C1 KO : F 4.42 Hz, R 9.56 Hz ;
  - C2 OK : F 5.00 Hz ;
  - C3 « OK » en apparence : F 56.8 %, R 54.1 %. Trompeur : les courbes divergent (F 53.6 %, R 29.0 % à 300 s) ;
  - C4 KO : F 8 waypoints, R 69 ;
  - C5 KO : F 85 incidents, R 1.
  - En F, la TF `map → odom` vue par Nav2 reste figée à 89 s simulées (2 292 messages « Transform data too old »), avec 55 near_collisions. F a parcouru 510 m en zigzags et recoveries, contre 61.9 m en R. Facteur d'accélération obtenu : environ 1.9 seulement.
- **Résultat-leçon** : le mode accéléré est négatif pour B. Un critère isolé (C3) peut sembler bon par hasard : il faut plusieurs critères, dont des critères de comportement. Le risque identifié en revue était fondé.

### 2026-10-08 · Stratégie B : run de référence en temps réel (T3, seed 1)

- **Contexte** : premier run de référence de la stratégie B, config T3, seed 1, 600 s, en temps réel.
- **Options envisagées** : non applicable (mesure).
- **Choix** : ce run est retenu comme référence de B, en temps réel, suite à la vérification croisée négative de l'entrée précédente.
- **Justification** : seul mode de mesure validé pour la stratégie B.
- **Résultat-leçon** :
  - Couverture finale : 54.1 % (A : 51.0 ± 6.7 %). 80 % non atteint. Distance : 61.9 m. near_collisions : 1.
  - Waypoints : 69 atteints sur 112. Un « Failed to make progress », 0 recovery. Facteur temps réel : 0.95 (mesuré 0.952).
  - L'executor s'arrête seul à `max_duration` (610 s). Sa mémoire reste stable, environ 74 Mo : le correctif de fuite est confirmé.
  - Limite : un seul run, donc aucune conclusion statistique.

### 2026-10-08 · Incident : Nav2 bloqué à l'attente d'activation (run B)

- **Contexte** : au premier lancement du run R, l'executor est resté bloqué sur l'attente de Nav2 (`waitUntilNav2Active`). Avertissement précédent dans le log : « amcl: failed to send response to /amcl/get_state (timeout) ». Fréquence : 1 lancement sur 3.
- **Options envisagées** : non consignées.
- **Choix** : procédure. Si Nav2 n'est pas actif 90 s après le lancement, arrêter et relancer. Le cas est noté comme incident.
- **Justification** : `BasicNavigator` n'a pas de délai d'attente. La sortie doit donc être gérée à l'extérieur du nœud.
- **Résultat-leçon** : un blocage intermittent ne doit pas être pris pour un résultat. Limite à noter dans `docs/RESULTATS.md`.

### 2026-10-08 · Essai T5 : suppression du ralentissement aux waypoints

- **Contexte** : en revue, le relecteur a relevé deux pertes de temps dans la configuration T3. Le contrôleur RPP ralentit avant chaque but (`approach_velocity_scaling_dist`, défaut 0.6 m, jusqu'à `min_approach_linear_velocity`). Le `waypoint_follower` marque en outre une pause de 200 ms à chaque waypoint. Estimation non mesurée : plusieurs minutes perdues sur 10.
- **Options envisagées** : garder T3 ; réduire le ralentissement et la pause (T5).
- **Choix** : `approach_velocity_scaling_dist` = 0.2 m (juste au-dessus de `xy_goal_tolerance` = 0.15 m) et `waypoint_pause_duration` = 0. T5 devient la configuration officielle (`nav2_params.yaml`). Fin des réglages de la stratégie B.
- **Justification** : mesure en temps réel, 600 s, T3 (seed 1) contre T5 (seed 5).
  - Couverture à 300 s : 29.0 % contre 30.6 %.
  - Couverture à 450 s : 39.8 % contre 47.3 %.
  - Couverture finale : 54.1 % contre 59.7 %.
  - Waypoints atteints : 69 contre 73.
  - Distance : 61.9 m contre 69.8 m.
  - Vitesse moyenne en translation : 0.131 m/s contre 0.147 m/s.
  - Rotation sur place : 18 % du temps dans les deux cas.
  - Recoveries : 0 dans les deux cas. T5 a eu 2 « controller patience exceeded », soit environ 5 s perdues.
- **Résultat-leçon** : gain net sur le même protocole, mais un seul run par configuration : la différence ne suffit pas à conclure statistiquement. Restent 18 % du temps en rotation sur place et quelques arrêts d'environ 30 s sur les petits segments entre lignes ; ce sont les perspectives de la stratégie B.

### 2026-10-08 · Correctif : blocage de l'executor au démarrage

- **Contexte** : sur 5 lancements, l'executor est resté bloqué 2 fois au démarrage. Avertissement dans le log : « amcl: failed to send response to /amcl/get_state (timeout) ».
- **Options envisagées** : non consignées.
- **Choix** :
  - fonction locale `wait_nav2_active` : interrogation du service `GetState` avec un délai de 2 s et un nouvel essai ;
  - la pose initiale est republiée jusqu'à réception sur `/amcl_pose` ;
  - plus aucune attente sans délai dans l'executor ;
  - `rclpy` est initialisé avec `SignalHandlerOptions.NO`, pour que SIGINT lève `KeyboardInterrupt`.
- **Justification** : mécanisme identifié dans le code de `nav2_simple_commander` (Humble, attente sans délai) ; la perte de la réponse elle-même n'a pas été observée directement. `_waitForNodeToActivate` appelle `spin_until_future_complete` sans délai sur la réponse du service `GetState`. Si la réponse est perdue, le processus reste bloqué dans cette attente en code C : l'interpréteur Python ne reprend jamais la main et SIGINT n'est jamais traité. Voir aussi l'entrée « SIGINT ignoré par les processus lancés en arrière-plan » : le Ctrl+C ignoré s'explique au moins en partie par la méthode de lancement.
- **Résultat-leçon** : à valider pendant les runs officiels de la stratégie B. Une bibliothèque « simple » peut cacher une attente infinie : toute attente réseau doit avoir un délai.

### 2026-10-08 · Correctif : course au démarrage de Nav2 (but FollowWaypoints rejeté)

- **Contexte** : le correctif d'attente de Nav2 (`wait_nav2_active`) n'attendait que `amcl` et `bt_navigator`. Le `lifecycle_manager` active les nœuds en séquence. Le but `FollowWaypoints` partait 0.5 ms après « Nav2 actif », alors que `waypoint_follower` n'était activé que 0.1 s plus tard. Résultat : « request was rejected », 2 lancements sur 2, aucun CSV produit.
- **Options envisagées** : non consignées.
- **Choix** : attendre aussi `waypoint_follower`, puis le serveur d'action `FollowWaypoints`. Cinq essais si le but est rejeté.
- **Justification** : explication vérifiée dans le code de Nav2 en revue. Le serveur d'action existe dès la configuration du nœud, mais il rejette les buts tant que le nœud n'est pas activé. L'ancien `waitUntilNav2Active` masquait la course par des pauses de 2 s.
- **Résultat-leçon** :
  - 3 démarrages sur 3 conformes (Nav2 actif en 10 à 17 s).
  - Un correctif peut créer un autre bug. Le test d'intégration avec vérifications de démarrage l'a attrapé avant de fausser une mesure.

### 2026-10-08 · Protocole officiel B (config T5, temps réel, 600 s, 3 runs)

- **Contexte** : protocole officiel de la stratégie B, config T5, en temps réel, 600 s, 3 runs.
- **Options envisagées** : non applicable (mesure).
- **Choix** : résultats rapportés tels quels, sans retirer de run.
- **Justification** : comparaison A/B sur le protocole défini (3 runs, 600 s). Limite à noter : la stratégie A est mesurée en mode accéléré, la stratégie B en temps réel.
- **Résultat-leçon** :
  - B1 : 59.8 % de couverture, 70.2 m, 0 near_collision, 71/112 waypoints.
  - B2 : 55.4 %, 62.2 m, 2 near_collisions, 70/112 waypoints.
  - B3 : 17.2 %, 29.5 m, 25 near_collisions, 14/112 waypoints.
  - Moyenne B : 44.1 ± 23.4 %. A (3 runs accélérés) : 51.0 ± 6.7 %.
  - 80 % jamais atteint. Moyennes de A et B à moins de 4 points jusqu'à 540 s (B3 tire la moyenne de B vers le bas) ; B1 et B2 devant la moyenne de A dès ≈ 4 min.
  - Dispersion de B nettement plus forte que celle de A. Avec 3 runs, aucune conclusion statistique solide.

### 2026-10-08 · Run B3 : TF figée dans Nav2 et choix de la moyenne officielle

- **Contexte** : à environ 135 s simulées, la TF `map → odom` vue par le conteneur Nav2 reste figée (4 329 messages « Transform data too old »). Le rosbag montre qu'AMCL la publie sans interruption (5 Hz, aucun trou supérieur à 1 s). Nav2 croit le robot immobile : 42 « Failed to make progress », puis recoveries, et 71 « Behavior Tree tick rate exceeded ». Même phénomène déjà vu en essai T1 et en mode accéléré. Cause non identifiée (charge CPU sous WSL, DDS, buffer TF ?).
- **Options envisagées** : garder B3 dans la moyenne ; garder B3 et ajouter un 4e run ; diagnostiquer d'abord ; exclure B3.
- **Choix** (de l'étudiant) : garder B3 dans la moyenne officielle, et indiquer à côté « 2 runs sur 3 terminés normalement : 57.6 % ».
- **Justification** : ne pas écarter un résultat après l'avoir vu. C'est une limite de fiabilité de la stratégie B dans notre environnement, à présenter comme telle.
- **Résultat-leçon** : la fiabilité fait partie de la performance. Une stratégie plus « intelligente » dépend d'une pile logicielle plus lourde et plus fragile.

### 2026-10-08 · Refactoring de lisibilité de coverage_executor et non-régression

- **Contexte** : après le protocole officiel, la fonction d'attente de Nav2 de `coverage_executor` (environ 55 lignes, 3 boucles imbriquées) est difficile à défendre devant le jury. Le code a changé après les mesures.
- **Options envisagées** : non précisées dans le compte rendu source (à compléter si nécessaire).
- **Choix** : découpage de la fonction d'attente en petites fonctions (attente d'un nœud actif, attente de la pose initiale, attente du serveur d'action). Annulation protégée regroupée dans une seule fonction.
- **Justification** : un nœud = une responsabilité, et chaque fonction doit pouvoir être expliquée en une phrase. Comme le code a changé après les mesures, un essai de non-régression en simulation a été fait (120 s, temps réel).
- **Résultat-leçon** : séquence de démarrage conforme (amcl actif, pose initiale, bt_navigator actif, waypoint_follower actif, Nav2 actif, 112 waypoints). Couverture à 60 s et 120 s : 7.6 % et 15.4 %, à comparer aux runs officiels B1/B2 (8.3–8.4 % à 60 s, 15.5–16.2 % à 120 s). Arrêt automatique à `max_duration` avec annulation du but (« Goal was canceled. Stopping the robot. »). Arrêt manuel par SIGINT en 1 s. Toute modification faite après une mesure demande une non-régression, même si elle semble purement cosmétique. Il s'agit d'un seul essai, pas d'une campagne.

### 2026-10-08 · Découverte : SIGINT ignoré par les processus lancés en arrière-plan

- **Contexte** : pendant la journée, plusieurs processus `coverage_executor` survivaient à Ctrl+C. Un `kill -INT` envoyé directement à l'executor était ignoré. `/proc/<pid>/status` montrait SIGINT dans les signaux ignorés.
- **Options envisagées** : non consignées.
- **Choix** : relancer le test avec SIGINT remis par défaut, et ne pas modifier le code de l'executor pour ce motif.
- **Justification** : un processus lancé en arrière-plan (`&`, `nohup`) par un shell non interactif hérite d'un SIGINT ignoré. Python n'installe alors pas son gestionnaire de SIGINT. Ce mécanisme explique au moins en partie les executors survivants observés. Ce n'était donc pas uniquement un défaut de notre code.
- **Résultat-leçon** : avant de conclure à un bug du code testé, vérifier l'outil de test (signaux hérités, environnement du shell). La méthode de test a été corrigée.

### 2026-10-08 · Jour 3 du plan — code gelé, pas de vidéo de démonstration

- **Contexte** : le jour 3 est consacré à l'évaluation et aux livrables. Le cahier de soutenance demande « vidéo ou captures de la démo ».
- **Options envisagées** :
  - vidéo d'environ 30 s (Gazebo + RViz), enregistrée par l'étudiant sous Windows ;
  - captures : figures de `results/` (couverture en fonction du temps, courbes par run), capture RViz éventuelle.
- **Choix** (décision de l'étudiant) : pas de vidéo. Les figures de `results/` (couverture en fonction du temps, courbes par run) servent de captures de démo.
- **Justification** : choix de l'étudiant.
- **Résultat-leçon** : code gelé. Le jour 3 ne contient que l'audit de cohérence des documents, le plan des slides avec la préparation des questions du jury, et un README d'utilisation.

### 2026-10-08 · Préparation du robot réel (bonus), sans robot

- **Contexte** : séance prévue à l'école avec un TurtleBot3 Burger réel. Le robot n'est pas disponible pour l'instant : la préparation est testée uniquement en simulation.
- **Options envisagées** :
  - zone de test : murs en carton (plan principal) ; barrière virtuelle en repère odom (en option) ; keepout filter de Nav2 pour la stratégie B (en option) ;
  - mesure de la stratégie A : localisation AMCL (utilisée pour la mesure seulement) ou TF statique `map → odom` en repli.
- **Choix** :
  - deux launch sans Gazebo : `aspi_real_random` et `aspi_real_planned`, avec `use_sim_time` à false par défaut (true pour les tester avec Gazebo) ;
  - vitesses réduites : 0.10 m/s en translation, 0.6 rad/s en rotation ;
  - `near_collision_distance` = 0.20 m ;
  - mesure de A via AMCL, TF statique en repli ; zone limitée par des murs en carton ;
  - CSV du robot dans `results/robot_reel/` ;
  - procédure réseau WSL2 et checklist dans `docs/JOUR_ROBOT.md`. Aucune modification de `.bashrc` ni de `.wslconfig`.
- **Justification** : le LDS-02 a une portée minimale d'environ 0.16 m. Avec 0.15 m, la métrique serait toujours nulle, même piège qu'au jour 1. Le seuil de 0.20 m est au-dessus de cette portée minimale.
- **Résultat-leçon** : résultats des tests en simulation :
  - barrière A : le robot reste dans le rectangle ; arrêt à environ 0.25 m avant le bord, dépassement maximal d'environ 0.13 m ;
  - stratégie B à 0.10 m/s : 12.2 % de couverture en 120 s ;
  - keepout : fonctionne, mais un départ sur le bord de la zone autorisée empêche tout mouvement (collision détectée dès le premier pas, 75 messages « patience exceeded ») ;
  - avec une marge de 0.5 m autour du départ : 30.7 % en 120 s, et le robot reste dans la zone. Le script de masque refuse désormais une zone sans marge de 0.5 m autour du départ.

### 2026-10-08 · Sécurité : un Ctrl+C n'arrêtait pas le robot

- **Contexte** : en test avec Gazebo, après Ctrl+C du launch, le `random_walker` s'arrêtait sans publier de vitesse nulle. La dernière consigne (0.10 m/s) restait appliquée et le robot continuait tout droit. Le TurtleBot3 réel garde aussi la dernière consigne reçue.
- **Options envisagées** : correctif dans le nœud ; procédure seule (Ctrl+C puis arrêt manuel). La procédure a été conservée en complément du correctif.
- **Choix** : rclpy initialisé sans gestionnaire de signal ; 5 vitesses nulles publiées à l'arrêt ; SIGTERM traité comme Ctrl+C. Procédure : Ctrl+C puis toujours `stop_robot.sh`.
- **Justification** : le gestionnaire de signal de rclpy ferme le contexte avant le bloc d'arrêt, donc la publication de la vitesse nulle était sautée. Le même mécanisme avait déjà causé un bug dans l'executor.
- **Résultat-leçon** : vérifié avec Gazebo : vitesse nulle 70 ms après Ctrl+C, robot arrêté en moins de 1 s ; idem avec SIGTERM. En cours suite à la revue de code : second Ctrl+C ignoré pendant l'arrêt ; arrêt si `/scan` (ou `/odom`) n'arrive plus depuis 0.5 s ; arrêt propre du tracker. Leçon : la sécurité d'un robot réel se teste, elle ne se suppose pas.

### 2026-10-08 · Limites connues pour le robot réel

- **Contexte** : limites identifiées pendant la préparation de la séance, à présenter au jury et à respecter pendant les essais.
- **Options envisagées** : non applicable (constat).
- **Choix** : limites documentées ; procédure `stop_robot.sh` systématique après Ctrl+C.
- **Justification** : ces limites viennent de l'architecture (lien réseau, capteur, odométrie) et ne se corrigent pas par le code seul.
- **Résultat-leçon** :
  - si le lien PC–robot tombe, rien côté PC ne peut arrêter le robot ;
  - les obstacles sous la portée minimale du LiDAR sont invisibles ;
  - la barrière virtuelle (odom) glisse avec la dérive d'odométrie ;
  - avec la stratégie B, une dernière consigne de Nav2 peut rester appliquée après Ctrl+C, d'où l'arrêt systématique par `stop_robot.sh`.

### 2026-10-09 · Séance robot réel : configuration constatée

- **Contexte** : première séance avec le TurtleBot3 Burger réel. Configuration relevée pendant la séance.
- **Options envisagées** : non consignées.
- **Choix** : aucun choix technique ; configuration consignée pour les essais suivants.
  - Robot n°1, joint en point d'accès Wi-Fi à l'adresse 10.42.0.1, utilisateur SSH `turtle`, clé SSH du PC installée sur le robot.
  - `ROS_DOMAIN_ID=1`, ROS 2 Humble, LiDAR LDS-02.
  - PC sous WSL en réseau `mirrored`, pare-feu Hyper-V ouvert en entrée.
  - Carte `zone_reelle` de 11 h 11.
- **Justification** : ces valeurs diffèrent de la simulation (domaine 30, pas de SSH). Les noter évite de reproduire les incidents 1 et 2.
- **Résultat-leçon** : le robot n'a pas d'Internet et pas d'horloge sauvegardée. Il repart au 2 octobre à chaque extinction (voir incident 3).

### 2026-10-09 · Incident 1 : variables de la simulation dans un onglet

- **Contexte** : un onglet de terminal avait gardé `ROS_DOMAIN_ID` et `ROS_LOCALHOST_ONLY` de la simulation. La téléopération n'avait aucun effet sur le robot.
- **Options envisagées** : non consignées.
- **Choix** : non consigné (la séance ne détaille pas de correction).
- **Justification** : le domaine et le mode localhost de la simulation ne correspondent pas à ceux du robot (domaine 1). Les nœuds d'un onglet ne voient donc pas le robot.
- **Résultat-leçon** : vérifier `ROS_DOMAIN_ID` et `ROS_LOCALHOST_ONLY` dans chaque onglet avant un essai réel.

### 2026-10-09 · Incident 2 : deux bringups simultanés sur le robot

- **Contexte** : deux bringups ont été lancés en même temps sur le robot. Seul `/scan` était visible, sans `/cmd_vel`.
- **Options envisagées** : non consignées.
- **Choix** : non consigné (la séance ne détaille pas de correction).
- **Justification** : deux bringups concurrents se gênent sur le même robot, et la commande ne passe plus.
- **Résultat-leçon** : un seul bringup actif à la fois. Vérifier les topics attendus (`/cmd_vel`, `/odom`, `/scan`) avant chaque essai.

### 2026-10-09 · Incident 3 : horloge du robot au 2 octobre

- **Contexte** : sans Internet et sans horloge sauvegardée, le robot était à la date du 2 octobre, soit un écart de 7 jours exactement. Les TF étaient rejetées et la mesure figée (run RANDOM_2_20261009-113503, bloqué à 37,5 %).
- **Options envisagées** : non consignées.
- **Choix** : remise à l'heure depuis le PC. Le script `robot_check.sh` mesure l'écart et remet l'heure à jour si l'écart dépasse 300 ms.
- **Justification** : sans Internet, aucune synchronisation automatique. Une horloge décalée rend les transformations inutilisables.
- **Résultat-leçon** : mesurer l'écart d'horloge avant chaque run, car le robot repart au 2 octobre à chaque extinction.

### 2026-10-09 · Incident 4 : première zone trop étroite

- **Contexte** : la première carte ne couvrait que 0,95 m² (cartons trop serrés). Le run d'essai RANDOM_1_20261009-102808 a donné 79,4 % en 300 s, avec 255 near_collisions.
- **Options envisagées** : non consignées.
- **Choix** : run conservé comme essai, à exclure des résultats. Nouvelle carte `zone_reelle` de 634 cellules, soit environ 1,6 m².
- **Justification** : avec des cartons trop serrés, le LiDAR détecte un obstacle à moins de 0,20 m en permanence, d'où le nombre élevé de near_collisions.
- **Résultat-leçon** : une zone trop petite fausse les métriques. Contrôler le nombre de cellules atteignables avant chaque série de runs.

### 2026-10-09 · Incident 5 : dernière consigne conservée après Ctrl+C

- **Contexte** : le `random_walker` ne s'arrêtait pas en fin de run. Après Ctrl+C, le TurtleBot3 garde le dernier `/cmd_vel` reçu, et le robot a percuté un mur.
- **Options envisagées** : non consignées.
- **Choix** : paramètre `run_duration` dans le walker. Après la durée, un Twist nul est republié à chaque tick. Le script `stop_robot.sh` publie le Twist nul sur le robot via SSH, puis depuis le PC, avec ses propres exports.
- **Justification** : le robot réel garde la dernière consigne, comme la simulation (voir l'entrée du 2026-10-08 sur la sécurité).
- **Résultat-leçon** : test isolé du walker (domaine 77) : 0,1 m/s pendant le run, 0 après `run_duration`. Confirmé sur le robot par le message « fin du run : robot à l'arrêt ». Corrigé.

### 2026-10-09 · Incident 6 : batterie trop basse, moteurs coupés

- **Contexte** : à 11,03 V (29 %), les moteurs ont été coupés alors que le LiDAR restait actif. Le robot semblait tourner sans bouger (run seed 2, vers 11 h 19).
- **Options envisagées** : non consignées.
- **Choix** : non consigné (la séance ne détaille pas de correction).
- **Justification** : le LiDAR publie `/scan` normalement, donc le capteur ne signale pas la panne des moteurs.
- **Résultat-leçon** : contrôler la batterie avant chaque séance (plus de 11,3 V, seuil noté pour la prochaine séance). Un run où le robot ne bouge pas est invalide, même si `/scan` circule.

### 2026-10-09 · Incident 7 : `/tf_static` perdu sur le Wi-Fi

- **Contexte** : `/tf_static` n'arrivait pas au PC de façon fiable sur le Wi-Fi. AMCL affichait « queue is full », sa position était figée et la trace rose de RViz s'était arrêtée.
- **Options envisagées** : non consignées.
- **Choix** : publication du `/tf_static` sur le PC, avec `robot_state_publisher` du burger (script `pc_robot_description.sh`, URDF avec `${namespace}` retiré). Corrigé.
- **Justification** : un message statique publié une seule fois et perdu sur le Wi-Fi n'est pas republié. Le PC fournit le modèle du robot sans dépendre du lien.
- **Résultat-leçon** : sur un lien instable, ne pas compter sur un topic statique publié une seule fois par le robot. Vérifier l'arbre TF avant un essai de navigation.

### 2026-10-09 · Incident 8 : heure du PC prise trop tôt

- **Contexte** : lors de la remise à l'heure, l'heure du PC était lue avant la saisie du mot de passe sudo. Le robot était donc en retard de plusieurs secondes, et le script redemandait le mot de passe à chaque fois.
- **Options envisagées** : non consignées.
- **Choix** : corrigé. Le correctif n'est pas détaillé dans les notes de séance ; le défaut venait de la lecture de l'heure avant la saisie.
- **Justification** : l'heure envoyée doit correspondre au moment de l'envoi, pas au début du script.
- **Résultat-leçon** : prendre l'heure au moment de l'envoi de la commande, pas avant une étape interactive.

### 2026-10-09 · Incident 9 : couche « Coverage map » figée dans RViz

- **Contexte** : dans RViz, la couche « Coverage map » ne se rafraîchit pas toujours, alors que `/coverage_status` et le CSV continuent de progresser.
- **Options envisagées** : piste à vérifier, la durabilité Volatile dans `aspi.rviz`.
- **Choix** : non résolu.
- **Justification** : le CSV et `/coverage_status` sont écrits par le tracker, indépendamment de l'affichage.
- **Résultat-leçon** : ne pas se fier à l'affichage RViz pour juger d'un run. Les mesures font foi (CSV, `/coverage_status`).

### 2026-10-09 · Incident 10 : run B bloqué, non résolu

- **Contexte** : run B (Nav2) sur le robot réel, non résolu.
  - Tentative 1 (12 h 26) : Nav2 est actif, mais le log affiche `tf_help: Transform data too old`. Les TF du robot sont environ 2,4 s en retard sur l'horloge du PC. RPP et le Behavior Tree déclarent chaque but atteint sans mouvement : 14 waypoints « réussis » en 12 s, robot immobile.
  - Tentative 2 : tolérances à 1,0 s (`transform_tolerance` pour RPP et les costmaps locale et globale, `transform_timeout` pour le behavior_server). `bt_navigator` reste inactif, car l'activation ne se termine pas. AMCL et la costmap locale signalent « timestamp earlier than all the data in the transform cache ».
- **Options envisagées** : pistes listées dans la séance, non tranchées.
  - Écart d'horloge réel (lire la sortie « écart … ms » de `robot_check.sh`).
  - Latence Wi-Fi des TF.
  - Charge CPU de WSL.
  - Synchronisation propre avec chrony, le PC servant de serveur.
  - Lancer Nav2 sur le Pi du robot.
- **Choix** : non résolu. Aucun run B réel n'est mesurable en l'état.
- **Justification** : les deux tentatives montrent que le statut de Nav2 ne prouve pas le mouvement du robot. Le blocage est lié à la synchronisation des horloges et à la latence des TF.
- **Résultat-leçon** : vérifier le mouvement réel, ne pas se fier au statut de Nav2. Le cœur de la comparaison A/B réelle reste à faire.

### 2026-10-09 · Constat d'analyse : run RANDOM_2 arrêté à 146,5 s

- **Contexte** : le run RANDOM_2_20261009-121427 était présenté comme valide et complet (72,1 % en 300 s). La relecture des CSV par le chef de projet montre que la distance reste figée à 11,94 m de 146,5 s à 300,5 s, et la couverture à 72,1 %. Pendant ce temps, near_collisions continue de croître (50 → 95) : le LiDAR fonctionne toujours.
- **Options envisagées** : causes possibles, non tranchées faute de rosbag. Arrêt physique (moteurs ou batterie, comme l'incident 6) ou pose figée (TF), comme le run B3 de la simulation.
- **Choix** : le run n'est valide que jusqu'à 146,5 s. Il ne doit pas être présenté comme complet.
- **Justification** : la distance et la couverture sont figées, alors que le LiDAR continue d'envoyer des données. Cela exclut un simple arrêt du capteur, mais pas la cause du blocage.
- **Résultat-leçon** : vérifier la distance parcourue en fonction du temps avant de déclarer un run complet. Enregistrer un rosbag à chaque run réel pour trancher la cause.

### 2026-10-09 · Constat : free_thresh de la carte zone_reelle

- **Contexte** : la carte `zone_reelle.yaml` a été sauvegardée avec `free_thresh` à 0,25. C'est le même piège que le premier run A du 2026-10-08 : les pixels inconnus sont relus comme libres.
- **Options envisagées** : non consignées.
- **Choix** : les runs de la séance sont mesurés avec 634 cellules atteignables. Le calcul donne 634 cellules avec 0,25 contre 620 avec 0,19, soit un écart de 2 %.
- **Justification** : la zone est fermée par les cartons, donc l'écart reste faible. Il faut tout de même le noter pour l'interprétation des résultats.
- **Résultat-leçon** : vérifier `free_thresh` à chaque sauvegarde de carte, comme le contrôle de cohérence du premier jour.

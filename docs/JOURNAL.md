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
- **Résultat-leçon** : cause localisée du blocage : une ligne de balayage coupée par un pilier (waypoints (3.52, -0.67) puis (2.77, -0.67) ; pilier en x 2.96–3.27, y -0.72 à -0.42). Le robot finit le premier segment face au pilier à 0.25 m. DWB oscille (vx ≈ 0, wz ±0.03 à 0.18 rad/s) sans contourner. La surcharge CPU était un vrai défaut, mais pas la cause du blocage. Mesurer chaque correction séparément évite de conclure trop vite.

### 2026-10-08 · Stratégie B : contrôleur Regulated Pure Pursuit (T3)

- **Contexte** : le contrôleur DWB reste bloqué au pilier (entrée précédente). Essai d'un autre contrôleur de Nav2, Regulated Pure Pursuit (RPP).
- **Options envisagées** :
  - changer de contrôleur ;
  - calculer les contournements dans notre planner (T4) ;
  - décomposition cellulaire de Choset (trop long pour 3 jours).
- **Choix** : changer de contrôleur (T3). Réglages alignés sur la stratégie A pour une comparaison équitable : vitesse de 0.15 m/s (celle de `random_walker` ; DWB autorisait 0.22 m/s), rotation sur place à 1.0 rad/s (celle de `random_walker`), pas de ralentissement près des obstacles.
- **Justification** : le blocage venait du comportement de DWB face au pilier, pas du réglage de l'inflation. RPP n'a pas été comparé à d'autres contrôleurs.
- **Résultat-leçon** : à 300 s, T3 atteint 28.5 % de couverture (T2 : 21.9 %), 30.5 m parcourus, 1 near_collision (T2 : 5), 0 « Failed to make progress » (T2 : 13), 0 recovery. Dernier waypoint atteint : 37/112 (T2 : 19). Le passage du pilier prend environ 13 s : rotation sur place puis contournement par le sud. Limites restantes : la vitesse (0.15 m/s) et les rotations sur place (environ 48 s sur 300 s).

### 2026-10-08 · Stratégie B : contournements calculés par le planner (T4, impasse)

- **Contexte** : après T3, les lignes de balayage restent coupées par les obstacles. Essai de contournements calculés par notre planner.
- **Options envisagées** : garder T3 seul ; ajouter des points de contournement calculés par le planner (T4).
- **Choix** : T3 retenu. `plan_transitions` est conservé, testé, et désactivé par défaut (argument de launch).
- **Justification** : principe de `plan_transitions` : fonction pure, Dijkstra sur le 8-voisinage du masque atteignable, simplification par visibilité, tronçons ≤ 0.3 m. Résultat : 112 → 245 waypoints, 49 transitions corrigées, 0 point hors masque, 8 tests unitaires (39 tests au total). Bug trouvé pendant le développement : des tronçons à 45° passaient exactement sur un coin de cellule, et l'arrondi les rangeait hors masque. Correction par un test exact de segment. Résultat T4 (T3 plus contournements) à 300 s : 22.3 % contre 28.5 % pour T3 ; 25 à 26 waypoints d'origine atteints contre 36 ; 43 « collision ahead » (RPP), 8 « patience exceeded », 3 recoveries. Les points intermédiaires consomment 38 % du temps, car chaque but déclenche une replanification et une rotation.
- **Résultat-leçon** : avec RPP, Nav2 contourne déjà les obstacles. Notre marge (0.155 m) est aussi plus faible que ce que la costmap Nav2 accepte, d'où les conflits. Une amélioration algorithmique « évidente » doit être mesurée : elle peut être contre-productive selon le reste de la chaîne.

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

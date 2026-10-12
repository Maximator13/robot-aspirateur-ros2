# Plan de soutenance

10 minutes de présentation, 10 minutes de questions.
Fil : problème, options, solution retenue, évaluation chiffrée (simulation, robot réel, jumeau numérique), leçons, perspectives.

Règles tenues dans ce plan :

- aucun extrait de code sur les slides : des algorigrammes à la place ;
- schéma système obligatoire (nœuds, topics avec types, launch, Nav2) ;
- outils du cours à montrer explicitement : Nav2, AMCL, Cartographer, map_server, RViz, rosbag (voir section 1.1) ;
- pas de vidéo de démonstration (décision de l'étudiant) : captures, figures, tableaux. Une photo ou une vidéo du robot réel peut être ajoutée par l'étudiant (slide 9) ;
- tous les chiffres viennent de `docs/RESULTATS.md`, `docs/JOURNAL.md`, `docs/ARCHITECTURE.md`,
  `docs/ETAT_DE_L_ART.md` et `docs/PERSPECTIVES.md`. Quand le journal et RESULTATS divergent légèrement, on retient RESULTATS (section 5).

---

## 1. Plan des slides (13 slides, 9 min 30 + 30 s de marge)

| N° | Titre | Durée | Visuel principal (fichier) |
|---|---|---|---|
| 1 | Problème et objectif | 0:20 | aucun |
| 2 | État de l'art | 0:45 | tableau de `docs/ETAT_DE_L_ART.md` §3 |
| 3 | Deux stratégies et leurs algorigrammes | 0:50 | `docs/ALGORIGRAMMES.md` §1.2 et §2.2 |
| 4 | Schéma système | 0:50 | `docs/ARCHITECTURE.md` §2.1 (B simulée), §7.1 (B réelle) |
| 5 | Une mesure équitable | 0:30 | tableau de protocole (`docs/RESULTATS.md` §1) |
| 6 | Simulation : A contre B | 0:55 | `results/coverage_vs_time_runs.png` + tableau §2 |
| 7 | Démarche : régler B de T0 à T5 | 0:40 | tableau §5 de RESULTATS |
| 8 | Bugs et impasses en simulation | 0:45 | tableau à 3 colonnes (section 2) |
| 9 | Robot réel : A contre B | 1:00 | `results/robot_reel/coverage_vs_time_reel_12oct.png` |
| 10 | Impasse Nav2 sur le robot réel | 0:50 | schéma de la chaîne de diagnostic (à tracer) |
| 11 | Jumeau numérique | 0:55 | `results/figures/jumeau_vs_reel.png` + 2 captures |
| 12 | Limites assumées | 0:30 | liste de puces |
| 13 | Perspectives et conclusion | 0:40 | tableau gain / effort de `docs/PERSPECTIVES.md` |

Total : 570 s, soit 9 min 30. Les 30 s restantes servent aux transitions.
Si on dépasse : fusionner 7 dans 8 (gain 0:30) ou passer la slide 5 en une phrase orale.

### 1.1 Où apparaissent les outils du cours

| Outil | Slide | Rôle à dire |
|---|---|---|
| Cartographer | 5, 11 | a produit la carte de référence de `turtlebot3_world` (JOURNAL 2026-10-08) ; la carte de la zone réelle sert aussi au jumeau |
| map_server | 4, 5 | publie `/map` (`nav_msgs/OccupancyGrid`) à tous les nœuds ; la carte sert de vérité terrain pour A |
| AMCL | 4, 10, 12 | localisation de B en simulation (TF `map` vers `odom`) ; écarté sur le robot réel |
| Nav2 | 3, 4, 7, 10 | exécute B en simulation (`FollowWaypoints`) ; n'a pas fait avancer le robot réel |
| RViz | 11 | carte de couverture `/coverage_map`, trajet `/coverage_path`, scan LiDAR |
| rosbag | 8, 12 | a permis de prouver que la TF d'AMCL était publiée à 5 Hz pendant le gel de B3 ; **pas de rosbag sur les runs réels** (limite) |

---

### Slide 1. Problème et objectif (0:20)

- **Message clé** : couvrir toute une pièce, c'est un problème connu (CCPP), et nous le mesurons.
- **Contenu**
  - TurtleBot3 Burger. Simulation Gazebo (`turtlebot3_world`, 13,9 m² atteignables), puis robot réel (zone en carton, environ 1,6 m²).
  - Question : une stratégie planifiée avec carte bat-elle une stratégie aléatoire sans carte ?
  - Seuil visé en simulation : 80 % de surface couverte en 10 min.
  - Évalué : la démarche, pas un résultat parfait.
- **Visuel** : aucun fichier.

### Slide 2. État de l'art (0:45)

- **Message clé** : cinq familles d'approches ; deux seulement sont réalisables en 3 jours.
- **Contenu** (une ligne par approche : principe, limite, décision)
  - Aléatoire type Roomba [3] : sans carte, sans garantie. **Retenu** (stratégie A).
  - Spirale [1] : bonne en zone dégagée, insuffisante avec obstacles. Non retenue.
  - Boustrophédon et décomposition cellulaire de Choset [2][4] : lignes parallèles, carte exigée.
    **Retenu sous forme simplifiée** (stratégie B).
  - Spanning Tree Coverage, Gabriely & Rimon [5][6] : grille de cellules à la taille du robot. Non retenu.
  - Coverage server de Nav2, opennav_coverage [7] : conçu pour des champs agricoles. Non retenu.
  - Référence de synthèse : Galceran & Carreras [1].
- **Visuel** : tableau comparatif de `docs/ETAT_DE_L_ART.md`, section 3. Références [1] à [7] en bas de slide.

### Slide 3. Deux stratégies et leurs algorigrammes (0:50)

- **Message clé** : A est la borne basse simple ; B est un balayage planifié sur la carte. Deux algorithmes simples, testables sans ROS.
- **Contenu**
  - A : avancer ; devant un obstacle (secteur avant ±30°, seuil 0,25 m), tourner de 90 à 180° ; graine fixée.
  - B : carte, érosion de l'espace libre, composante connexe du départ, lignes alternées tous les 0,18 m, extrémités de segments en waypoints.
  - Sur la carte du protocole : 5564 cellules atteignables, 112 waypoints. 107 tests unitaires (pytest, sans ROS).
  - Limite assumée : B n'est pas une décomposition de Choset ; Nav2 contourne les obstacles.
- **Visuel** : deux algorigrammes côte à côte, simplifiés (moins de texte dans les nœuds).
  - Gauche : `docs/ALGORIGRAMMES.md` §1.2 (machine à états du `random_walker`).
  - Droite : `docs/ALGORIGRAMMES.md` §2.2 (balayage boustrophédon).

### Slide 4. Schéma système (0:50)

- **Message clé** : trois nœuds à nous, un tracker commun ; l'exécutant de B change entre simulation (Nav2) et robot réel (suiveur).
- **Contenu**
  - Nos nœuds : planner, exécutant (`coverage_executor` en simulation, `coverage_follower` sur le robot réel), tracker commun, plus `random_walker` pour A.
  - Topics et types : `/map` (`nav_msgs/OccupancyGrid`), `/coverage_path` (`nav_msgs/Path`), `/scan` (`sensor_msgs/LaserScan`),
    `/cmd_vel` (`geometry_msgs/Twist`), `/coverage_status` (`aspi_interfaces/CoverageStatus`).
  - Action Nav2 : `FollowWaypoints` (`nav2_msgs/action/FollowWaypoints`), simulation seulement.
  - TF : `map` vers `odom` par AMCL (simulation, B) ou fixe (A, robot réel) ; `odom` vers `base_footprint`.
  - Launch : `aspi_planned.launch.py` (simulation B), `aspi_real_follow.launch.py` (robot réel B).
- **Visuel** : `docs/ARCHITECTURE.md` §2.1 en grand (B simulée). Le schéma du robot réel (§7.1) en petit ou sur la slide 9.
  Détail interne de Nav2 (§2.2) et schéma de A (§1.1) en annexe, pour les questions. Prévoir des versions allégées.

### Slide 5. Une mesure équitable (0:30)

- **Message clé** : A et B sont mesurées par le même nœud, avec le même dénominateur.
- **Contenu**
  - Même `coverage_tracker`, même masque atteignable (5564 cellules en simulation), même fonction partagée.
  - Rayon de nettoyage 0,09 m demandé, 0,10 m appliqué (2 cellules). Espacement des lignes 0,18 m demandé, 0,20 m appliqué.
  - 600 s simulées, départ (-2.0, -0.5), 3 runs par stratégie (seeds 1, 2, 3), vitesse 0,15 m/s.
  - Carte de référence faite avec Cartographer, servie par map_server.
  - A en mode accéléré (validé par 5 critères), B en temps réel (accéléré invalidé).
- **Visuel** : tableau de protocole bâti depuis `docs/RESULTATS.md`, section 1.

### Slide 6. Simulation : A contre B (0:55)

- **Message clé** : 80 % n'est atteint par personne ; B est plus sûre quand elle fonctionne, mais moins fiable.
- **Contenu**
  - A : 51,0 ± 6,7 %. B : 44,1 ± 23,4 % (3 runs, officiel). Meilleur run : B1 avec 59,8 %.
  - B1 et B2 : 59,8 % et 55,4 %. B3 : 17,2 % (blocage, slide 8). B1 et B2 devancent la moyenne de A dès environ 4 min.
  - near_collisions : A 25,7 en moyenne ; B 0 et 2 sur les runs normaux, 25 sur B3.
  - Distance : A environ 70 m ; B 70,2 et 62,2 m, 29,5 m pour B3.
  - Aucune conclusion statistique ferme avec n = 3.
- **Visuel** : `results/coverage_vs_time_runs.png` (deux sous-graphes, seeds étiquetées, B3 visible), avec un tableau réduit de `docs/RESULTATS.md` §2
  (stratégie, seed, % final, distance, near_collisions). `results/coverage_vs_time.png` en secours.

### Slide 7. Démarche : régler B de T0 à T5 (0:40)

- **Message clé** : un facteur à la fois, une mesure à chaque fois ; l'impasse T4 est documentée.
- **Contenu** (`docs/RESULTATS.md` §5)
  - T0, config d'origine : 19,5 % à 300 s, 33,2 % à 600 s ; boucle du suiveur à 2000 Hz, CPU saturé.
  - T1, boucle à 20 Hz : 18,2 %. T2, inflation réduite : 21,9 %, blocage devant le pilier.
  - T3, contrôleur Regulated Pure Pursuit : 28,5 % à 300 s, 54,1 % à 600 s.
  - T4, contournements calculés : 22,4 %. **Impasse**, code conservé et désactivé.
  - T5, ralentissement d'approche réduit : 30,6 % à 300 s, 59,7 % à 600 s. **Retenu.**
  - Réserve : T3 et T5 avec une seule seed chacune.
- **Visuel** : tableau T0 à T5 de `docs/RESULTATS.md` §5, ou frise horizontale faite à la main.

### Slide 8. Bugs et impasses en simulation (0:45)

- **Message clé** : chaque bug a produit une règle de travail.
- **Contenu** (détail en section 2)
  1. Repère `map` vers `odom` : l'hypothèse « identité » était fausse ; deux bugs se masquaient.
  2. Mode accéléré : bon pour A, invalidé pour B ; un critère isolé était trompeur.
  3. Executor : fuite mémoire (4,8 Go) et attente sans délai. Toute attente doit avoir une sortie.
  4. B3 : TF figée dans Nav2, alors qu'AMCL la publiait à 5 Hz (prouvé par rosbag). Cause non identifiée, run conservé dans la moyenne.
- **Visuel** : tableau à trois colonnes (bug, cause, leçon), sans fichier.

### Slide 9. Robot réel : A contre B (1:00)

- **Message clé** : sur la zone réelle, B termine la zone en 2,5 min avec deux fois moins de distance que A.
- **Contenu**
  - TurtleBot3 Burger réel, LiDAR LDS-02. Zone en carton : 620 cellules atteignables, environ 1,6 m². Même zone et même croix de départ pour A et B.
  - Vitesse 0,10 m/s. Localisation en mode `static` : TF `map` vers `odom` fixe, odométrie seule, pas d'AMCL.
  - **B réel n'est pas exécuté par Nav2** mais par le suiveur `coverage_follower` : tourner vers le waypoint, puis avancer. **La planification (boustrophédon) est la même qu'en simulation.**
  - Tableau, séance du 12/10 (2 runs A, 2 runs B valides) :

    | | A (seeds 1 et 3) | B (n°1 et n°2) |
    |---|---|---|
    | % à 120 s | 36,2 et 30,3 | 79,3 et 75,2 |
    | % final | 73,1 et 74,8 (300 s) | 98,4 (301 s) et 96,5 (170 s, arrêt manuel) |
    | Temps pour 80 % | non atteint | 125 s et 134 s |
    | Distance | 19,7 et 20,9 m | 9,8 et 9,8 m |
    | near_collisions | 21 et 19 | 8 et 2 |

  - Un run B incident (10 h 45), exclu : waypoints sautés, couverture figée à 46,8 %. B réel n'est pas toujours fiable (1 run sur 3 lancés).
  - 2 + 2 runs : aucune variabilité chiffrable.
- **Visuel** : `results/robot_reel/coverage_vs_time_reel_12oct.png` (A en orange, B en bleu ; les parties pointillées après la fin du trajet de B sont des prolongements, pas des mesures : le dire).
  Tableau ci-dessus à droite ou en dessous.
  **Photo ou vidéo du robot réel dans la zone en carton : à fournir par l'étudiant** (emplacement : coin haut droit de la slide, ou en insert de 5 s). Si rien n'est disponible, laisser la courbe seule.

### Slide 10. Impasse Nav2 sur le robot réel (0:50)

- **Message clé** : Nav2 annonçait un succès alors que le robot ne bougeait pas ; un exécutant plus simple a débloqué la mesure.
- **Contenu** (JOURNAL 2026-10-12, « Impasse : Nav2 sur le robot réel »)
  - Diagnostic point par point, un facteur à la fois.
  - Horloge du robot : écart ramené de 462 ms à 30–60 ms.
  - Réseau : âge de `/scan` et `/odom` d'environ 0,26 s. Nav2 actif (7 nœuds sur 7).
  - AMCL : transformée `map` vers `odom` vieille de 27 s. Nav2 déclare le but atteint sans que le robot bouge : **faux succès**, détecté par la mesure du déplacement réel sur `/odom`.
  - Mode `static` (sans AMCL) : Nav2 fait pivoter le robot de 109° à 174° sans jamais avancer (« Failed to make progress »), même après réglage du progress checker puis du contrôleur. Cause non trouvée.
  - **Décision** : exécutant simplifié `coverage_follower`, même planification. 2 runs B complets obtenus.
  - **Leçons** : le statut d'un logiciel ne prouve pas le mouvement, il faut mesurer le déplacement réel ; simplifier l'exécutant a débloqué la situation ; la navigation à travers le Wi-Fi est un problème en soi.
- **Visuel** : petit algorigramme à tracer : « Nav2 actif ? oui → but atteint ? oui → robot a bougé (`/odom`) ? non → faux succès ». Aucun fichier existant ; à dessiner (Mermaid, 5 nœuds).
  Option : algorigramme du suiveur `docs/ALGORIGRAMMES.md` §5, en petit.

### Slide 11. Jumeau numérique (0:55)

- **Message clé** : le même monde que le robot réel, dans Gazebo, donne des distances quasi identiques ; l'écart sur A a une hypothèse.
- **Contenu**
  - Monde Gazebo `zone_reelle.world` généré à partir de la carte réelle : 96 boîtes couvrant les 486 cellules murs, zone fermée, départ en (0, 0). Mêmes launch et réglages que le robot réel (0,10 m/s, mode `static`, 300 s, 620 cellules).
  - **Un seul run par configuration** : A seed 1, B suiveur, B Nav2.
  - Distances quasi identiques : B 9,7 m (jumeau) contre 9,8 m (réel) ; A 19,3 m contre 19,7 et 20,9 m. B termine avec environ deux fois moins de distance que A dans les deux mondes.
  - A plus haut en simulation : 82,7 % contre 73,1 et 74,8 % (+7,9 à +9,6 points). Hypothèse non testée : odométrie parfaite en simulation, alors que A tourne beaucoup et dérive sur le robot réel. Le hasard de la seed n'est pas exclu.
  - B suiveur un peu plus bas en simulation : 93,1 % contre 98,4 et 96,5 %. Pas d'explication vérifiée.
  - **Nav2 bloque aussi dans le jumeau** : couverture figée à 67,7 % dès 107 s, recoveries en échec, robot arrêté contre le mur diagonal, dans la partie haute de la zone. Hypothèse (1 run) : la géométrie étroite de la zone joue, pas seulement le Wi-Fi ou l'horloge.
- **Visuel** (de gauche à droite)
  1. `results/figures/jumeau_vs_reel.png` : courbes réel (traits pleins) et jumeau (pointillés), B Nav2 en gris. Figure principale.
  2. `results/figures/jumeau_B_rviz_t090.png` : RViz, trajet en lacets (vert), couverture (rose), scan LiDAR (rouge). **Bien cadrée, à utiliser telle quelle** (recadrer la barre de fenêtre et les panneaux de gauche si la place manque).
  3. `results/figures/jumeau_A_gazebo_t030.png` : Gazebo, la zone en boîtes marron ; **mal cadrée** (voir section 6), à remplacer par `jumeau_A_gazebo_t150.png` ou `jumeau_A_gazebo_t300.png` après vérification, ou à recadrer.
  Option pour le blocage de Nav2 : `results/figures/jumeau_Bnav2_rviz_fin_trajet.png` (couverture rose arrêtée avant la fin du trajet vert, robot arrêté contre le mur diagonal, dans la partie haute de la zone, coin supérieur droit de la capture). Cadrage correct mais barre de fenêtre noire à gauche à retirer.
  `results/figures/jumeau_A_rviz_t300.png` en réserve pour la question sur A (zone petite dans le cadre).

### Slide 12. Limites assumées (0:30)

- **Message clé** : nous disons nous-mêmes ce que la mesure ne prouve pas.
- **Contenu**
  - **Localisation par odométrie seule sur le robot réel** : `map` vers `odom` figée, décalage visible entre murs de la carte et murs réels dans RViz, dérive à chaque rotation sur place (A tourne environ 20 fois). Les pourcentages sont approximatifs, surtout pour A. AMCL a été écarté (il figeait la TF avec Nav2). Un recalage LiDAR est une perspective.
  - **Marge aux bords** : B s'arrête à environ 20 cm des murs (érosion de 0,155 m arrondie à 4 cellules, soit 0,20 m). Même zone mesurée pour A et B : cette bande n'est nettoyée par aucun des deux.
  - **Peu de runs** : 3 + 3 en simulation, 2 + 2 sur le robot réel, 1 par configuration sur le jumeau.
  - **Une seule pièce** en simulation, une seule zone réelle. Vitesse réduite à 0,10 m/s en réel.
  - **B3 bloqué en simulation officielle** (cause non identifiée) ; Nav2 bloqué sur le robot réel et dans le jumeau.
  - B réel exécuté par un suiveur, B simulé par Nav2 : pas le même exécutant. Pas de rosbag sur les runs réels.
- **Visuel** : liste de puces. Sources : `docs/RESULTATS.md` §6, §7.6 et §7.7.

### Slide 13. Perspectives et conclusion (0:40)

- **Message clé** : des incréments petits, chacun avec une mesure de succès.
- **Contenu**
  - Rang 1, P1 : plus de runs (5 par stratégie en simulation, plus de runs sur le robot réel), 0,5 jour.
  - Rang 2, P10 : recalage LiDAR sur le robot réel (AMCL ou scan matching, une fois l'horloge corrigée), 1 jour.
  - Rang 3, P2 : réduire les rotations sur place (environ 18 % du temps de B en simulation), 0,5 à 1 jour.
  - Rang 5, P4 : diagnostiquer le gel de la TF `map` vers `odom` (B3) avec rosbag, 1 jour.
  - Rang 6, P11 : passe finale de suivi de mur pour les 20 cm de bord, 1 jour.
  - En réserve : opennav_coverage comme référence (P5, disponibilité pour Humble à vérifier).
  - Efforts : estimations de `docs/PERSPECTIVES.md`, pas des mesures. P9 (essai sur robot réel) est réalisé.
  - Conclusion : mesure comparable ; en simulation 80 % non atteint et B moins fiable ; sur le robot réel B atteint 80 % en 125 à 134 s contre A qui ne l'atteint pas en 300 s ; démarche et impasses documentées.
- **Visuel** : tableau « classement gain / effort » de `docs/PERSPECTIVES.md` (rangs 1 à 6 : P1, P10, P2, P3, P4, P11 ; P3 n'est pas repris sur la slide). Le tableau reprend bien le recalage LiDAR (P10) et le suivi de mur (P11).

---

## 2. Détail des slides 7, 8 et 10 (fil de la parole)

### Slide 7. Chaîne de réglages T0 à T5

Ordre de lecture à l'oral : problème mesuré, correction, effet.

1. T0 : 19,5 % à 300 s. Cause trouvée en lisant le log : 37 000 lignes « Processing waypoint ».
2. T1 : on corrige la fréquence de boucle. La surcharge disparaît, le comportement ne change pas.
   Leçon : un vrai défaut peut ne pas être la cause du problème observé.
3. T2 : on réduit l'inflation. Le début est plus rapide, mais le robot reste bloqué devant un pilier dès 177 s.
4. T3 : on change de contrôleur. 28,5 % à 300 s contre 21,9 %, 0 « Failed to make progress » contre 13.
5. T4 : on ajoute des contournements calculés. 245 waypoints au lieu de 112, 22,4 % contre 28,5 %.
   Les points intermédiaires consomment 38 % du temps.
6. T5 : on retire un ralentissement et une pause. 59,7 % à 600 s contre 54,1 %. Une seule seed chacun.

Phrase de conclusion : les paramètres de sécurité de Nav2 sont pensés pour aller d'un point à un autre, pas pour longer les obstacles.

### Slide 8. Les quatre bugs et impasses de la simulation

| Bug ou impasse | Ce qui s'est passé | Leçon |
|---|---|---|
| Repère `map` vers `odom` et inconnu relu libre | Le premier run de A ne comptait que 754 cellules au lieu de 5564. Le plugin Gazebo publie `odom` dans le repère du monde (-2.0, -0.5 au spawn). Le TF identité prévu décalait la trajectoire de 2 m. Un second bug masquait le premier : les pixels inconnus de la carte étaient relus comme libres. | Vérifier une hypothèse par une mesure (lecture de `/odom`). Un contrôle de cohérence détecte l'erreur silencieuse. Deux bugs peuvent se masquer. |
| Mode accéléré invalidé pour B | Cinq critères fixés avant les runs. Contrôleur 4,42 Hz contre 9,56 Hz, 8 waypoints contre 69, 85 incidents contre 1. Le % final seul paraissait bon (56,8 % contre 54,1 %), mais à 300 s : 53,6 % contre 29,0 %. | Valider un changement de banc par plusieurs critères chiffrés fixés à l'avance, dont des critères de comportement. |
| Executor de B : fuite mémoire et attente infinie | Un executor orphelin occupait 4,8 Go (80 % de la RAM). Une boucle d'attente ne testait pas l'état du contexte ROS. Au démarrage, une attente sans délai s'est bloquée 2 fois sur 5 lancements. | Toute attente doit tester l'état de ROS et avoir une sortie ou un délai. |
| Run B3 : TF figée dans Nav2 | À environ 135 s, la TF `map` vers `odom` vue par Nav2 reste figée, alors qu'AMCL la publie à 5 Hz (rosbag). 4 329 messages « Transform data too old ». Couverture bloquée à 17,2 %. Cause non identifiée. | Ne pas écarter un résultat après l'avoir vu. La fiabilité fait partie de la performance. |

Ordre conseillé à l'oral : 1, 2, 3, 4. Si le temps manque, garder 1, 2 et 4 (le 3 passe en question).
Autres bugs en réserve (JOURNAL) : seuil `near_collisions` (`range_min` du LiDAR 0,12 m supérieur au rayon du robot 0,105 m),
course au démarrage de Nav2, SIGINT ignoré par les processus lancés en arrière-plan.
Bugs du robot réel en réserve : horloge du robot repartie d'une date ancienne (TF rejetées, deux runs figés),
`/tf_static` perdu sur le Wi-Fi, première zone trop étroite (0,95 m²), `free_thresh` de la carte réelle (même piège que le premier bug).

### Slide 10. Fil de la parole (impasse Nav2 réelle)

1. « Nav2 est actif, 7 nœuds sur 7, mais le robot ne bouge pas. »
2. Premier suspect : l'horloge. 462 ms d'écart, ramenés à 30–60 ms. Pas suffisant.
3. Deuxième suspect : le réseau. 0,26 s d'âge des messages. Nav2 reste actif.
4. Avec AMCL : la transformée `map` vers `odom` a 27 s. Nav2 dit « but atteint » sans mouvement. C'est la mesure de `/odom` qui révèle le faux succès.
5. Sans AMCL (mode `static`) : le robot pivote de 109° à 174° et n'avance jamais. Cause non trouvée.
6. Décision : un suiveur simple, « tourner puis avancer », dont chaque action est vérifiable. La planification ne change pas.
7. Honnêteté : la comparaison réelle n'oppose pas les mêmes exécutants que la simulation.

---

## 3. Préparation aux questions du jury

Réponses courtes et honnêtes. Chaque réponse est appuyée sur un chiffre ou une source du dossier.

### 3.1 Nouvelles questions (robot réel et jumeau)

**Q-N1. Pourquoi pas Nav2 sur le robot ?**
Nous avons essayé. Avec AMCL, la TF `map` vers `odom` avait 27 s de retard et Nav2 déclarait le but atteint sans mouvement
(faux succès, détecté sur `/odom`). Sans AMCL (mode `static`), le robot pivotait de 109° à 174° sans jamais avancer, même après
réglage du progress checker puis du contrôleur. Nous avons corrigé l'horloge (462 ms vers 30–60 ms) sans résoudre. Cause non trouvée.
Nous avons donc gardé la même planification et remplacé l'exécutant par un suiveur simple. Nous le disons sur la slide 9 : B réel n'est pas Nav2.
Le blocage de Nav2 dans le jumeau (1 run) suggère que la zone étroite joue aussi. C'est une hypothèse.

**Q-N2. Vos résultats réels contredisent-ils la simulation (B3, 44 % contre 51 %) ?**
Non, et ils ne la confirment pas non plus : ce n'est pas le même banc. En simulation, B (44,1 ± 23,4 %) est sous A (51,0 ± 6,7 %)
à cause de B3, bloqué à 17,2 % ; B1 et B2 (59,8 % et 55,4 %) sont au-dessus de la moyenne de A. Sur le robot réel, B a une zone de 1,6 m²
au lieu de 13,9 m², un autre exécutant (suiveur au lieu de Nav2), une autre vitesse (0,10 m/s au lieu de 0,15 m/s) et une autre
localisation (odométrie seule). Le point commun : sans blocage, B fait moins de near_collisions que A (0 et 2 contre 25,7 en moyenne en simulation ; 8 et 2 contre 21 et 19 en réel).
Sur le robot réel, B finit la zone avec deux fois moins de distance que A ; en simulation, la distance est comparable (B1 70,2 m contre 70,0 à 71,9 m pour A).
Fiabilité : 1 run B sur 3 bloqué en simulation officielle (B3), et 1 incident sur 3 runs lancés sur le robot réel, même proportion mais cause différente (waypoints contre un carton, pas Nav2).
Pas de comparaison de pourcentages entre les deux.

**Q-N3. Le jumeau numérique prouve-t-il quelque chose avec 1 run ?**
Non, il ne prouve rien statistiquement. Il sert à comparer des ordres de grandeur sur la même géométrie.
Ce qui est solide : les distances quasi identiques (B 9,7 m contre 9,8 m ; A 19,3 m contre 19,7 et 20,9 m), parce qu'elles
dépendent surtout du trajet. Ce qui ne l'est pas : l'écart de A (82,7 % contre 73,1 et 74,8 %), qui peut venir de l'odométrie
parfaite en simulation (hypothèse non testée) ou du hasard de la seed. Le blocage de Nav2 dans le jumeau est un seul run :
c'est une hypothèse, pas un diagnostic.

**Q-N4. Pourquoi le mode static et pas AMCL sur le robot ?**
AMCL figeait la TF `map` vers `odom` avec Nav2 : transformée vieille de 27 s. Avec le suiveur, AMCL n'était plus indispensable.
Conséquence assumée : le robot suppose qu'il part exactement sur la croix, dans l'orientation de la carte. Une erreur de cap de 3°
donne environ 5 cm d'écart à 1 m (calcul géométrique, non mesuré). La dérive d'odométrie s'accumule à chaque rotation, surtout pour A.
Les pourcentages réels sont donc approximatifs. AMCL ou un recalage LiDAR est la première perspective.
Les runs du 9/10 avec AMCL (A seul, données d'illustration) ne sont pas mélangés avec ceux du 12/10.

**Q-N5. Comment savez-vous que le robot a vraiment bougé ?**
Par la mesure du déplacement sur `/odom`, pas par le statut de Nav2 : c'est ce qui a révélé le faux succès (script de contrôle de mouvement).
Dans les CSV, la distance parcourue sert de contrôle : un run est invalide si la couverture et la distance restent figées
(runs figés du 9/10 écartés ; run 121427 retenu seulement jusqu'à 146,5 s). Limite : l'odométrie mesure ce que le robot croit avoir fait,
pas son déplacement physique (pas de rosbag ni de caméra pour recouper).

**Q-N6. Pourquoi B réel s'arrête-t-il à environ 20 cm des murs ?**
Érosion du planificateur : 0,155 m demandés (rayon 0,105 m plus marge 0,05 m), arrondis à 4 cellules de 5 cm, soit 0,20 m appliqués. Le pourcentage est calculé
sur la même zone pour A et B, donc cette bande n'est nettoyée par aucun des deux. Une passe de suivi de mur est une perspective, non testée.

**Q-N7. Pourquoi B réel atteint 98 % alors que A reste à 73–75 % ?**
Avec deux runs chacun, c'est un ordre de grandeur. B suit un trajet planifié de 9,8 m dont la couverture se termine vers 147 à 153 s (distance totale 9,8 m), alors que A
repasse sur des zones déjà couvertes (19,7 à 20,9 m parcourus). La couverture de A progresse encore à 300 s : sa valeur finale n'est pas un plafond.

**Q-N8. Le suiveur est-il équitable face à Nav2 ?**
Il ne s'agit pas d'une comparaison d'exécutants. Il s'agit de comparer deux stratégies (aléatoire contre balayage) avec le même tracker, la même zone,
la même vitesse. L'exécutant de B diffère de la simulation : c'est écrit sur la slide 9 et dans RESULTATS §7.6.

### 3.2 Questions existantes (mises à jour)

**Q1. Pourquoi A en mode accéléré et B en temps réel ?**
Chaque mode a été validé séparément, en temps simulé. A : 5 critères sur 5 (`/scan` 5,00 Hz, `/cmd_vel` 9,99 Hz,
vitesse 0,120 m/s, near_collisions 24 contre 27, % final 54,4 % contre 58,1 %). B : 3 critères sur 5 en échec
(4,42 Hz contre 9,56 Hz, 8 waypoints contre 69, 85 incidents contre 1). Ce n'est pas le même banc : limite annoncée (RESULTATS §6).
Sur le robot réel et le jumeau, tout est en temps réel : la question ne se pose pas.

**Q2. Pourquoi garder le run B3 dans la moyenne ?**
On n'écarte pas un résultat après l'avoir vu. Moyenne officielle 44,1 ± 23,4 %. À côté, 57,6 % pour les 2 runs normaux.
B3 est une limite de fiabilité de la pile B (Nav2) dans notre environnement. Nav2 s'est aussi bloqué sur le robot réel (TF d'AMCL vieille de 27 s : même famille de symptôme, cause non établie) et dans le jumeau (1 run, cause différente : géométrie étroite de la zone, hypothèse).

**Q3. n = 3 suffit-il ?**
Non. L'écart-type de B vaut 23,4 points. Les intervalles de A et de B se recouvrent largement. Aucune conclusion sur le % final.
Sur le robot réel, 2 + 2 runs : encore moins. Perspective : plus de runs.

**Q4. Pourquoi pas la décomposition de Choset ?**
Elle demande une détection de points critiques, un graphe de cellules et un ordre de visite. Estimée à 3 jours ou plus
(PERSPECTIVES P7). Balayage simplifié ; en simulation Nav2 fait les contournements. Limite : un pilier coupe une ligne en segments enchaînés dans l'ordre.

**Q5. Pourquoi pas opennav_coverage, le coverage server de Nav2 ?**
Conçu pour des champs agricoles (polygones, Fields2Cover) [7]. Notre entrée est une grille d'occupation avec 9 piliers.
Le dépôt annonce un tag et une branche pour Humble, mais le README dit que l'API peut changer. Ni installé ni essayé :
perspective P5, avec abandon documenté si le paquet n'est pas disponible.

**Q6. Comment savez-vous que la mesure est équitable ?**
Même nœud `coverage_tracker`, même dénominateur (fonction partagée), même rayon de nettoyage (0,09 m demandé, 0,10 m appliqué),
même début de mesure (premier déplacement), même vitesse d'avance dans chaque banc (0,15 m/s en simulation, 0,10 m/s en réel).
Réserves : en simulation la pose de B vient d'AMCL, celle de A de l'odométrie simulée ; sur le robot réel, les deux viennent de l'odométrie seule.
L'arrondi à la grille rend la mesure légèrement optimiste, pour A comme pour B (PERSPECTIVES P3).

**Q7. Que se passe-t-il sur le robot réel ?** (réponse modifiée : l'essai a eu lieu)
Séance du 12/10, zone en carton de 1,6 m². B atteint 80 % en 125 et 134 s et finit à 98,4 et 96,5 % ; A reste à 73,1 et 74,8 % en 300 s.
B parcourt 9,8 m contre 19,7 et 20,9 m. Mais : 2 + 2 runs, exécutant de B différent de la simulation, odométrie seule (donc dérive,
surtout pour A), un run B incident sur 3 lancés. Les chiffres réels sont approximatifs et non transposables à la simulation.

**Q8. Pourquoi 80 % n'est-il jamais atteint en simulation ?**
Meilleur run : B1 avec 59,8 %. Borne optimiste calculée hors ligne (RESULTATS §4 bis, ce n'est pas une mesure) :
trajet idéal 91,7 m, au moins 75,7 m pour 80 %, soit au moins 505 s de translation pure à 0,15 m/s sur 600 s. La marge est faible même pour un robot parfait.
À 70,2 m (distance de B1), le trajet idéal couvrirait 76,3 %, contre 59,8 % mesurés. L'écart vient des rotations sur place
(environ 18 % du temps), des arrêts d'environ 30 s sur les petits segments et des lignes coupées par les piliers, sans chiffrer la part de chacun.
Sur la petite zone réelle, 80 % est atteint par B en environ 2 min : l'objectif de départ dépend de la taille de la zone par rapport au temps et à la vitesse.

**Q9. Alors B ne bat pas A : à quoi sert la planification ?**
En simulation, pas de conclusion ferme sur le % final. Sur la sécurité : 0 et 2 near_collisions (runs normaux de B) contre 25,7 en moyenne pour A.
Sur la régularité : B1 et B2 quasi superposées. Sur le robot réel, B finit la zone avec deux fois moins de distance que A.
En contrepartie, B dépend de plus de composants : un run sur trois bloqué en simulation, Nav2 inutilisable sur le robot réel.

**Q10. Pourquoi avoir changé de contrôleur (T3) ? Est-ce mesuré ?**
DWB restait bloqué devant un pilier (T2 : blocage dès 177 s). Avec Regulated Pure Pursuit : 28,5 % à 300 s contre 21,9 %,
0 « Failed to make progress » contre 13. Réserve : RPP pas comparé à d'autres contrôleurs ; T3 et T5 ont une seed chacun.

**Q11. Pourquoi votre amélioration T4 a-t-elle échoué ?**
Avec RPP, Nav2 contourne déjà les obstacles. Nos points intermédiaires ont fait passer le trajet de 112 à 245 waypoints
et consommé 38 % du temps. Résultat : 22,4 % contre 28,5 % à 300 s. Une amélioration « évidente » doit être mesurée.

**Q12. Le gel de la TF : est-ce un bug de votre code ?**
Pas démontré. AMCL publie sans interruption (5 Hz, aucun trou supérieur à 1 s dans le rosbag), mais Nav2 voit la TF figée.
Vu en T1, en mode accéléré et en B3. Pistes non vérifiées : charge CPU sous WSL, DDS, buffer TF. Sur le robot réel, la TF `map` vers `odom`
d'AMCL avait 27 s de retard : même famille de symptôme, cause non établie.

**Q13. Pourquoi le seuil near_collisions est-il à 0,15 m et non au rayon du robot ?**
Le `range_min` du LiDAR vaut 0,12 m, supérieur au rayon du robot (0,105 m). Avec la définition du brief, la métrique serait
toujours nulle. Front montant sous 0,15 m, sur 360°, pour A comme pour B en simulation. Sur le robot réel : 0,20 m (au-dessus de la portée minimale du LDS-02).
Les valeurs ne sont donc pas comparables entre simulation et réel.

**Q14. Vos résultats se généralisent-ils à une autre pièce ?**
Non. `turtlebot3_world` (13,9 m²) et une zone réelle (1,6 m²) : deux zones, réglages adaptés à la première.
Perspective : un second monde sans changer les paramètres.

**Q15. Vous avez modifié le code de l'executor après les mesures. Les résultats restent-ils valables ?**
Le refactoring était de lisibilité. Un essai de non-régression de 120 s en temps réel donne 7,6 % à 60 s et 15,4 % à 120 s,
contre 8,3 à 8,4 % et 15,5 à 16,2 % pour B1 et B2. Un seul essai, pas une campagne.

**Q16 (réserve). Pourquoi pas la spirale ou le Spanning Tree Coverage ?**
Spirale : insuffisante seule avec des obstacles, classée dans [1], perspective P6. STC [5][6] : demande une grille de cellules
à la taille du robot et un suiveur plus fin. Non implémenté ; nos jugements sur ses limites pratiques restent à confirmer (ETAT_DE_L_ART §2.4).

---

## 4. Chiffres à retenir par cœur

**Simulation (`turtlebot3_world`, 600 s)**

1. **A : 51,0 ± 6,7 %** (3 runs, mode accéléré).
2. **B : 44,1 ± 23,4 %** (3 runs, officiel), soit **57,6 %** sur les 2 runs normaux ; B3 bloqué à 17,2 %.
3. **80 % jamais atteint** : meilleur run B1, 59,8 %.
4. **near_collisions : A 25,7 en moyenne, B 0 et 2** sur ses deux runs normaux.
5. **T0 vers T5 : 33,2 % vers 59,7 %** à 600 s pour B (une seule seed par configuration).

**Robot réel (zone en carton, 620 cellules, environ 1,6 m², 0,10 m/s, séance du 12/10)**

6. **À 120 s : B 75,2 et 79,3 %, A 30,3 et 36,2 %.**
7. **Final : B 96,5 et 98,4 %, A 73,1 et 74,8 % (300 s).** B atteint 80 % en 125 et 134 s ; A ne l'atteint pas.
8. **Distance : B 9,8 m (deux runs), A 19,7 et 20,9 m.** near_collisions : B 8 et 2, A 21 et 19.
9. **Exécutant de B réel : suiveur, pas Nav2.** 2 + 2 runs, plus 1 run B incident (46,8 %, exclu).

**Jumeau numérique (1 run par configuration, 300 s)**

10. **A 82,7 %, B suiveur 93,1 %, B Nav2 67,7 % (bloqué dès 107 s).** Distances : A 19,3 m, B 9,7 m.

**Impasse Nav2 réelle** : horloge 462 ms vers 30–60 ms ; âge des messages 0,26 s ; TF `map` vers `odom` vieille de 27 s ; pivots de 109° à 174° sans avancer.

Chiffres de réserve : 5564 cellules (13,9 m²) et 112 waypoints en simulation ; 8 waypoints atteints en accéléré contre 69 en temps réel ;
marge aux bords environ 20 cm (érosion de 4 cellules, 0,20 m) ; 96 boîtes pour 486 cellules murs dans le jumeau.

---

## 5. Divergences relevées dans les documents (à trancher par l'étudiant)

Règle appliquée dans ce plan : on retient `docs/RESULTATS.md`, calculé depuis les CSV ; le journal donne parfois des valeurs arrondies ou
interpolées autrement. À préciser à l'oral si on les demande.

1. **T3 à 300 s** : 28,5 % (RESULTATS §5, run de réglage de 300 s) contre 29,0 % (JOURNAL, vérification croisée, run de 600 s). Deux runs distincts.
2. **Premier run de A** : 58,1 % (JOURNAL, run en temps réel) contre 54,4 % pour A1 officiel (run accéléré, même seed). Écart attendu pour une marche aléatoire (critère C5).
3. **Durée d'activation de Nav2** : environ 12 s (premier run B) contre 10 à 17 s (correctif de course). Compatible.
4. **Valeurs réelles du 12/10 : journal contre RESULTATS §7.6** (le journal lit le dernier échantillon avant l'instant, RESULTATS interpole : vérifié dans les CSV) : A seed 1 à 30 s, 5,2 % (journal) contre 5,6 % ;
   A seed 1 à 120 s, 36,1 % contre 36,2 % ; A seed 3 à 60 s, 23,2 % contre 23,4 % ; B n°1 à 120 s, 79,4 % contre 79,3 % ;
   B n°2 à 60 s, 29,7 % contre 30,3 %, à 120 s, 74,5 % contre 75,2 % ; fin de trajet de B n°2 : « vers 157 s » (journal) contre « figé dès 153 s » (RESULTATS).
   Ce plan utilise RESULTATS. Les fourchettes annoncées (B ≈ 75–79 % à 120 s, A ≈ 30–36 %) restent exactes dans les deux cas.
5. **near_collisions du B Nav2 du jumeau** : 48 (CSV) contre 46 (note de séance). Le CSV fait foi.
6. **Nombre de tests** : 107 tests passent (`pytest src/aspi_bot/test`, 84 fonctions dont certaines paramétrées, 6 fichiers), recompté le 12/10 après l'ajout de `test_follow_logic.py`.

---

## 6. Avant la soutenance : liste de vérifications

**Mermaid**

- [ ] Prévisualiser chaque diagramme Mermaid retenu (ARCHITECTURE §2.1 et §7.1, ALGORIGRAMMES §1.2, §2.2 et §5) dans un rendu Mermaid avant de les copier : vérifier qu'aucun nœud ne déborde.
- [ ] Alléger les nœuds (moins de texte) pour la lisibilité à 3 m de l'écran. Garder les types de topics sur le schéma système.
- [ ] Tracer le petit algorigramme de la slide 10 (faux succès de Nav2) : il n'existe pas encore.
- [ ] Vérifier que le schéma de la slide 4 correspond à `rqt_graph` (exigence du brief) ; non revérifié ici.

**Captures (`results/figures/`) : cadrage observé**

- [ ] `jumeau_B_rviz_t090.png` : bien cadrée (trajet vert, couverture rose, scan rouge). Recadrer pour ne garder que la vue de la carte si besoin.
- [ ] `jumeau_A_rviz_t300.png` : **cadrage serré mais zone petite**, bande noire à gauche (hors fenêtre), zone couverte magenta visible. À recadrer sur la carte seule.
- [ ] `jumeau_Bnav2_rviz_fin_trajet.png` : bien cadrée (couverture rose arrêtée avant la fin du trajet vert), **bande noire à gauche à retirer**.
- [ ] `jumeau_A_gazebo_t030.png` : **mal cadrée** : la fenêtre Gazebo est coupée à droite (vue 3D en partie hors cadre), bande noire à gauche, avertissement « fin de vie de Gazebo » dans la barre. À recadrer sur la vue 3D, ou à remplacer par `t150` ou `t300` après vérification (non vues ici).
- [ ] Les 12 autres captures (`jumeau_A_*_t030/t150`, `jumeau_B_*`, `jumeau_Bnav2_*`) n'ont pas été ouvertes pour ce plan : les regarder avant de les mettre sur une slide.
- [ ] Toutes les captures montrent le titre de fenêtre `/home/maxime/ros2_ws/install/...aspi.rviz*` : recadrer au-dessous de la barre de titre.
- [ ] Courbes : `jumeau_vs_reel.png`, `coverage_vs_time_reel_12oct.png` et `coverage_vs_time_runs.png` ont été regardées : lisibles. Expliquer à l'oral les pointillés de B sur la figure du 12/10 (prolongement après la fin du trajet, non mesuré). Le jumeau n'a pas de prolongement.

**À fournir par l'étudiant**

- [ ] **Photo ou courte vidéo du robot réel dans la zone en carton** (slide 9). Emplacement prévu : coin de la slide, ou insert de 5 s. Sans fichier, laisser la courbe seule.
- [ ] Cartographer pour la carte `zone_reelle` : à confirmer par l'étudiant, consigné dans JOUR_ROBOT §8 (le journal ne le dit pas).
- [ ] Confirmer s'il existe un rosbag d'un run réel (le journal du 9/10 note leur absence) ; sinon, le dire en limite.
- [ ] Slide 13 alignée sur `docs/PERSPECTIVES.md` (P10 recalage LiDAR, P11 suivi de mur, P9 marqué réalisé) : relire une fois les deux fichiers côte à côte.

**Chiffres et dossier**

- [ ] Relancer `cd ~/ros2_ws/src/aspi_bot && python3 -m pytest test/ -q` et recompter les tests avant de citer un nombre.
- [ ] Recouper chaque chiffre de la slide 9 avec `docs/RESULTATS.md` §7.6, et de la slide 11 avec §7.7.
- [ ] Relire les slides : aucun extrait de code ; aucune mention d'outil ou d'auteur en dehors des sources citées ; références [1] à [7] présentes en bas de la slide 2.
- [ ] Chronométrer deux fois : cible 9 min 30. Plan de coupe : fusionner 7 dans 8, passer la slide 5 à une phrase.
- [ ] Préparer en annexe (hors des 13 slides) : ARCHITECTURE §1.1 (schéma de A), §2.2 (intérieur de Nav2), la figure `coverage_vs_time.png`, et `jumeau_A_rviz_t300.png`.

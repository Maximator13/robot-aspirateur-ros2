# Plan de soutenance

10 minutes de présentation, 10 minutes de questions.
Fil : problème, options, solution retenue, évaluation chiffrée, leçons, perspectives.

Règles tenues dans ce plan :

- aucun extrait de code sur les slides : des algorigrammes à la place ;
- schéma système obligatoire (nœuds, topics avec types, launch, Nav2) ;
- pas de vidéo (décision de l'étudiant) : des figures et des tableaux ;
- tous les chiffres viennent de `docs/RESULTATS.md`, `docs/JOURNAL.md`, `docs/ARCHITECTURE.md`,
  `docs/ETAT_DE_L_ART.md` et `docs/PERSPECTIVES.md`.

Option capture RViz : si l'étudiant le souhaite, il peut faire lui-même une capture d'écran de RViz
(carte `/coverage_map` colorée, trajet `/coverage_path` en B). Elle irait sur la slide 7 (en insert)
ou sur la slide 5. Ce n'est pas indispensable : le plan fonctionne sans elle.

---

## 1. Plan des slides (12 slides, environ 9 min 20 + 40 s de marge)

| N° | Titre | Durée |
|---|---|---|
| 1 | Problème et objectif | 0:30 |
| 2 | État de l'art | 0:55 |
| 3 | Deux stratégies retenues | 0:40 |
| 4 | Algorigrammes : A et planner de B | 0:45 |
| 5 | Schéma système (stratégie B) | 0:55 |
| 6 | Une mesure équitable : protocole et tracker | 0:45 |
| 7 | Résultats : courbes | 0:55 |
| 8 | Résultats : tableau | 0:45 |
| 9 | Démarche : régler B de T0 à T5 | 0:55 |
| 10 | Bugs et impasses | 1:10 |
| 11 | Limites assumées | 0:25 |
| 12 | Perspectives et conclusion | 0:40 |

Total : 560 s, soit 9 min 20. Les 40 s restantes servent aux transitions.

---

### Slide 1. Problème et objectif (0:30)

- **Message clé** : couvrir toute une pièce, c'est un problème connu (CCPP), et nous le mesurons.
- **Contenu**
  - TurtleBot3 Burger, simulation Gazebo, monde `turtlebot3_world`, une pièce de 13.9 m² atteignables.
  - Objectif : passer sur toute la surface libre, comme un robot aspirateur.
  - Question posée : une stratégie planifiée avec carte bat-elle une stratégie aléatoire sans carte ?
  - Seuil visé : 80 % de surface couverte en 10 min simulées.
  - Évalué : la démarche (problème, options, solution, mesure, leçons), pas un résultat parfait.
- **Visuel** : aucun fichier. Titre, une phrase, une icône de pièce si l'étudiant veut.
- **Durée** : 0:30.

### Slide 2. État de l'art (0:55)

- **Message clé** : cinq familles d'approches existent ; deux seulement sont réalisables en 3 jours.
- **Contenu** (une ligne par approche : principe, limite, décision)
  - Aléatoire type Roomba [3] : sans carte, sans garantie. **Retenu** (stratégie A).
  - Spirale [1] : bonne en zone dégagée, insuffisante avec obstacles. Non retenue.
  - Boustrophédon et décomposition cellulaire de Choset [2][4] : lignes parallèles, carte exigée.
    **Retenu sous forme simplifiée** (stratégie B).
  - Spanning Tree Coverage, Gabriely & Rimon [5][6] : grille de cellules à la taille du robot. Non retenu.
  - Coverage server de Nav2, opennav_coverage [7] : conçu pour des champs agricoles. Non retenu.
  - Référence de synthèse : Galceran & Carreras [1].
- **Visuel** : tableau comparatif de `docs/ETAT_DE_L_ART.md`, section 3
  (colonnes : carte requise, complétude, redondance, complexité, retenu). Références [1] à [7] en bas de slide.
- **Durée** : 0:55.

### Slide 3. Deux stratégies retenues (0:40)

- **Message clé** : A est la borne basse simple, B est une planification simplifiée exécutée par Nav2.
- **Contenu**
  - A : avancer, tourner d'un angle aléatoire de 90 à 180 degrés devant un obstacle. Graine fixée.
  - B : carte, zone atteignable, lignes de balayage tous les 0.18 m, waypoints envoyés à Nav2.
  - Limite assumée de B : ce n'est pas une décomposition de Choset. Nav2 contourne les obstacles.
  - Raison du choix : décomposition complète trop longue pour 3 jours (JOURNAL, entrée T3).
  - Même vitesse d'avance : 0.15 m/s dans les deux cas.
- **Visuel** : tableau à deux colonnes (A / B) construit à la main. Source des valeurs : `docs/ETAT_DE_L_ART.md`
  section 4 et `docs/RESULTATS.md` section 1.
- **Durée** : 0:40.

### Slide 4. Algorigrammes : A et planner de B (0:45)

- **Message clé** : deux algorithmes simples, testables sans ROS.
- **Contenu**
  - A : deux états, avancer et tourner. Le test porte sur la distance minimale dans le secteur avant ±30 degrés,
    seuil 0.25 m.
  - B : carte, érosion de l'espace libre, composante connexe du départ, lignes alternées, extrémités de segments.
  - Résultat sur la carte : 5564 cellules atteignables, 112 waypoints.
  - 39 tests unitaires au total (JOURNAL, entrée T4).
- **Visuel** : deux algorigrammes côte à côte.
  - À gauche : `docs/ALGORIGRAMMES.md`, section 1.2 (machine à états du `random_walker`).
  - À droite : `docs/ALGORIGRAMMES.md`, section 2.2 (balayage boustrophédon). Le masque de la section 2.1
    peut tenir en une phrase au-dessus.
  - Les deux diagrammes sont à simplifier pour la slide (moins de texte dans les nœuds).
- **Durée** : 0:45.

### Slide 5. Schéma système (stratégie B) (0:55)

- **Message clé** : trois nœuds à nous, un tracker commun, et Nav2 fait le travail de navigation.
- **Contenu**
  - Nœuds du projet : `coverage_planner`, `coverage_executor`, `coverage_tracker`.
  - Topics et types : `/map` (`nav_msgs/OccupancyGrid`), `/coverage_path` (`nav_msgs/Path`),
    `/scan` (`sensor_msgs/LaserScan`), `/cmd_vel` (`geometry_msgs/Twist`),
    `/coverage_status` (`aspi_interfaces/CoverageStatus`).
  - Action Nav2 : `FollowWaypoints` (`nav2_msgs/action/FollowWaypoints`).
  - TF : `map` vers `odom` par AMCL, `odom` vers `base_footprint` par le plugin Gazebo.
  - Launch : `aspi_planned.launch.py` inclut `sim.launch.py` (Gazebo + robot) et `bringup_launch.py` de Nav2.
  - A : même schéma sans Nav2 ni planner, avec `random_walker` et un TF statique `map` vers `odom`.
- **Visuel** : `docs/ARCHITECTURE.md`, section 2.1 (nœuds du projet, avec types de topics et action).
  Ajouter en petit : section 2.3 (arbre TF) et section 2.4 (launch).
  Le détail de l'intérieur de Nav2 (section 2.2) reste en annexe, pour les questions.
  Le schéma de A (section 1.1) aussi en annexe. Ces diagrammes sont détaillés : prévoir une version allégée
  pour la slide.
- **Durée** : 0:55.

### Slide 6. Une mesure équitable : protocole et tracker (0:45)

- **Message clé** : A et B sont mesurées par le même nœud, avec le même dénominateur.
- **Contenu**
  - Même nœud `coverage_tracker` pour les deux stratégies.
  - Même dénominateur : 5564 cellules atteignables, 13.9 m², masque calculé par la même fonction.
  - Une cellule est couverte quand le robot passe à moins de 0.09 m demandé, arrondi à 2 cellules (0.10 m appliqué).
  - Espacement des lignes de B : 0.18 m demandé, 4 cellules appliquées (0.20 m).
  - Mesure lancée au premier déplacement : l'activation de Nav2 n'est pas comptée.
  - 600 s simulées, départ identique (-2.0, -0.5), 3 runs par stratégie (seeds 1, 2, 3).
  - A en mode accéléré, validé par 5 critères fixés avant les runs. B en temps réel (accéléré invalidé, slide 10).
- **Visuel** : tableau de protocole bâti depuis `docs/RESULTATS.md`, section 1. Optionnel : encadré
  « même tracker » avec `docs/ARCHITECTURE.md`, section 5.
- **Durée** : 0:45.

### Slide 7. Résultats : courbes (0:55)

- **Message clé** : aucune stratégie n'atteint 80 %, et les moyennes restent proches jusqu'à 9 min.
- **Contenu**
  - 80 % jamais atteint. Meilleur run : B1 avec 59.8 %.
  - A : 51.0 ± 6.7 %. B : 44.1 ± 23.4 % (3 runs, officiel).
  - Les moyennes de A et B restent à moins de 4 points l'une de l'autre jusqu'à 540 s, parce que B3 tire la moyenne de B vers le bas.
  - Pris séparément, B1 et B2 devancent la moyenne de A dès environ 4 min.
  - B1 et B2 se terminent à 59.8 % et 55.4 %. B3 s'arrête à 17.2 % (blocage, slide 10).
  - Quand Nav2 fonctionne, B1 et B2 sont quasi identiques. Les runs de A divergent plus tôt.
  - Aucune conclusion statistique ferme avec n = 3.
- **Visuel** : `results/coverage_vs_time.png` (moyennes, runs et enveloppes) à gauche ;
  `results/coverage_vs_time_runs.png` (un sous-graphe par stratégie, seeds étiquetées) en dessous ou à droite.
  Si la place manque, garder `coverage_vs_time_runs.png` : il montre B3 et la reproductibilité de B1 et B2.
  Option : une capture RViz faite par l'étudiant en insert.
- **Durée** : 0:55.

### Slide 8. Résultats : tableau (0:45)

- **Message clé** : B est plus sûre quand elle fonctionne, mais moins fiable.
- **Contenu**
  - near_collisions : A 25.7 en moyenne, B 0 et 2 sur les runs normaux, 25 sur le run bloqué.
  - Distance : A environ 70 m par run. B 70.2 m et 62.2 m, 29.5 m pour B3.
  - À 300 s : 27.6 ± 3.6 % (A) contre 26.1 ± 7.7 % (B).
  - Information complémentaire : 2 runs de B sur 3 terminés normalement, 57.6 % en moyenne.
  - La fiabilité fait partie de la performance (JOURNAL, entrée B3).
- **Visuel** : tableau de `docs/RESULTATS.md`, section 2 (« Tableau par run »), réduit aux colonnes
  stratégie, seed, % final, distance, near_collisions. Les deux lignes de moyenne en gras.
  Source des chiffres bruts : `results/summary.md`.
- **Durée** : 0:45.

### Slide 9. Démarche : régler B de T0 à T5 (0:55)

- **Message clé** : un facteur à la fois, une mesure à chaque fois ; l'impasse T4 est documentée.
- **Contenu** (chaîne de réglages, chiffres de `docs/RESULTATS.md`, section 5)
  - T0, config TurtleBot3 d'origine : 19.5 % à 300 s, 33.2 % à 600 s. Fréquence de boucle du suiveur de waypoints
    à 2000 Hz, CPU saturé.
  - T1, boucle ramenée à 20 Hz : 18.2 % à 300 s. Surcharge supprimée, comportement inchangé.
  - T2, inflation réduite (0.30 m) : 21.9 %. Blocage devant le pilier dès 177 s.
  - T3, contrôleur Regulated Pure Pursuit à 0.15 m/s : 28.5 % à 300 s, 54.1 % à 600 s.
  - T4, contournements calculés par notre planner : 22.4 %. **Impasse**, code conservé et désactivé.
  - T5, ralentissement d'approche réduit, pause supprimée : 30.6 % à 300 s, 59.7 % à 600 s. **Retenu.**
  - Réserve à dire : T3 et T5 comparés avec une seule seed chacune (1 et 5).
- **Visuel** : tableau T0 à T5 de `docs/RESULTATS.md`, section 5 (colonnes essai, modification, % à 300 s,
  % à 600 s). Option : le même tableau en frise horizontale (flèches T0 vers T5), faite à la main.
- **Durée** : 0:55.

### Slide 10. Bugs et impasses (1:10)

- **Message clé** : chaque bug a produit une règle de travail.
- **Contenu** (4 entrées, détail dans la section 2 ci-dessous)
  1. Repère `map` vers `odom` : l'hypothèse « identité » était fausse. Deux bugs se masquaient.
  2. Mode accéléré : bon pour A, invalidé pour B. Un critère isolé était trompeur.
  3. Executor de B : fuite mémoire (4.8 Go) et attente sans délai. Toute attente doit avoir une sortie.
  4. Run B3 : TF figée dans Nav2, cause non identifiée. Décision de le garder dans la moyenne.
  - Renvoi : la fréquence de boucle à 2000 Hz et l'impasse T4 sont sur la slide 9.
- **Visuel** : tableau à trois colonnes (bug, cause, leçon). Aucun fichier de `results/` n'est nécessaire.
  Option : `results/coverage_vs_time_runs.png` en miniature pour B3.
- **Durée** : 1:10.

### Slide 11. Limites assumées (0:25)

- **Message clé** : nous disons nous-mêmes ce que la mesure ne prouve pas.
- **Contenu**
  - 3 runs par stratégie, une seule pièce, odométrie simulée sans dérive.
  - A et B en modes de simulation différents, chacun validé.
  - Position de B estimée par AMCL, celle de A vient de l'odométrie.
  - Blocage de la TF non diagnostiqué : il peut se reproduire.
- **Visuel** : liste de puces. Source : `docs/RESULTATS.md`, section 6.
- **Durée** : 0:25.

### Slide 12. Perspectives et conclusion (0:40)

- **Message clé** : des incréments petits, chacun avec une mesure de succès.
- **Contenu**
  - P1 : plus de runs (5 par stratégie) pour une conclusion statistique, effort 0,5 jour.
  - P2 : réduire les rotations sur place, qui pèsent environ 18 % du temps de B.
  - P4 : diagnostiquer le gel de la TF `map` vers `odom`, effort 1 jour.
  - P5 : essayer opennav_coverage comme référence, disponibilité pour Humble à vérifier.
  - Conclusion : mesure comparable, 80 % non atteint, B plus sûre mais moins fiable, démarche documentée.
- **Visuel** : tableau « classement gain / effort » de `docs/PERSPECTIVES.md` (rangs 1 à 5 seulement).
- **Durée** : 0:40.

---

## 2. Détail des slides 9 et 10 (fil de la parole)

### Slide 9. Chaîne de réglages T0 à T5

Ordre de lecture à l'oral : problème mesuré, correction, effet.

1. T0 : 19.5 % à 300 s. Cause trouvée en lisant le log : 37 000 lignes « Processing waypoint ».
2. T1 : on corrige la fréquence de boucle. La surcharge disparaît, le comportement ne change pas.
   Leçon : un vrai défaut peut ne pas être la cause du problème observé.
3. T2 : on réduit l'inflation. Le début est plus rapide (+4 points à 180 s), mais le robot reste bloqué devant un pilier.
4. T3 : on change de contrôleur. 28.5 % à 300 s contre 21.9 %, 0 « Failed to make progress » contre 13.
5. T4 : on ajoute des contournements calculés. 245 waypoints au lieu de 112, 22.4 % contre 28.5 %.
   Les points intermédiaires consomment 38 % du temps.
6. T5 : on retire un ralentissement et une pause. 59.7 % à 600 s contre 54.1 %. Avec une seule seed chacun.

Phrase de conclusion : les paramètres de sécurité de Nav2 sont pensés pour aller d'un point à un autre,
pas pour longer les obstacles.

### Slide 10. Les quatre bugs et impasses retenus

| Bug ou impasse | Ce qui s'est passé | Leçon |
|---|---|---|
| Repère `map` vers `odom` et inconnu relu libre | Le premier run de A ne comptait que 754 cellules au lieu de 5564. Le plugin Gazebo publie `odom` dans le repère du monde (-2.0, -0.5 au spawn). Le TF identité prévu par le brief décalait la trajectoire de 2 m. Un second bug masquait le premier : les pixels inconnus de la carte étaient relus comme libres (seuil à 0.25). | Vérifier une hypothèse par une mesure (lecture de `/odom`). Un contrôle de cohérence (nombre de cellules attendu) détecte l'erreur silencieuse. Deux bugs peuvent se masquer. |
| Mode accéléré invalidé pour B | Cinq critères fixés avant les runs. Fréquence du contrôleur 4.42 Hz contre 9.56 Hz, 8 waypoints contre 69, 85 incidents contre 1. Le % final seul paraissait bon (56.8 % contre 54.1 %), mais à 300 s : 53.6 % contre 29.0 %. | Valider un changement de banc par plusieurs critères chiffrés fixés à l'avance, dont des critères de comportement. |
| Executor de B : fuite mémoire et attente infinie | Un executor orphelin occupait 4.8 Go (80 % de la RAM). Une boucle d'attente ne testait pas l'état du contexte ROS. Au démarrage, une attente sans délai dans la bibliothèque s'est bloquée 2 fois sur 5 lancements. | Toute attente doit tester l'état de ROS et avoir une sortie explicite ou un délai. |
| Run B3 : TF figée dans Nav2 | À environ 135 s, la TF `map` vers `odom` vue par Nav2 reste figée, alors qu'AMCL la publie à 5 Hz (rosbag). 4 329 messages « Transform data too old ». Couverture bloquée à 17.2 %. Cause non identifiée. | Ne pas écarter un résultat après l'avoir vu. La fiabilité fait partie de la performance. |

Ordre conseillé à l'oral : 1, 2, 3, 4. Si le temps manque, garder 1, 2 et 4 (le 3 passe en question).

Autres bugs utiles en réserve (JOURNAL) : seuil `near_collisions` (le `range_min` du LiDAR, 0.12 m, dépasse le rayon
du robot, 0.105 m), course au démarrage de Nav2 (but rejeté 2 fois sur 2 après un premier correctif),
SIGINT ignoré par les processus lancés en arrière-plan.

---

## 3. Préparation aux questions du jury

Réponses courtes et honnêtes. Chaque réponse est appuyée sur un chiffre ou une source du dossier.

**Q1. Pourquoi A en mode accéléré et B en temps réel ?**
Chaque mode a été validé séparément, en temps simulé. A : 5 critères sur 5 (`/scan` 5.00 Hz, `/cmd_vel` 9.99 Hz,
vitesse 0.120 m/s, near_collisions 24 contre 27, % final 54.4 % contre 58.1 %). B : 3 critères sur 5 en échec
(4.42 Hz contre 9.56 Hz, 8 waypoints contre 69, 85 incidents contre 1). Ce n'est pas le même banc : c'est une limite
que nous annonçons (RESULTATS, section 6).

**Q2. Pourquoi garder le run B3 dans la moyenne ?**
On n'écarte pas un résultat après l'avoir vu. La moyenne officielle est 44.1 ± 23.4 %. À côté, nous donnons
57.6 % pour les 2 runs normaux. B3 est une limite de fiabilité de la pile B dans notre environnement.

**Q3. n = 3 suffit-il ?**
Non. L'écart-type de B vaut 23.4 points. Les intervalles de A et de B se recouvrent largement. Nous ne concluons
pas sur le % final. Perspective P1 : 5 runs par stratégie.

**Q4. Pourquoi pas la décomposition de Choset ?**
Elle demande une détection de points critiques, un graphe de cellules et un ordre de visite. Estimée à 3 jours ou plus
(PERSPECTIVES P7). Nous avons gardé un balayage simplifié, avec Nav2 pour les contournements. Limite assumée :
un pilier coupe une ligne en segments enchaînés dans l'ordre.

**Q5. Pourquoi pas opennav_coverage, le coverage server de Nav2 ?**
Il est conçu pour des champs agricoles (polygones, Fields2Cover) [7]. Notre entrée est une grille d'occupation
avec 9 piliers. Le dépôt annonce un tag et une branche pour Humble, mais le README dit que l'API peut changer. Nous ne l'avons pas
installé ni essayé : c'est la perspective P5, avec abandon documenté si le paquet n'est pas disponible.

**Q6. Comment savez-vous que la mesure est équitable ?**
Même nœud `coverage_tracker`, même dénominateur (5564 cellules, fonction partagée), même rayon de nettoyage
(0.09 m demandé, 0.10 m appliqué après arrondi à 2 cellules), même début de mesure (premier déplacement), même vitesse d'avance (0.15 m/s). Réserve : la pose de B vient
d'AMCL, celle de A de l'odométrie simulée. Les deux sources n'ont pas la même erreur. Autre réserve : l'arrondi à la grille
(rayon 0.09 vers 0.10 m, espacement 0.18 vers 0.20 m) rend la mesure légèrement optimiste, pour A comme pour B (PERSPECTIVES P3).

**Q7. Que se passerait-il sur le robot réel ?**
Nous ne le savons pas : aucun essai réel. Le LiDAR serait bruité et l'odométrie dériverait. A serait mesurée avec
dérive, donc moins fiable. Le TF statique de A suppose une odométrie sans dérive. B dépend d'AMCL, déjà fragile en
simulation (B3). Perspective P9, après P1 et P2.

**Q8. Pourquoi 80 % n'est-il jamais atteint ?**
Meilleur run : B1 avec 59.8 %. Une borne optimiste calculée hors ligne (RESULTATS, section 4 bis, ce n'est pas une mesure) :
le trajet idéal fait 91.7 m, il faut au moins 75.7 m pour atteindre 80 %, soit au moins 505 s de translation pure à
0.15 m/s sur 600 s. La marge est faible même pour un robot parfait (au plus 90 m parcourables). À 70.2 m (distance de B1),
le trajet idéal couvrirait 76.3 %, contre 59.8 % mesurés. L'écart vient des rotations sur place (environ 18 % du temps),
des arrêts d'environ 30 s sur les petits segments et des lignes coupées par les piliers, sans chiffrer la part de chacun.
Pour A, les plateaux viennent des repassages sur zones déjà couvertes. Le seuil de 80 % est un objectif de départ,
pas une garantie.

**Q9. Alors B ne bat pas A : à quoi sert la planification ?**
Sur le % final, pas de conclusion ferme. Sur la sécurité, oui : 0 et 2 near_collisions sur les runs normaux de B contre
25.7 en moyenne pour A. Sur la régularité, B1 et B2 sont quasi superposées. En contrepartie, B dépend de plus de composants :
un run sur trois s'est bloqué. La planification n'apporte pas ici un gain de couverture démontré.

**Q10. Pourquoi avoir changé de contrôleur (T3) ? Est-ce mesuré ?**
DWB restait bloqué devant un pilier (T2 : blocage dès 177 s). Avec Regulated Pure Pursuit : 28.5 % à 300 s contre
21.9 %, 0 « Failed to make progress » contre 13. Réserve : RPP n'a pas été comparé à d'autres contrôleurs, et T3 comme T5
n'ont qu'une seed chacun.

**Q11. Pourquoi votre amélioration T4 a-t-elle échoué ?**
Avec RPP, Nav2 contourne déjà les obstacles. Nos points intermédiaires ont fait passer le trajet de 112 à 245 waypoints
et consommé 38 % du temps (replanification et rotation à chaque but). Résultat : 22.4 % contre 28.5 % à 300 s. Une amélioration
« évidente » doit être mesurée.

**Q12. Le gel de la TF : est-ce un bug de votre code ?**
Pas démontré. AMCL publie sans interruption (5 Hz, aucun trou supérieur à 1 s dans le rosbag), mais Nav2 voit la TF
figée. Le phénomène est apparu en T1, en mode accéléré et en B3. Pistes non vérifiées : charge CPU sous WSL, DDS,
buffer TF. Perspective P4 : une journée de diagnostic.

**Q13. Pourquoi le seuil near_collisions est-il à 0.15 m et non au rayon du robot ?**
Le `range_min` du LiDAR vaut 0.12 m, supérieur au rayon du robot (0.105 m). Avec la définition du brief, la métrique serait
toujours nulle. Nous comptons un front montant sous 0.15 m, sur 360 degrés, pour A comme pour B.

**Q14. Vos résultats se généralisent-ils à une autre pièce ?**
Non. Une seule pièce de 13.9 m², et les réglages T0 à T5 sont adaptés à ce monde. Perspective P8 : un second monde sans
changer les paramètres.

**Q15. Vous avez modifié le code de l'executor après les mesures. Les résultats restent-ils valables ?**
Le refactoring était de lisibilité. Un essai de non-régression de 120 s en temps réel donne 7.6 % à 60 s et 15.4 % à 120 s,
contre 8.4 à 8.5 % et 15.6 à 16.2 % pour B1 et B2. C'est un seul essai, pas une campagne.

**Q16 (réserve). Pourquoi pas la spirale ou le Spanning Tree Coverage ?**
Spirale : insuffisante seule avec des obstacles, classée dans [1], perspective P6. STC [5][6] : demande une grille de cellules
à la taille du robot et un suiveur plus fin. Nous ne l'avons pas implémenté : nos jugements sur ses limites pratiques
restent à confirmer (ETAT_DE_L_ART, section 2.4).

---

## 4. Les 5 chiffres à retenir par cœur

1. **A : 51.0 ± 6.7 %** de couverture finale (3 runs, 600 s, mode accéléré).
2. **B : 44.1 ± 23.4 %** (3 runs, officiel), soit **57.6 %** sur les 2 runs normaux. Le troisième est bloqué à 17.2 %.
3. **80 % jamais atteint** : le meilleur run est B1 avec 59.8 %.
4. **near_collisions : 25.7 en moyenne pour A, contre 0 et 2 pour B** sur ses deux runs normaux.
5. **T0 vers T5 : 33.2 % vers 59.7 %** à 600 s pour B (une seule seed par configuration, seeds différentes).

Chiffres de réserve : 5564 cellules (13.9 m²), 112 waypoints, 8 waypoints atteints en accéléré contre 69 en temps réel.

---

## 5. Divergences relevées dans les documents (à trancher par l'étudiant)

Les divergences d'ARCHITECTURE (section 4), de PERSPECTIVES (P1, P3) et des courbes superposées sont résolues.
Pour les courbes, la formulation précise est celle de la slide 7 et de `docs/RESULTATS.md`, section 4 : deux objets différents
(moyennes avec B3, ou B1 et B2 seuls).
Restent trois points mineurs, à préciser à l'oral si on les demande.

1. **T3 à 300 s** : 28.5 % (RESULTATS section 5, run de réglage de 300 s) contre 29.0 % (JOURNAL, vérification croisée, run
   de 600 s). Ce sont deux runs distincts. À préciser à l'oral si la question est posée.
2. **Premier run de A** : 58.1 % (JOURNAL, run en temps réel de référence) contre 54.4 % pour A1 officiel (run accéléré,
   même seed). Écart attendu pour une marche aléatoire, déjà noté dans le journal (critère C5, 3.7 points).
3. **Durée d'activation de Nav2** : environ 12 s (JOURNAL, premier run B) contre 10 à 17 s (JOURNAL, correctif de course).
   Compatible, formulations différentes.

Nombre de tests : 39 fonctions de test comptées dans `src/aspi_bot/test/` (11 + 20 + 8). L'exécution de `pytest` est à relancer
avant la soutenance (`cd ~/ros2_ws/src/aspi_bot && python3 -m pytest test/ -q`).

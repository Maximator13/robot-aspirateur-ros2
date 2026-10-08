# Résultats : stratégie A (aléatoire) contre stratégie B (boustrophédon + Nav2)

Tous les chiffres viennent des CSV de `results/`, du résumé `results/summary.md` et du `docs/JOURNAL.md`.
Les figures et le tableau sont produits par `scripts/plot_results.py`.

## 1. Protocole appliqué

- **Monde** : `turtlebot3_world` (une seule pièce).
- **Départ** : (-2.0, -0.5), qui est aussi l'origine de la carte de référence.
- **Durée** : 600 s simulées par run.
- **Métrique commune** : le même nœud `coverage_tracker` pour A et B.
  - Dénominateur : un masque d'espace atteignable de 5564 cellules, soit 13.9 m².
  - Une cellule est couverte quand le robot passe à moins du rayon de nettoyage (disque).
  - La mesure démarre au premier déplacement du robot.
- **Vitesse d'avance identique** : 0.15 m/s pour A et B.
- **Stratégie A** : 3 runs, seeds 1, 2, 3, en mode **accéléré** (Gazebo sans limite de temps réel, sans fenêtres).
  - Ce mode a été validé par 5 critères fixés avant les runs (fréquences de `/scan` et `/cmd_vel`, vitesse moyenne, near_collisions, % final).
  - Les 5 critères sont satisfaits (`results/comparaison_vitesse/`). Les deux courbes, accélérée et temps réel, sont quasi superposées jusqu'à environ 5 min.
- **Stratégie B** : 3 runs, seeds 1, 2, 3, en **temps réel**, configuration Nav2 finale appelée T5.
  - Le mode accéléré a été testé et **invalidé** pour Nav2 (`results/comparaison_vitesse_B/`). Fréquence du contrôleur 4.42 Hz au lieu de 10 Hz, 8 waypoints atteints contre 69 en temps réel, 85 incidents contre 1.
  - Le critère « % final » seul paraissait bon (56.8 % contre 54.1 %). Il était trompeur : à 300 s, 53.6 % contre 29.0 %.
- **Comparaison** : en temps simulé. Chaque stratégie est mesurée dans un mode dont le comportement en temps simulé a été vérifié.

## 2. Résultats

### Figures

- `results/coverage_vs_time.png` : moyenne (trait épais), runs individuels (pointillés) et enveloppe min/max, par stratégie.
- `results/coverage_vs_time_runs.png` : un sous-graphe par stratégie, chaque run étiqueté par sa seed.

La seconde figure montre le run B3 : sa courbe devient plate à 17.2 %. Sur la première figure, il forme le bas de l'enveloppe de B.

### Tableau par run

| Stratégie | Seed | Durée | % final | % à 300 s | Temps pour 80 % | Distance (m) | near_collisions |
|---|---|---|---|---|---|---|---|
| A (RANDOM) | 1 | 600 s | 54.4 % | 24.8 % | non atteint | 71.9 | 24 |
| A (RANDOM) | 2 | 601 s | 55.5 % | 26.3 % | non atteint | 70.5 | 32 |
| A (RANDOM) | 3 | 601 s | 43.3 % | 31.7 % | non atteint | 70.0 | 21 |
| **A moyenne ± écart-type** | n=3 | | **51.0 ± 6.7 %** | 27.6 ± 3.6 % | non atteint | 70.8 ± 1.0 | 25.7 ± 5.7 |
| B (BOUSTROPHEDON) | 1 | 600 s | 59.8 % | 30.5 % | non atteint | 70.2 | 0 |
| B (BOUSTROPHEDON) | 2 | 600 s | 55.4 % | 30.6 % | non atteint | 62.2 | 2 |
| B (BOUSTROPHEDON) | 3 | 600 s | 17.2 % | 17.2 % | non atteint | 29.5 | 25 |
| **B moyenne ± écart-type (officielle, 3 runs)** | n=3 | | **44.1 ± 23.4 %** | 26.1 ± 7.7 % | non atteint | 54.0 ± 21.5 | 9.0 ± 13.9 |

L'écart-type est celui de l'échantillon (n-1).

**Information complémentaire** : 2 runs sur 3 terminés normalement (B1 et B2) : **57.6 % en moyenne**. Ce chiffre est donné à titre indicatif. Le résultat principal reste la moyenne à 3 runs.

### Lecture rapide

- **80 % n'est atteint par aucun run**, ni en A, ni en B. Le meilleur run est B1 avec 59.8 %.
- Autres seuils, à titre de repère : 50 % est atteint à 473 s par B1 et B2, à 566 s et 561 s par A1 et A2. A3 et B3 ne l'atteignent jamais.
- À 300 s, les moyennes sont proches : 27.6 % (A) contre 26.1 % (B).
- Distance : A parcourt environ 70 m dans chaque run. B1 et B2 en parcourent 70.2 et 62.2. B3 en parcourt 29.5 (bloqué).
- near_collisions : 25.7 en moyenne pour A. Pour B, 0 et 2 sur les deux runs normaux, 25 sur le run bloqué.

## 3. Décision méthodologique : le run B3 est conservé

Le run B3 s'arrête à 17.2 %. Sa couverture n'augmente plus après environ 158 s.

- **Cause observée** : à environ 135 s simulées, la TF `map → odom` vue par Nav2 reste figée, alors qu'AMCL continue de la publier (5 Hz, rosbag). Nav2 croit le robot immobile et enchaîne échecs de progression et recoveries.
- **Déjà vu** : en essai T1 et en mode accéléré.
- **Cause non identifiée** : charge CPU sous WSL, DDS ou buffer TF sont des pistes, aucune n'est vérifiée.
- **Décision de l'étudiant** : B3 reste dans la moyenne officielle (44.1 ± 23.4 %). La moyenne des 2 runs normaux (57.6 %) est indiquée à côté, comme information complémentaire.
- **Justification** : on n'écarte pas un résultat après l'avoir vu. Le blocage est une limite de fiabilité de la pile B dans notre environnement.

## 4. Interprétation (prudente)

- **Début de run** : les courbes A et B sont quasi superposées jusqu'à environ 7 min.
- **Fin de run** : sur ses deux runs complets, B passe devant (55.4 % et 59.8 %, contre 43.3 à 55.5 % pour A). L'écart apparaît tard dans le run.
- **Sécurité** : B fait nettement moins de near_collisions (0 et 2) que A (21 à 32). C'est cohérent avec une trajectoire calculée sur la carte et un évitement d'obstacles par Nav2. A ne réagit qu'au dernier moment.
- **Objectif non atteint** : aucune stratégie ne couvre 80 % en 10 min.
- **Pas de conclusion statistique ferme** sur le % final. Avec n = 3 et une dispersion de B de 23.4 points, les intervalles de A et B se recouvrent largement.
- **Régularité** : B1 et B2 ont des courbes presque identiques sur la majeure partie du run, car le trajet est planifié. A varie plus d'un run à l'autre en cours de route (par exemple à 420 s : 28.4 % pour A1 contre 40.3 % pour A3).
- **Reproductibilité (observation sur la figure `results/coverage_vs_time_runs.png`, 2 runs)** : quand Nav2 fonctionne, B1 et B2 sont quasi superposées jusqu'à environ 8 min, alors que les runs de A divergent dès environ 2 min. Le balayage est déterministe, l'aléatoire ne l'est pas. La variance de B vient de la fiabilité (B3), pas de la stratégie. Cela reste une observation sur deux runs, pas une démonstration.
- **Où B perd du temps** (analyse du journal, runs de réglage) :
  - rotations sur place : environ 18 % du temps (18 à 20 % selon les essais) ;
  - petits segments entre deux lignes de balayage, avec des arrêts d'environ 30 s ;
  - lignes de balayage coupées par les obstacles (le pilier), avec rotation puis contournement d'environ 13 s.
- **Ce que A fait gratuitement** : pas de carte, pas de localisation, pas de planification. Il dépend de moins de composants, donc de moins de pannes. Sur les runs officiels, un run sur trois de B s'est bloqué de cette façon. Aucun run de A n'est documenté comme bloqué.

## 5. Historique des réglages de B (démarche d'ingénierie)

Essais en temps réel. Un facteur modifié à la fois, mesuré séparément. Les essais T1 à T4 durent 300 s. T0 et T5 ont aussi un run de 600 s. T3 a un run de 600 s dans `results/comparaison_vitesse_B/`.

| Essai | Modification | % à 300 s | % à 600 s | Constat |
|---|---|---|---|---|
| T0 | config TurtleBot3 d'origine (DWB) | 19.5 % | 33.2 % | `loop_rate` à 2000 Hz, CPU saturé, blocages près du pilier et des murs |
| T1 | `loop_rate` du waypoint_follower à 20 | 18.2 % | | surcharge CPU supprimée, comportement inchangé |
| T2 | T1 + inflation 0.30 m, `cost_scaling` 10 | 21.9 % | | début plus rapide, mais blocage devant le pilier dès 177 s (DWB oscille) |
| T3 | contrôleur Regulated Pure Pursuit, 0.15 m/s, rotation 1.0 rad/s | 28.5 % | 54.1 % | plus de blocage, 1 near_collision à 300 s |
| T4 | T3 + contournements calculés par notre planner | 22.3 % | | **impasse** : 245 waypoints au lieu de 112, replanification à chaque but. Code conservé, désactivé |
| T5 | T3 + ralentissement d'approche réduit (0.2 m), pause aux waypoints à 0 | 30.6 % | 59.7 % | gain net, **configuration retenue** |

- T3 et T5 ont été comparés avec une seule seed chacun (seeds 1 et 5). La différence ne suffit pas à conclure statistiquement.
- Les runs officiels (seeds 1 à 3) sont refaits en configuration T5.
- Leçon : un réglage « officiel » peut contenir des valeurs inadaptées à la couverture. Les paramètres de sécurité de Nav2 sont pensés pour aller d'un point à un autre, pas pour longer les obstacles.
- Sources : `results/reglages_B/`, `results/comparaison_vitesse_B/`, `docs/JOURNAL.md`.

## 6. Limites

- **Peu de runs** : 3 par stratégie. Les écarts-types sont peu fiables. Aucun test statistique n'est proposé.
- **Une seule pièce** : `turtlebot3_world`, de 13.9 m² atteignables. Les résultats ne se généralisent pas à d'autres plans.
- **Odométrie parfaite en simulation** : A ne dérive pas. En conditions réelles, A serait mesuré avec une dérive, donc moins fiable. Le TF statique `map → odom` de A suppose cette absence de dérive.
- **Mesure de B sur la pose AMCL** : la position de B pour la couverture est estimée par AMCL, celle de A vient de l'odométrie simulée. Les deux sources n'ont pas la même erreur.
- **Modes de simulation différents** : A en accéléré, B en temps réel. Chaque choix est justifié par une validation, mais ce n'est pas le même banc.
- **Discrétisation** : la carte a des cellules de 5 cm. L'espacement effectif des lignes de balayage de B est de 0.20 m, pour 0.18 m demandé.
- **Blocage de la TF non diagnostiqué** : la cause du blocage de B3 est inconnue. Il peut se reproduire.
- **Blocages au démarrage de Nav2** : l'executor est resté bloqué au démarrage 2 fois sur 5 lancements avant correctif (journal). Le correctif est validé seulement par les runs officiels.
- **Facteur temps réel** (temps simulé / temps mural), mesuré sur les runs officiels : B1 0.91, B2 0.84, B3 0.94 (temps réel, donc inférieur à 1) ; A en mode accéléré ×2.84, ×3.06, ×3.08 (seeds 1, 2, 3). Un facteur inférieur à 1 en B peut jouer sur les cadences de Nav2.
- **Seeds de B** : le trajet planifié est le même d'un run à l'autre. Les différences entre runs de B viennent des aléas d'exécution (Nav2, AMCL, machine), pas d'un tirage aléatoire comme en A.

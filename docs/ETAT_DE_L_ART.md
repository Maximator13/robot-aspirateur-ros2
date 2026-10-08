# État de l'art : couverture de zone par un robot mobile

Les références sont numérotées [1] à [7] (section 5). Les affirmations tirées de ces sources sont
signalées par leur numéro. Les jugements propres au projet ne portent pas de numéro.

## 1. Le problème CCPP

Le Complete Coverage Path Planning (CCPP) consiste à trouver un trajet qui fait passer le robot
(ou son outil) sur chaque point de l'espace libre d'une zone [1][2].
Critères d'évaluation habituels :

- **Couverture** : part de l'espace libre effectivement passée.
- **Redondance (recouvrement)** : surface passée plusieurs fois.
- **Longueur du trajet et temps** : distance et durée pour atteindre la couverture visée.
- **Prérequis** : carte et localisation nécessaires ou non.

Deux revues de référence : Galceran & Carreras (2013) [1] et Choset (2001) [2].
Cette dernière classe les algorithmes en quatre familles : heuristiques, approximatives,
partiellement approximatives et décompositions cellulaires exactes [2].

## 2. Approches

### 2.1 Aléatoire / « bump and turn » (type Roomba)

- **Principe** : le robot avance tout droit, et change de direction (souvent aléatoire) quand il
  détecte un obstacle. Aucune carte, aucune localisation.
- **Source** : Jones (2006) [3] décrit la conception du Roomba. Il explique que le produit a réussi
  avec des composants courants et une complexité de système maîtrisée. Cet article est un retour
  d'expérience industriel : il ne fournit pas d'analyse de couverture.
- **Avantages** : très simple, peu coûteux, robuste, sans dépendance à la localisation.
- **Limites** : pas de garantie de complétude, forte redondance, temps de couverture élevé
  quand on vise les derniers pourcents. Ces deux points sont ce que nous mesurons ; nous ne les
  tirons pas d'une source.
- **Pour CE projet** : **retenu** comme stratégie A, la référence de comparaison. Implémentable en
  une journée, explicable en une phrase.

### 2.2 Spirale

- **Principe** : le robot décrit une spirale vers l'extérieur ou l'intérieur, jusqu'à rencontrer
  un obstacle. Les motifs en spirale sont classés parmi les méthodes de couverture dans la revue
  de Galceran & Carreras [1].
- **Avantages** : efficace dans une zone dégagée, sans carte.
- **Limites** : ne couvre pas à elle seule une pièce avec obstacles. Il faut un comportement de
  secours quand la spirale est bloquée.
- **Pour CE projet** : **non retenu**. Hors périmètre en 3 jours. Mentionné en perspective
  (variante « aléatoire + spirale »).

### 2.3 Boustrophédon et décomposition cellulaire

- **Principe** : le boustrophédon est un balayage en lignes parallèles, de sens alterné
  (« comme le bœuf qui laboure »). La décomposition cellulaire boustrophédon de Choset & Pignon [4]
  découpe l'espace libre en cellules sans obstacle interne. Chaque cellule est balayée
  en lignes. Le parcours des cellules est ensuite un problème de graphe d'adjacence [4].
- **Avantages** : couverture complète en théorie (sur carte connue), faible redondance, trajet
  prévisible.
- **Limites** : exige une carte et une bonne localisation. La décomposition complète
  (détection des points critiques, graphe de cellules, ordre de visite) est longue à implémenter
  et à tester.
- **Pour CE projet** : **retenu sous forme simplifiée** (stratégie B), voir section 4.

### 2.4 Spanning Tree Coverage (STC)

- **Principe** : Gabriely & Rimon [5][6] découpent la zone en cellules carrées de deux fois la taille
  de l'outil, chacune divisée en 4 sous-cellules à la taille de l'outil. Ils construisent un arbre
  couvrant du graphe des grandes cellules et le contournent. L'outil couvre la zone en suivant le
  tour de l'arbre [5][6].
- **Avantages** : méthode à grille, garanties théoriques décrites dans [5].
- **Limites** : travaille sur une grille alignée de cellules de deux fois la taille de l'outil. Le suivi
  du tour d'arbre impose beaucoup de virages. Nous ne l'avons pas implémentée : nos
  jugements sur ses limites pratiques restent à confirmer.
- **Pour CE projet** : **non retenu**. Elle demande une grille de cellules de deux fois la taille de l'outil
  (2 x 2 sous-cellules) et un suiveur de trajet à ce niveau de finesse. Nous préférons un balayage en lignes, plus
  lisible pour un jury.

### 2.5 Coverage server de Nav2 (opennav_coverage)

- **Principe** : serveur de tâche de couverture compatible Nav2, de Open Navigation LLC, financé
  et publié en open source avec Bonsai Robotics. Il s'appuie sur la bibliothèque Fields2Cover
  (Mier, Valente & de Bruin, IEEE RA-L 2023, voir [7]) pour générer en-têtes de champ (headlands), swaths,
  route et chemin [7]. Il prend en entrée un polygone ou des rangées annotées.
- **Compatibilité Humble** (vérifiée sur le dépôt GitHub open-navigation/opennav_coverage) :
  tag `v1.2.1` ou branche `humble-v2` pour Humble. Le paquet `ros-humble-fields2cover` en
  version 2.0.0 est annoncé disponible dans les paquets apt. Le README indique que l'API du
  navigateur peut changer et que les polygones non convexes, les trous (voids) font partie des
  objectifs non terminés.
- **Avantages** : solution outillée et maintenue, intégrée à Nav2.
- **Limites** : conçu pour des champs agricoles (polygones, GPS), pas pour une pièce
  extraite d'une `OccupancyGrid` avec piliers. Dépendance supplémentaire et configuration
  à comprendre, à compiler peut-être depuis les sources.
- **Pour CE projet** : **non retenu** : mauvaise adéquation à notre carte de pièce, risque
  d'intégration, et une boîte noire ne se défend pas devant un jury. Piste de perspective.

## 3. Tableau comparatif

Les colonnes « complétude » et « redondance » sont des appréciations qualitatives.

| Approche | Carte requise | Complétude garantie | Redondance | Complexité d'implémentation | Retenu |
|---|---|---|---|---|---|
| Aléatoire (bump and turn) | Non | Non (seulement en moyenne sur un long temps) | Élevée | Très faible | Oui (A) |
| Spirale | Non | Non | Faible en zone dégagée | Faible | Non |
| Boustrophédon simplifié (lignes sur grille érodée) | Oui | Non (les segments inaccessibles sont sautés) | Faible | Moyenne | Oui (B) |
| Décomposition cellulaire boustrophédon [4] | Oui | Oui, en théorie, sur carte exacte | Faible | Élevée | Non |
| Spanning Tree Coverage [5][6] | Oui | Oui, en théorie, sur grille de cellules | Faible | Moyenne à élevée | Non |
| opennav_coverage [7] | Oui (polygone) | Selon Fields2Cover | Faible | Moyenne (intégration) | Non |

## 4. Notre choix

- **Stratégie A (référence sans carte)** : bump and turn, avec graine aléatoire reproductible.
  Elle donne la borne basse à battre. Sa simplicité en fait le point de comparaison.
- **Stratégie B (planifiée)** : boustrophédon simplifié sur grille. Pas de décomposition
  cellulaire complète. On érode l'espace libre, on garde la composante connexe de départ, on
  trace des lignes horizontales à intervalle fixe, de sens alterné. Les extrémités de segments
  deviennent des waypoints. **Nav2 (`FollowWaypoints`) gère les transitions** entre lignes
  et l'évitement local. C'est ce qui dispense d'un graphe de cellules.
- **Limite assumée** : un pilier coupe une ligne en plusieurs segments, et les transitions
  entre segments passent par la planification de Nav2, sans optimisation de l'ordre de visite.
- **Avec plus de temps** : décomposition cellulaire boustrophédon complète [4] avec ordre de visite
  optimisé ; essai d'opennav_coverage [7] ; STC [5][6] pour comparer une couverture à grille ;
  variante aléatoire + spirale ; test sur robot réel.

## 5. Références

1. E. Galceran, M. Carreras, « A survey on coverage path planning for robotics »,
   *Robotics and Autonomous Systems*, vol. 61, n° 12, pp. 1258-1276, déc. 2013.
   DOI : 10.1016/j.robot.2013.09.004. (Vérifié : dépôts universitaires de Gérone et Recercat.)
2. H. Choset, « Coverage for robotics – A survey of recent results »,
   *Annals of Mathematics and Artificial Intelligence*, vol. 31, pp. 113-126, oct. 2001.
   DOI : 10.1023/A:1016639210559. (Vérifié : Crossref, fiche CMU Robotics Institute.)
3. J. Jones, « Robots at the tipping point: the road to iRobot Roomba »,
   *IEEE Robotics & Automation Magazine*, vol. 13, n° 1, pp. 76-78, 2006.
   DOI : 10.1109/MRA.2006.1598056. (Vérifié par recherche web : résumé et DBLP.)
4. H. Choset, P. Pignon, « Coverage path planning: the boustrophedon cellular decomposition ».
   Deux versions existent :
   - actes de la 1re conférence *Field and Service Robotics* (FSR '97), pp. 216-222, déc. 1997
     (vérifié : fiche CMU Robotics Institute, qui l'intitule « Coverage Path Planning: The
     Boustrophedon Decomposition ») ;
   - chapitre dans *Field and Service Robotics*, Springer London, 1998, pp. 203-209,
     DOI : 10.1007/978-1-4471-1273-0_32 (vérifié : Crossref). Le nom du directeur de l'ouvrage n'a pas été vérifié : non indiqué.
5. Y. Gabriely, E. Rimon, « Spanning-tree based coverage of continuous areas by a mobile robot »,
   *Annals of Mathematics and Artificial Intelligence*, vol. 31, n° 1-4, pp. 77-98, oct. 2001. DOI : 10.1023/A:1016610507833.
   (Vérifié : Crossref, DBLP.)
6. Y. Gabriely, E. Rimon, même titre, *Proc. 2001 IEEE International Conference on Robotics and
   Automation (ICRA)*, vol. 2, pp. 1927-1933, 2001. DOI : 10.1109/ROBOT.2001.932890.
   (Vérifié : Crossref, DBLP. Version conférence.)
7. Open Navigation LLC, dépôt `opennav_coverage`, https://github.com/open-navigation/opennav_coverage
   (consulté le 08/10/2026, licence Apache-2.0). Cite : G. Mier, J. Valente, S. de Bruin,
   « Fields2Cover: An Open-Source Coverage Path Planning Library for Unmanned Agricultural
   Vehicles », *IEEE Robotics and Automation Letters*, vol. 8, n° 4, pp. 2166-2172, avr. 2023.
   DOI : 10.1109/LRA.2023.3248439. (Vérifié : Crossref.)

### Points non vérifiés

- Nom du directeur de l'ouvrage Springer de [4] (1998).
- Attribution individuelle du code d'opennav_coverage à Steve Macenski : le README ne nomme que
  Open Navigation LLC et Bonsai Robotics, donc nous n'écrivons pas de nom d'auteur.
- Affirmations sur la spirale et le STC : les résumés de revue consultés ne détaillent pas
  leurs performances. À relire dans [1] avant la soutenance.

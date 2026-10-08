# Algorigrammes

Les slides ne contiennent pas de code : ces algorigrammes les remplacent.
Fidèles à `random_logic.py`, `random_walker_node.py`, `planning.py` et `coverage_tracker_node.py`.
Le planner (stratégie B) est décrit ici au niveau de `planning.py` ; le nœud `coverage_planner` s'y ajoute (voir ARCHITECTURE.md).

---

## 1. random_walker (stratégie A)

### 1.1 Distance frontale (à chaque message `/scan`)

```mermaid
flowchart TD
    A(["Message LaserScan reçu"]) --> B["meilleure distance = infini"]
    B --> C{"Reste-t-il un rayon à traiter ?"}
    C -- "non" --> Z(["distance frontale = meilleure distance"])
    C -- "oui" --> D["angle du rayon = angle_min + i x incrément<br/>normalisé dans -pi à +pi"]
    D --> E{"angle dans le secteur avant<br/>±30 degrés ?"}
    E -- "non" --> C
    E -- "oui" --> F{"mesure finie et comprise<br/>entre range_min et range_max ?<br/>exclut inf, nan, trop proche"}
    F -- "non" --> C
    F -- "oui" --> G["meilleure distance = minimum<br/>entre elle et la mesure"]
    G --> C
```

Le scan du TurtleBot3 va de 0 à 2π : l'avant est au début et à la fin du tableau.
La normalisation des angles dans [-π, π] gère ce cas. S'il n'y a aucune mesure valide, la distance vaut l'infini (voie libre).

### 1.2 Machine à états (timer à 10 Hz)

```mermaid
flowchart TD
    T(["Timer 10 Hz"]) --> H{"horloge simulée active ?<br/>temps différent de 0"}
    H -- "non" --> RIEN(["rien publié"])
    H -- "oui" --> I{"un scan déjà reçu ?"}
    I -- "non" --> STOP["publier vitesse nulle"]
    I -- "oui" --> S{"état courant"}
    S -- "FORWARD" --> B1{"distance frontale<br/>inférieure à 0.25 m ?"}
    B1 -- "non" --> FW["publier avance 0.15 m/s"]
    B1 -- "oui" --> TIRE["tirer un angle entre 90 et 180 degrés<br/>tirer un sens gauche ou droite<br/>fin de rotation = maintenant + angle / vitesse 1 rad/s<br/>état = TURN"]
    TIRE --> ROT["publier rotation sur place"]
    S -- "TURN" --> C1{"maintenant avant<br/>la fin de rotation ?"}
    C1 -- "oui" --> ROT
    C1 -- "non" --> D1{"distance frontale<br/>inférieure à 0.25 m ?"}
    D1 -- "oui, voie bloquée" --> TIRE
    D1 -- "non, voie libre" --> RET["état = FORWARD"]
    RET --> FW
```

- Deux états seulement : `FORWARD` et `TURN`.
- Le hasard vient d'un générateur local initialisé par `seed` : même graine, même suite de rotations.
- La rotation est temporisée (durée = angle / vitesse angulaire), sans odométrie. L'angle réel peut différer légèrement de l'angle tiré : sans importance pour une marche aléatoire.
- Si la voie est encore bloquée à la fin de la rotation, un nouveau tirage est fait.
- La commande est publiée sur `/cmd_vel` (`geometry_msgs/Twist`) à chaque tick.

---

## 2. Masque atteignable et boustrophédon (`planning.py`)

### 2.1 Masque atteignable

Utilisé par le planner (tracé) et par le tracker (dénominateur du pourcentage).

```mermaid
flowchart TD
    A(["OccupancyGrid : données, largeur, hauteur"]) --> B["redimensionner en grille lignes x colonnes<br/>ligne 0 = bas de la carte"]
    B --> C["cellule libre si valeur de 0 à 49<br/>obstacle si valeur de 50 ou plus<br/>inconnu -1 = obstacle"]
    C --> D["rayon d'érosion en cellules =<br/>arrondi sup de rayon robot + marge, divisé par la résolution<br/>0.105 + 0.05 sur 0.05 donne 4 cellules"]
    D --> E["érosion par un disque :<br/>une cellule reste libre si tout le disque est libre<br/>bords de la carte = obstacles"]
    E --> F{"cellule de départ libre<br/>après érosion ?"}
    F -- "oui" --> H["départ = cellule de départ"]
    F -- "non" --> G{"existe-t-il une cellule libre<br/>après érosion ?"}
    G -- "non" --> VIDE(["masque vide"])
    G -- "oui" --> G2["départ = cellule érodée libre<br/>la plus proche"]
    G2 --> H
    H --> I["parcours en largeur BFS<br/>4 voisins depuis le départ"]
    I --> Z(["masque atteignable = composante connexe du départ"])
```

- L'inconnu est traité comme obstacle : on ne nettoie pas ce qu'on ne connaît pas.
- L'érosion garantit que le centre du robot reste à distance des murs.
- La composante connexe élimine les zones libres inaccessibles depuis le départ.
- Sur la carte `world` : 5564 cellules atteignables, soit 13.9 m².

### 2.2 Balayage boustrophédon

```mermaid
flowchart TD
    A(["Masque atteignable, origine, résolution, espacement 0.18 m"]) --> B["espacement en cellules = 0.18 / résolution, arrondi, au moins 1"]
    B --> C{"le masque contient<br/>des cellules ?"}
    C -- "non" --> VIDE(["aucun waypoint"])
    C -- "oui" --> D["lignes de balayage horizontales<br/>espacées d'une valeur constante<br/>bloc de lignes centré entre bas et haut de la zone"]
    D --> E["sens = gauche vers droite"]
    E --> F{"reste-t-il une ligne ?<br/>du bas vers le haut"}
    F -- "non" --> Z(["liste de waypoints x, y, yaw"])
    F -- "oui" --> G["découper la ligne en segments contigus<br/>de cellules atteignables"]
    G --> H{"la ligne a-t-elle<br/>au moins un segment ?"}
    H -- "non" --> F
    H -- "oui" --> I{"sens droite vers gauche ?"}
    I -- "oui" --> J["inverser l'ordre des segments"]
    I -- "non" --> K["garder l'ordre"]
    J --> L["pour chaque segment : waypoints aux deux extrémités<br/>un seul si le segment fait une cellule<br/>yaw = 0 vers +x, ou pi vers -x"]
    K --> L
    L --> M["inverser le sens<br/>pour la ligne suivante"]
    M --> F
```

- Les lignes sont centrées : l'excédent est réparti moitié en bas, moitié en haut. L'espacement reste constant et la bande du haut est couverte (correction du jour 1).
- Les waypoints sont les extrémités des segments seulement, orientés dans le sens de passage.
- Une ligne vide ne change pas le sens.
- Limite assumée : ce n'est pas une décomposition cellulaire de Choset. Quand un obstacle coupe une ligne, les segments sont enchaînés dans l'ordre. Le contournement est laissé au planificateur de Nav2.
- Sur la carte `world` : 112 waypoints.

---

## 3. coverage_tracker (mesure commune A et B)

```mermaid
flowchart TD
    T1(["Timer pose 10 Hz"]) --> A{"horloge active et<br/>carte reçue ?"}
    A -- "non" --> FIN1(["rien"])
    A -- "oui" --> B{"mesure terminée ?"}
    B -- "oui" --> FIN1
    B -- "non" --> C["lire la TF map vers base_footprint"]
    C --> D{"TF disponible ?"}
    D -- "non" --> FIN1
    D -- "oui" --> E{"masque déjà calculé ?"}
    E -- "non" --> F["masque atteignable depuis cette pose<br/>couverture vide<br/>mémoriser la pose de départ"]
    E -- "oui" --> G
    F --> G{"mesure démarrée ?"}
    G -- "oui" --> J
    G -- "non" --> H{"déplacement depuis le départ<br/>supérieur à 1 cm ?"}
    H -- "non, le robot n'a pas bougé" --> FIN1
    H -- "oui" --> I["début de la mesure :<br/>mémoriser le temps simulé<br/>ouvrir le CSV"]
    I --> J["distance = distance + déplacement depuis la dernière pose"]
    J --> K["marquer couvertes les cellules d'un disque de 0.09 m<br/>autour du robot, limité au masque atteignable"]
    K --> FIN2(["fin du tick"])

    S(["Message LaserScan"]) --> S1{"mesure démarrée<br/>et non terminée ?"}
    S1 -- "non" --> SF(["rien"])
    S1 -- "oui" --> S2["distance minimale valide sur 360 degrés"]
    S2 --> S3{"minimum inférieur à 0.15 m<br/>et le scan précédent<br/>ne l'était pas ?"}
    S3 -- "oui, front montant" --> S4["near_collisions + 1"]
    S3 -- "non" --> S5["mémoriser l'état proche ou non"]
    S4 --> S5

    P(["Timer publication 1 Hz"]) --> P1{"masque calculé et<br/>mesure non terminée ?"}
    P1 -- "non" --> PF(["rien"])
    P1 -- "oui" --> P2["publier /coverage_status<br/>et /coverage_map"]
    P2 --> P3{"mesure démarrée ?"}
    P3 -- "non" --> PF
    P3 -- "oui" --> P4["écrire une ligne dans le CSV"]
    P4 --> P5{"temps écoulé supérieur ou égal<br/>à run_duration ?"}
    P5 -- "non" --> PF
    P5 -- "oui" --> P6["journaliser la fin du run<br/>fermer le CSV<br/>cesser de mesurer"]
```

- Trois déclencheurs indépendants : la pose (10 Hz), le scan (5 Hz), la publication (1 Hz).
- Le pourcentage est le nombre de cellules couvertes dans le masque atteignable, divisé par la taille du masque.
- La mesure démarre au premier déplacement : le temps d'activation de Nav2 (stratégie B) n'est pas compté.
- La quasi-collision est comptée sur front montant : un passage sous le seuil compte pour un événement.
- Le seuil est de 0.15 m, car `range_min` du LiDAR (0.12 m) dépasse le rayon du robot (0.105 m).
- Le temps du run est le temps simulé.

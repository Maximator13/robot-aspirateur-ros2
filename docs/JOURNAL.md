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

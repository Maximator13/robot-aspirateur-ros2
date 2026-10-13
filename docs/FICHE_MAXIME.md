# Fiche express — mes slides (1, 2, 12, 13, 15, 16, 17, 22)

À relire juste avant de passer. Chaque slide : **ce que je dis** (à l'oral, court), **les chiffres**, **les questions pièges** avec la réponse.

---

## Le contexte du robot réel en 6 lignes (à connaître par cœur)

- TurtleBot3 **Burger** réel, LiDAR **LDS-02**, relié au PC par **Wi-Fi**. Les nœuds de calcul tournent sur le PC.
- Zone fermée en **carton**, environ **1,6 m²** à couvrir (620 cases de 5 cm), croix de départ au sol, même départ pour A et B.
- **Vitesse 0,10 m/s** (sécurité, au lieu de 0,15 en simulation), essais de **5 min**.
- **Localisation par les roues seules** (odométrie) : la transformation `map → odom` est **fixe**, pas d'AMCL.
- **Même nœud de mesure** (`coverage_tracker`) qu'en simulation, même zone à couvrir pour A et B.
- 2 essais A (graines 1 et 3) et 2 essais B valides, le 12/10. Un 3e essai B a eu un incident (bloqué contre un carton, 46,8 %), écarté.

---

## Slide 1 — Titre (10 s)

**Je dis** : « Notre question : un robot aspirateur qui planifie son trajet sur une carte nettoie-t-il mieux qu'un robot qui roule au hasard ? On compare deux stratégies, A au hasard et B planifiée. »

**Si on me demande « c'est quoi le sujet exact ? »** : le CCPP, *Complete Coverage Path Planning* : passer sur toute la surface libre d'une pièce.

## Slide 2 — Sommaire (15 s)

**Je dis** : « D'abord le problème et ce qui existe, puis nos deux stratégies. Ensuite trois bancs d'essai, toujours dans le même ordre, A puis B puis une conclusion : la simulation, le vrai robot, puis un jumeau numérique de la zone réelle. On finit par les limites et la suite. »

---

## Slide 12 — Le terrain réel (20 s)

**Je dis** :
- « Une zone fermée en carton, environ 1,6 m², une croix de départ au sol, la même pour A et B. »
- « Au centre : la carte et le **plan de B** : 7 lignes, donc 14 points de passage, les deux bouts de chaque ligne. »
- « À droite : RViz pendant un essai. Vert : le plan. Rose : ce qui est couvert. Rouge : ce que voit le LiDAR. »

**Question piège : « Pourquoi le LiDAR rouge est tourné par rapport aux murs ? »**
On n'utilise pas AMCL sur le vrai robot : la position vient **des roues seules**. Le robot n'est jamais posé exactement dans le même angle qu'à la cartographie, et les roues glissent un peu en tournant sur place. Le LiDAR voit les vrais murs, mais il est dessiné depuis une position un peu fausse, donc il paraît tourné. **3° d'erreur ≈ 5 cm d'écart à 1 m.** C'est une limite assumée (slide 21).

**« Pourquoi la croix de départ est hors de la zone beige ? »** La zone à couvrir exclut une bande de 20 cm le long des murs (marge de sécurité du planificateur). La croix est dans cette bande : le robot y entre d'abord.

**« Pourquoi 0,10 m/s ? »** Sécurité sur un vrai robot dans une petite zone.

---

## Slide 13 — A sur le vrai robot (25 s)

**Je dis** : « A monte par paliers : **73 et 75 %** en 5 min, jamais 80 %. Il roule environ **20 m**. Les plateaux, par exemple entre 50 et 100 s : il roule, mais ne gagne rien. Il repasse où il est déjà passé, et il longe les murs, dans la bande de 20 cm que la mesure ne compte pas. »

**Chiffres** : à 2 min, 36 % et 30 %. Distance 19,7 et 20,9 m. Obstacles frôlés : 21 et 19.

**« Les plateaux, il est bloqué ? »** Non : entre 50 et 100 s il roule environ 2,5 m. Sur tout l'essai, **environ 60 % de sa distance est faite sans gain** de surface.

**« Pourquoi il longe les murs ? »** On l'a vu pendant l'essai. A ne tourne que quand un obstacle est à moins de 25 cm devant lui (cône de ±30°) : de côté, il peut frôler un mur longtemps.

**« Pourquoi les graines 1 et 3 ? »** Ce sont les deux essais A faits pendant la séance du 12/10 ; la graine fixe la suite des angles tirés, pour qu'un essai soit reproductible.

---

## Slide 15 — Notre solution : le suiveur (35 s)

**Je dis** :
- « Nav2 ne faisait pas avancer le vrai robot. Plutôt que de s'acharner, on a gardé **exactement le même plan** et changé seulement celui qui conduit. »
- « Le cadre pointillé, c'est ce que lance `aspi_real_follow.launch.py` : `coverage_planner` publie le plan sur `/coverage_path`, notre nœud **`coverage_follower`** le lit et publie directement `/cmd_vel` vers le robot. »
- « Pour chaque point : s'il est mal orienté de plus de 20°, il tourne sur place ; sinon il avance en corrigeant son cap ; à moins de 8 cm du point, il passe au suivant. »
- « Écarts possibles : il n'évite pas les obstacles (il s'arrête), sa position dérive, il saute un point au bout de 40 s, et ce n'est pas le même conducteur qu'en simulation. »

**Les réglages, si on creuse** : 0,10 m/s en avance, 0,6 rad/s en rotation ; seuil d'orientation 20° (0,35 rad), et 40° une fois lancé, pour ne pas hésiter à cause du retard Wi-Fi ; ralentit sur les 20 derniers cm ; pause si obstacle à moins de 15 cm devant ; arrêt si plus de LiDAR ou de position depuis 1 s.

**« Ce n'est pas tricher par rapport à la simulation ? »** La **planification** (ce qu'on compare) est identique. Le conducteur est différent, on le dit sur la slide : la comparaison réelle n'oppose pas les mêmes exécutants qu'en simulation.

**« Pourquoi il marche alors que Nav2 non ? »** Il n'a pas besoin d'AMCL ni de la position recalée : il utilise les roues, qui répondent sans le retard de 27 s. Chaque action (tourner, avancer) se vérifie à l'œil.

**« C'est testé ? »** La logique de cap est dans un module Python sans ROS, testé par pytest (107 tests au total dans le projet).

---

## Slide 16 — B sur le vrai robot (30 s)

**Je dis** : « Avec le suiveur, B fait ce que son plan prévoit : il passe **80 % en 125 et 134 s**, et finit son trajet vers 2 min 30 à **98 et 96,5 %**, en roulant **10 m**. » Puis lancer la vidéo.

**Chiffres** : à 2 min, 79 % et 75 %. Distance 9,8 m. Obstacles frôlés : 8 et 2. Le 2e essai a été arrêté à la main à 170 s, le trajet était fini.

**« Pourquoi pas 100 % ? »** Explication probable, non mesurée : quelques coins de la zone ne sont pas atteints par le disque de nettoyage (10 cm de rayon) depuis les lignes, et la position estimée par les roues dérive un peu.

**« Et le 3e essai ? »** Incident : des points sautés contre un carton, couverture figée à 46,8 %. Écarté des résultats, mais c'est une limite de fiabilité (1 incident sur 3).

---

## Slide 17 — Conclusion du robot réel (30 s)

**Je dis** :
- « B atteint 80 % en 2 min avec 10 m ; A ne l'atteint jamais en 5 min, avec 20 m. »
- « Pourquoi c'est plus net qu'en simulation : la zone est petite, le plan se finit en 2 min 30, et le suiveur ne perd pas de temps en arrêts comme Nav2. »
- « **Mais le résultat est discutable** : 2 essais seulement, une petite zone, et une position estimée par les roues, sans recalage LiDAR. D'où le jumeau numérique. »

**« Votre conclusion tient avec 2 essais ? »** Non, pas statistiquement. L'écart est grand (80 % en 2 min contre jamais en 5) et cohérent avec la simulation et le jumeau, mais ce sont des indices, pas une preuve.

**« La mesure par les roues fausse-t-elle la comparaison ? »** Elle touche A et B pareil, et plus A, qui tourne beaucoup. Le jumeau (position parfaite) donne pour B le même comportement (93 %, 9,7 m), donc le résultat de B ne semble pas venir d'une erreur de position.

---

## Slide 22 — Conclusion générale (35 s)

**Je dis** : « Notre réponse : **oui, planifier aide**, à condition que le robot sache suivre le plan. En simulation, Nav2 perdait du temps et se bloquait 4 fois sur 7 ; sur le vrai robot, il ne roulait pas ; avec un conducteur simple, B a nettement battu A. »

**Les 4 prochaines étapes** (chacune estimée, pas mesurée, à 0,5–1 jour) :
1. Corriger notre mesure : ignorer une position impossible (au-delà de 0,5 m/s). On a vu des « sauts » de 465 m en 10 min sur des essais bloqués.
2. Recaler la position du vrai robot avec le LiDAR (AMCL), une fois le retard réglé.
3. Moins de rotations sur place (environ 18 % du temps de B en simulation).
4. Un tour le long des murs pour nettoyer la bande de 20 cm.

Finir par : « Merci, nous sommes prêts pour vos questions. »

---

## Les questions qu'on va forcément me poser

| Question | Réponse courte |
|---|---|
| Pourquoi pas Nav2 sur le robot ? | La position d'AMCL arrivait à Nav2 avec **27 s de retard** : Nav2 croyait le robot là où il était 27 s avant et disait « arrivé » sans qu'il bouge (vu sur l'odométrie). Sans AMCL, il pivotait sans avancer. Horloge recalée (462 ms → 30–60 ms), Wi-Fi vérifié (0,26 s de retard des messages), Nav2 réglé : cause exacte non trouvée. |
| C'est quoi AMCL ? | L'outil de localisation du cours : il compare ce que voit le LiDAR à la carte et en déduit où est le robot (transformation `map → odom`). |
| Pourquoi pas AMCL avec le suiveur ? | AMCL figeait la position avec 27 s de retard ; le suiveur n'en avait pas besoin. Recaler avec le LiDAR est notre perspective n°2. |
| Comment savez-vous que le robot a vraiment bougé ? | On mesure son déplacement sur `/odom` (les roues), indépendamment de ce que dit Nav2. C'est comme ça qu'on a vu le faux « arrivé ». |
| Comment avez-vous fait la carte réelle ? | En téléguidant le robot dans la zone avec l'outil de cartographie du cours (procédure dans JOUR_ROBOT, section 8 : vérifie que c'était bien Cartographer, c'est toi qui l'as faite), puis `map_saver`. La carte est servie par `map_server`. |
| La comparaison A/B est-elle équitable ? | Même nœud de mesure, même zone à couvrir (même calcul que le planificateur), même départ, même vitesse, même durée. |
| Pourquoi 20 cm aux murs ? | Marge de sécurité : rayon du robot 10,5 cm + 5 cm, arrondi à 4 cases de 5 cm = 20 cm. Cette bande n'est comptée ni pour A ni pour B. |
| Pas d'enregistrement des essais réels ? | Non, pas de rosbag en réel : c'est une limite. On ne peut pas rejouer la trajectoire réelle. |

**Les chiffres à avoir en tête** : réel A 73–75 % en 5 min, 20 m ; réel B 98 / 96,5 %, 80 % en 2 min, 10 m ; simulation A 52 % (6 essais), B réussi 59 % (3 sur 7), B bloqué 4 fois sur 7 ; jumeau A 83 %, B 93 %, Nav2 bloqué à 68 %.

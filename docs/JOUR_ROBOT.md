# Journée robot réel : guide pas à pas

Ce guide sert le jour où l'on travaille avec le vrai TurtleBot3 Burger, à l'école.
Les phrases sont courtes. Chaque étape dit où exécuter, quoi taper, ce qu'on doit voir, et quoi faire si ça échoue.

Légende des lieux d'exécution :

- **[WSL]** : terminal Ubuntu 22.04 sur le PC (WSL 2).
- **[PowerShell]** : PowerShell Windows. « Admin » = lancé en administrateur.
- **[Robot]** : session SSH sur le Raspberry Pi du robot.

Mentions utilisées :

- « **À vérifier** » : point non confirmé par une source officielle. Ne pas s'y fier sans test.

Principe de la journée : le robot ne fait tourner que le pilote bas niveau (`robot.launch.py` : moteurs, odométrie, LiDAR).
Tout le reste (nos nœuds, Nav2, Cartographer, RViz) tourne sur le PC. Les deux machines se parlent par DDS sur le réseau.
Donc : réseau, horloge et `ROS_DOMAIN_ID` doivent être corrects avant tout le reste.

**Faits constatés à la séance du 2026-10-09 (robot n°1)** :

- Le robot n°1 est un point d'accès Wi-Fi : réseau « turtlebot1 », IP du robot `10.42.0.1`, utilisateur SSH `turtle`, clé SSH du PC installée.
- `ROS_DOMAIN_ID=1` (pas 30), ROS 2 Humble, LiDAR **LDS-02**.
- Le robot n'a pas d'Internet et pas d'horloge sauvegardée : il repart en arrière à chaque extinction (incident 3 du journal).
- Les valeurs `ROS_DOMAIN_ID=30` et `LDS-01` des sections 2 à 5 ci-dessous sont des exemples : pour le robot n°1, utiliser 1 et LDS-02.
- Démarrage : toujours par `robot_check.sh` (section 4). Arrêt : section 6. Run B réel non résolu : section 12.

---

## 0. Avant de partir (ce soir)

À mettre dans le sac :

- [ ] PC portable, **chargeur du PC**.
- [ ] **Batterie du robot chargée** (et la deuxième si l'école en a une). Vérifier la charge avant de partir.
- [ ] **Chargeur de la batterie du robot**, au cas où.
- [ ] **Câble Ethernet** (+ adaptateur USB-Ethernet si le PC n'a pas de port RJ45).
- [ ] **Câble micro-USB / USB-C** pour le téléphone si besoin de le charger, et le **téléphone** avec le **partage de connexion** testé ce soir (nom du réseau et mot de passe notés).
- [ ] Rouleau de **scotch** (marque de départ au sol), **mètre ruban**, **carton** pour les murs, ciseaux.
- [ ] Une **multiprise**.
- [ ] Ce guide, **hors ligne** (copie sur le téléphone ou PDF) : le Wi-Fi de l'école peut manquer.
- [ ] Le workspace compilé et à jour : `cd ~/ros2_ws && colcon build --symlink-install` puis `git status` propre et commit fait.

Ce soir, **ne rien modifier** côté réseau (section 2) : c'est l'étudiant qui le fera, sur place.
Seule vérification utile ce soir, **[WSL]** :

```bash
printenv | grep -E "ROS|TURTLEBOT"
wsl.exe --version
```

Attendu : `ROS_DISTRO=humble`, `ROS_DOMAIN_ID=30`, `ROS_LOCALHOST_ONLY=1` (valeurs actuelles, à changer seulement le jour J, dans le terminal).
Si `wsl.exe --version` n'est pas reconnu : la version de WSL est ancienne, voir section 2.1.

---

## 1. Questions à poser au professeur

À poser dès l'arrivée. Noter les réponses dans le tableau.

| Question | Réponse |
|---|---|
| Adresse IP du robot ? | |
| Utilisateur et mot de passe SSH ? (`ssh <utilisateur>@<ip>`) | |
| Version de ROS sur le Raspberry Pi : **Humble** ? (sinon incompatibilité probable avec notre PC) | |
| Modèle de LiDAR : **LDS-01** ou **LDS-02** ? (variable `LDS_MODEL`) | |
| `ROS_DOMAIN_ID` utilisé par le robot ? (30 sur notre PC ; sinon on s'aligne) | |
| Réseau Wi-Fi utilisable ? Le **multicast** est-il autorisé ? Y a-t-il une **isolation des clients** ? | |
| Le robot est-il en Wi-Fi ou en Ethernet ? Peut-on le brancher en câble au PC ? | |
| OpenCR à jour (firmware compatible Humble) ? | |
| Peut-on modifier le Wi-Fi du Raspberry Pi (plan B, hotspot du téléphone) ? | |
| Peut-on corriger l'heure du robot (`sudo`) ? | |
| Où poser la zone, combien de temps, combien de batteries ? | |

Réponses connues pour le robot n°1 (séance du 2026-10-09) : IP `10.42.0.1` (point d'accès « turtlebot1 »), utilisateur `turtle`, ROS 2 Humble, LDS-02, `ROS_DOMAIN_ID=1`, pas d'Internet sur le robot, horloge non sauvegardée.

Si le prof ne sait pas pour le multicast ni pour l'isolation : on les teste soi-même (section 2.4).
Si l'OpenCR n'est pas à jour : ne pas le mettre à jour sans l'accord du prof. Noter l'impasse et passer au plan C.

---

## 2. Réseau PC (WSL 2) ↔ robot : procédure

**Rien de cette section n'a été appliqué.** C'est une procédure que l'étudiant exécute lui-même, sur place.

Pourquoi : par défaut WSL 2 est en mode NAT. Le PC Windows et WSL sont sur deux réseaux différents.
Le robot ne « voit » pas WSL, et la découverte DDS (multicast) ne traverse pas le NAT.
Le mode **mirrored** recopie les interfaces réseau de Windows dans WSL : WSL a alors l'IP du PC sur le réseau de l'école.

### 2.1 Prérequis (source : documentation Microsoft Learn, pages « Accessing network applications with WSL » et « Advanced settings configuration in WSL »)

- Windows 11 **22H2 ou plus récent**.
- Réglage `networkingMode` dans le fichier `.wslconfig`, section `[wsl2]`. Valeurs possibles : `none`, `nat`, `bridged` (déprécié), `mirrored`, `consomme`.
- Le mode mirrored apporte, selon Microsoft : le support du multicast, la connexion à WSL depuis le réseau local, la compatibilité VPN, IPv6.
- Le pare-feu Hyper-V est activé par défaut sur Windows 11 22H2+ avec WSL **2.0.9 ou plus récent**. Il filtre le trafic **entrant** vers WSL : c'est lui qui peut bloquer les réponses du robot.

Vérifier la version de WSL, **[PowerShell]** :

```powershell
wsl --version
winver
```

Attendu : une version de WSL affichée (≥ 2.0.9 conseillée) ; Windows 11 version 22H2 ou plus.
Si `wsl --version` est inconnu : mettre WSL à jour avec `wsl --update` (**[PowerShell]**, connexion Internet nécessaire). À vérifier : l'effet exact de cette commande sur votre version.

### 2.2 Activer le mode mirrored

ATTENTION : l'étape finale `wsl --shutdown` **coupe toutes les sessions WSL en cours** (Gazebo, nœuds, éditeurs). Sauvegarder et fermer le travail d'abord.

1. **[PowerShell]** : créer ou ouvrir le fichier :

   ```powershell
   notepad $env:UserProfile\.wslconfig
   ```

   Le fichier n'existe pas par défaut (source Microsoft). Notepad propose de le créer.
2. Y mettre exactement (si le fichier existe déjà, ajouter la ligne sous `[wsl2]` sans effacer le reste) :

   ```ini
   [wsl2]
   networkingMode=mirrored
   ```

3. **[PowerShell]** : redémarrer WSL :

   ```powershell
   wsl --shutdown
   ```

4. Attendre environ 8 secondes (règle Microsoft : la VM doit s'arrêter complètement), puis rouvrir Ubuntu.
5. Vérifier que WSL a bien l'IP du réseau de l'école, **[WSL]** :

   ```bash
   ip -br addr
   hostname -I
   ```

   Attendu : une adresse du même sous-réseau que Windows (ex. `192.168.x.x` ou `10.x.x.x`), et plus l'adresse `172.x.x.x` du NAT.
   Comparer avec `ipconfig` côté **[PowerShell]**.

Si l'IP reste en `172.x.x.x` : le fichier n'a pas été lu. Vérifier le nom (`.wslconfig`, pas `.wslconfig.txt`), l'emplacement (`%UserProfile%`), la section `[wsl2]`, et refaire `wsl --shutdown`.
Si WSL ne démarre plus ou n'a plus Internet : supprimer la ligne `networkingMode=mirrored` (ou le fichier), refaire `wsl --shutdown`. On revient au NAT. Noter l'impasse (plan C).

Retour arrière à la fin de la journée : même procédure, ligne retirée, puis `wsl --shutdown`.

### 2.3 Pare-feu Hyper-V (trafic entrant)

Sans cette règle, le robot peut envoyer ses paquets DDS sans que WSL les reçoive : `ros2 topic list` ne montre rien.
Source : page Microsoft « Accessing network applications with WSL », encadré sur le mode mirrored.

**[PowerShell Admin]** :

```powershell
Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
```

- `{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}` est l'identifiant de VM (« VMCreatorId ») de WSL, tel que donné par la page Microsoft ci-dessus.
- Cette commande autorise **tout** le trafic entrant vers WSL. À faire sur un réseau de confiance seulement. Pour l'annuler après la journée : même commande avec `-DefaultInboundAction Block`. **À vérifier** : la valeur par défaut d'origine sur votre machine (la relever avant, voir ci-dessous).
- Alternative plus fine (Microsoft) : `New-NetFirewallHyperVRule` avec `-VMCreatorId` et un protocole / des ports précis. Les ports DDS étant nombreux (UDP), l'autorisation globale est plus simple pour la journée.

Relever le réglage avant et après, **[PowerShell Admin]** :

```powershell
Get-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}'
```

**À vérifier** : cette commande « Get » n'a pas été confirmée sur la page lue (seule la commande « Set » y figure). Si elle échoue, passer.
Attendu après la modification : `DefaultInboundAction` affiché à `Allow`.

Si la commande est refusée (« accès refusé ») : relancer PowerShell **en administrateur**. Si le PC est géré par l'école (stratégie de groupe) et que c'est interdit : plan C.
Le pare-feu Windows classique (profil réseau « Public ») peut aussi bloquer le trafic. **À vérifier** : si besoin, passer le réseau en profil « Privé » dans les paramètres Windows.

### 2.4 Variables ROS pour la journée (sans toucher à `~/.bashrc`)

À faire dans **chaque** terminal **[WSL]** où l'on lance une commande ROS. Le fichier `~/.bashrc` n'est **pas** modifié : en ouvrant un nouveau terminal, les valeurs reviennent à celles de la simulation.

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=1         # robot n°1 : 1 (30 = valeur de la simulation)
export ROS_LOCALHOST_ONLY=0    # indispensable : 1 bloque tout le trafic hors du PC
export TURTLEBOT3_MODEL=burger
printenv | grep ROS
```

Attendu : `ROS_DOMAIN_ID=<celui du robot>`, `ROS_LOCALHOST_ONLY=0`, `ROS_DISTRO=humble`.
Si le robot utilise un autre domaine : remplacer 30 par sa valeur **dans les deux machines de la même façon**.
Piège constaté (incident 1) : un onglet gardait les variables de la simulation, et la téléopération n'avait aucun effet. Vérifier `printenv | grep ROS` dans **chaque** onglet.
Astuce : écrire ces lignes dans un fichier à part, par exemple `~/jour_robot.env`, et faire `source ~/jour_robot.env` dans chaque terminal. Ne pas l'ajouter au `.bashrc`.

Avant de tester, arrêter tout nœud de simulation encore actif (`ps aux | grep -E "gz|ros"`) : un vieux Gazebo pollue `ros2 topic list`.

### 2.5 Test de connexion

Dans l'ordre. Ne pas passer à l'étape suivante si une étape échoue.

**a) Ping du robot, [WSL]** :

```bash
ping -c 4 <IP_ROBOT>
```

Attendu : 4 réponses, 0 % de perte.
Si échec :
- PC et robot sont-ils sur le **même sous-réseau** ? (comparer `hostname -I` et l'IP du robot).
- Isolation des clients du Wi-Fi (le routeur interdit PC ↔ robot) : essayer le câble Ethernet direct ou le plan B.
- Tester aussi le ping depuis **[PowerShell]** (`ping <IP_ROBOT>`) : s'il marche côté Windows mais pas côté WSL, le mode mirrored n'est pas actif (2.2) ou le pare-feu bloque (2.3).

**b) SSH, [WSL]** :

```bash
ssh <utilisateur>@<IP_ROBOT>
```

Attendu : demande de mot de passe, puis l'invite du Raspberry Pi.
Si « Connection refused » : le service SSH n'est pas démarré sur le robot (demander au prof). Si « timed out » : retour au ping.

**c) Multicast, deux terminaux.**
Terminal 1 **[Robot]** (en SSH) :

```bash
source /opt/ros/humble/setup.bash
ros2 multicast receive
```

Terminal 2 **[WSL]** :

```bash
ros2 multicast send
```

Attendu : le récepteur affiche un message reçu de l'IP du PC. Refaire dans l'autre sens (receive sur WSL, send sur le robot).
Si rien n'arrive dans un sens ou dans l'autre : multicast bloqué (routeur) ou pare-feu entrant (2.3). La découverte DDS automatique échouera. Aller au plan B (hotspot) puis C.

**d) Découverte ROS 2.**
Sur le robot, le pilote doit tourner (section 4). Puis **[WSL]** :

```bash
ros2 topic list
```

Attendu : on voit au minimum `/scan`, `/odom`, `/cmd_vel`, `/tf`, `/imu`.
Si seuls `/parameter_events` et `/rosout` apparaissent :
1. `ROS_DOMAIN_ID` différent entre les deux machines (`printenv | grep ROS` des deux côtés).
2. `ROS_LOCALHOST_ONLY=1` encore actif côté PC (ou côté robot : le vérifier en SSH).
3. Multicast bloqué (test c).
4. `ros2 daemon stop` puis `ros2 topic list` (le démon garde parfois un état ancien).

### 2.6 Plan B : partage de connexion du téléphone

À utiliser si le Wi-Fi de l'école bloque le multicast ou isole les clients. **Seulement si le prof autorise la modification du robot.**

1. Activer le partage de connexion sur le téléphone. Noter le nom et le mot de passe. Préférer la bande **2,4 GHz** (le Raspberry Pi 3 ne gère pas le 5 GHz ; **à vérifier** pour le modèle du robot).
2. Connecter le **PC Windows** au hotspot. Refaire 2.2 à 2.4 : l'IP de WSL (mirrored) doit changer pour celle du hotspot (`hostname -I`). Si besoin, `wsl --shutdown` puis rouvrir.
3. Connecter le **robot** au hotspot. Il faut un accès au Raspberry Pi : câble Ethernet vers le PC, ou écran + clavier (demander au prof). Sur Ubuntu Server, le Wi-Fi se règle avec netplan.

   **[Robot]** :

   ```bash
   ls /etc/netplan/
   sudo cp /etc/netplan/<fichier>.yaml ~/netplan_sauvegarde.yaml
   sudo nano /etc/netplan/<fichier>.yaml
   ```

   Le nom du fichier varie (ex. `50-cloud-init.yaml`). Le robot a une configuration existante ; en repartir. Structure générale d'un fichier netplan pour le Wi-Fi (**à vérifier** sur le robot : l'interface s'appelle souvent `wlan0`, l'indentation en espaces est obligatoire, pas de tabulations) :

   ```yaml
   network:
     version: 2
     wifis:
       wlan0:
         dhcp4: true
         access-points:
           "NOM_DU_HOTSPOT":
             password: "MOT_DE_PASSE"
   ```

   Appliquer :

   ```bash
   sudo netplan apply
   ip -br addr show wlan0
   ```

   Attendu : `wlan0` avec une adresse du hotspot (ex. `192.168.43.x` ou `172.20.10.x` ; la plage dépend du téléphone).
   Si erreur de syntaxe : restaurer la sauvegarde (`sudo cp ~/netplan_sauvegarde.yaml /etc/netplan/<fichier>.yaml`) puis `sudo netplan apply`. Si le robot ne se reconnecte pas : le rebrancher en câble et restaurer.
   **Avant de partir : remettre la configuration d'origine du robot** (même commande de restauration), sinon le robot ne se connecte plus au Wi-Fi de l'école pour les camarades.
4. Retrouver l'IP du robot :
   - dans les paramètres du téléphone : liste des appareils connectés au partage de connexion (nom d'hôte du robot et adresse) ;
   - ou depuis le robot connecté en câble / écran : `hostname -I` ;
   - ou **[WSL]** : `ping <nom_hote_robot>.local` (**à vérifier** : dépend de mDNS, souvent absent).
5. Refaire les tests de 2.5 (ping, SSH, multicast, `ros2 topic list`).

Limite connue : certains téléphones isolent aussi les clients, ou n'autorisent pas le multicast. Si c'est le cas : plan C.

### 2.7 Plan C : DDS ne passe pas

Si les tests 2.5 c et d échouent malgré les plans A et B :

1. Travailler **en SSH sur le robot** pour les tests de base : lancer `robot.launch.py`, puis dans un second SSH `ros2 topic hz /scan`, `ros2 topic echo --once /scan`, `ros2 run turtlebot3_teleop teleop_keyboard`.
2. Les nœuds de couverture (qui tournent sur le PC) ne pourront pas piloter le robot. Noter-le comme **impasse** dans le journal : symptôme, tests faits, hypothèse (multicast bloqué / pare-feu / isolation).
3. Piste à tester si le temps le permet : **Fast DDS Discovery Server** (la découverte passe par une adresse IP unicast, sans multicast). **À vérifier** : non testé dans ce projet ; la procédure exacte est dans la documentation ROS 2 Humble.
4. Piste alternative : exécuter `aspi_bot` directement **sur le robot** (copie du workspace). **À vérifier** : le Raspberry Pi est probablement trop lent pour Nav2 ; faisable seulement pour la stratégie A. Demander l'accord du prof.

---

## 3. Mise à l'heure

Pourquoi : si les horloges du PC et du robot diffèrent de plus de quelques dixièmes de seconde, TF affiche « extrapolation into the future/past » et Nav2 / Cartographer refusent de travailler. Les messages du robot sont horodatés avec **son** horloge.

Vérifier, deux terminaux côte à côte.

**[WSL]** :

```bash
date +"%F %T.%N"
```

**[Robot]** :

```bash
date +"%F %T.%N"
```

Attendu : écart de moins de 0,1 s (idéalement quelques ms). Ne pas comparer à l'œil : lancer les deux commandes à quelques secondes d'écart, ou utiliser `date +%s` des deux côtés et comparer.
Sur le robot, voir aussi l'état de la synchronisation :

```bash
timedatectl
```

Attendu : `System clock synchronized: yes`. (Ubuntu 22.04 utilise `systemd-timesyncd` par défaut ; **à vérifier** sur le robot.)

Corriger si l'écart est grand :

1. **Option 1 : synchronisation réseau.** Si le robot a Internet (ou un serveur NTP de l'école) : `sudo timedatectl set-ntp true`, attendre 1 minute, revérifier. **À vérifier** : sans accès Internet, cela ne fonctionne pas.
2. **Option 2 : chrony.** Le robot se cale sur le PC. Cela demande d'installer et de configurer `chrony` des deux côtés (`sudo apt install chrony` ; installation à faire par l'étudiant avec l'accord du prof ; configuration du serveur NTP sur le PC et du client sur le robot : **à vérifier**, non préparé ici). Option longue : à n'utiliser que si l'option 3 ne suffit pas.
3. **Option 3 : mise à l'heure manuelle, seulement si le prof l'autorise.** **[Robot]** :

   ```bash
   sudo timedatectl set-ntp false
   sudo date -s "AAAA-MM-JJ HH:MM:SS"
   ```

   Saisir l'heure affichée par `date` sur le PC (**[WSL]**) quelques secondes à l'avance. Vérifier l'écart ensuite. Cette méthode dérive avec le temps : revérifier dans l'après-midi.

Le fuseau horaire n'a pas d'importance (ROS utilise le temps epoch). Seul l'écart compte : comparer `date +%s`.

**Robot n°1 : c'est `robot_check.sh` qui s'en charge** (section 4). Il mesure l'écart par SSH ; au-delà de 300 ms, il demande le mot de passe sudo du robot et le remet à l'heure du PC. Il affiche ensuite « nouvel écart » (retard résiduel : un aller-retour Wi-Fi, 100 à 500 ms). Pour le run B, viser **moins de 100 ms** (section 12).

**Règle absolue : ne jamais remettre le robot à l'heure pendant que des nœuds tournent côté PC.** Voir section 12, étape 0.

---

## 4. Lancement du robot

### 4.0 Robot n°1 : procédure de démarrage (la seule à utiliser)

**[WSL]**, onglet normal (le script fixe lui-même `ROS_DOMAIN_ID=1` et `ROS_LOCALHOST_ONLY=0`) :

```bash
bash ~/ros2_ws/src/aspi_bot/scripts/robot_check.sh
```

Le script enchaîne :

1. Test de la connexion SSH **par clé** (sans mot de passe). Sinon : `ssh-copy-id turtle@10.42.0.1`, puis relancer.
2. Mesure de l'écart d'horloge PC-robot. Si l'écart dépasse 300 ms : mot de passe sudo du robot demandé, remise à l'heure, nouvel écart affiché.
3. Arrêt des anciens lancements sur le robot (évite deux bringups simultanés, incident 2).
4. Relance propre du bringup (journal sur le robot : `~/bringup.log`). Attente 15 s : calibration du gyroscope, **ne pas bouger le robot**.
5. Publication de la description du robot **par le PC** (`pc_robot_description.sh`, journal `/tmp/state_publisher.log`) : le `/tf_static` du robot se perd parfois sur le Wi-Fi (incident 7).
6. Vérification des topics `/cmd_vel`, `/odom`, `/scan`, `/battery_state` et de la TF `base_footprint -> base_scan`.

Attendu : quatre lignes `OK` pour les topics, `OK TF base_footprint -> base_scan`, et « Si tout est OK : ros2 run turtlebot3_teleop teleop_keyboard ».
Si `MANQUANT` : regarder `~/bringup.log` sur le robot (lignes `Run!`, `ERROR`, `LDS-02 started`), puis relancer le script.
Si la TF manque : lire `/tmp/state_publisher.log`.

Avant de lancer : **batterie supérieure à 11,3 V**. À 11,03 V (29 %), les moteurs se sont coupés alors que le LiDAR tournait encore (incident 6). `/battery_state` donne la tension : `ros2 topic echo --once /battery_state`.

### 4.1 Lancement manuel (secours, si `robot_check.sh` est inutilisable)

**[Robot]** (SSH ouvert sur le Raspberry Pi) :

```bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-02        # robot n°1 : LDS-02 (ou LDS-01 sur un autre robot)
export ROS_DOMAIN_ID=1         # robot n°1
export ROS_LOCALHOST_ONLY=0
printenv | grep -E "ROS|TURTLEBOT|LDS"
ros2 launch turtlebot3_bringup robot.launch.py
```

Attendu : des lignes de log sans erreur, notamment le démarrage du nœud du LiDAR (`ld08_driver` ou `hlds_laser_publisher`, selon le modèle), `turtlebot3_ros` (OpenCR) et `robot_state_publisher`. Le LiDAR se met à tourner (bruit de rotation).
**À vérifier** : les noms exacts des nœuds et le rôle de `LDS_MODEL` selon la version de `turtlebot3_bringup` installée sur le robot (documentation ROBOTIS de la branche Humble).

Laisser ce terminal ouvert pendant toute la journée. Il se coupe avec Ctrl+C.

Si échec :
- « package 'turtlebot3_bringup' not found » : `ROS_DISTRO` non chargé (`source /opt/ros/humble/setup.bash`) ou paquet absent. Demander au prof.
- Erreur de port série `/dev/ttyACM0` (OpenCR) ou `/dev/ttyUSB0` (LiDAR) : câble USB mal branché, ou droits. Vérifier avec `ls /dev/ttyACM* /dev/ttyUSB*`. Débrancher / rebrancher.
- Le LiDAR ne tourne pas : mauvaise valeur de `LDS_MODEL`. Essayer l'autre modèle. Vérifier le branchement USB.
- Erreur de firmware OpenCR ou pas d'odométrie : OpenCR non à jour. Ne pas flasher sans l'accord du prof. Noter-le.
- Le robot n'a plus de batterie : l'OpenCR clignote ou le robot s'éteint. Changer la batterie.

---

## 5. Test de `/scan` depuis le PC

**[WSL]**, après avoir fait la section 2.4 :

```bash
ros2 topic hz /scan
```

Attendu : environ **5 Hz** (LDS-01 ; **à vérifier** pour le LDS-02), régulier. Arrêter avec Ctrl+C.

```bash
ros2 topic echo --once /scan
ros2 topic info /scan --verbose
```

Attendu : un message `sensor_msgs/msg/LaserScan` avec `frame_id: base_scan`, et la liste `ranges`.
Relever dans le message : `range_min`, `range_max`, `angle_increment`. Les noter dans le journal.

- **LDS-01** : `range_min` ≈ 0,12 m.
- **LDS-02** : `range_min` ≈ 0,16 m. Dans ce cas, `near_collision_distance` de **0,20 m** (déjà prévu dans la configuration robot réel) est nécessaire : sinon la métrique near_collisions reste toujours nulle (même piège qu'au jour 1).

Voir aussi `ros2 topic hz /odom` (attendu : quelques dizaines de Hz) et `ros2 topic echo --once /odom`.

Si `hz` n'affiche rien :
- `ros2 topic list` montre-t-il `/scan` ? Non → réseau (2.5 d). Oui mais aucun message → problème de **QoS** : le LiDAR publie en BEST_EFFORT. `ros2 topic hz` utilise une souscription compatible dans Humble ; si doute : `ros2 topic echo --qos-reliability best_effort /scan --once`.
- Le LiDAR ne tourne pas : voir section 4.

---

## 6. Téléopération et arrêt d'urgence

**Règles de sécurité, à lire avant de bouger le robot :**

- **Une main sur le clavier** en permanence.
- **Une personne prête à soulever le robot** (ou à couper son alimentation), à moins d'un bras de lui.
- Toujours tester d'abord **sur un sol dégagé**, en vitesse lente.
- Ne jamais lancer un run si personne ne surveille le robot.

**[WSL]** :

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

Attendu : le menu de touches s'affiche (`w` avance, `x` recule, `a`/`d` tourne, `s` stop). Appuyer sur `w` une fois : le robot avance doucement.
Garder la vitesse basse (touche `x`/`z` pour diminuer ; **à vérifier** la liste exacte des touches affichées).
Si le robot ne bouge pas :
- `ros2 topic echo --once /cmd_vel` pendant qu'on appuie sur une touche : rien reçu côté PC → problème de terminal (le focus doit être sur le terminal du teleop).
- `/cmd_vel` publié mais le robot ne bouge pas : vérifier le réseau côté robot (`ros2 topic echo /cmd_vel` en SSH). Si rien : réseau (2.5). Si reçu : OpenCR (section 4).

**Arrêt d'urgence, dans l'ordre :**

1. **Ctrl+C** dans le terminal qui pilote le robot (teleop, launch du run). Les nœuds de ce projet envoient un arrêt à la fin (le `random_walker` publie une vitesse nulle ; l'executor annule le but).
2. **Toujours**, même si Ctrl+C semble avoir suffi, **[WSL]** :

   ```bash
   ~/ros2_ws/src/aspi_bot/scripts/stop_robot.sh
   ```

   Ce script force lui-même le domaine du robot (1) et `ROS_LOCALHOST_ONLY=0`. Il publie 10 vitesses nulles sur `/cmd_vel` (10 Hz) par **deux voies** : d'abord depuis le PC (en arrière-plan), puis **directement sur le robot via SSH**. Chaque voie est bornée dans le temps (5 s et 10 s) : le script ne bloque jamais. Si le SSH est impossible, il l'écrit et n'arrête que depuis le PC.
   Attendu : « stop_robot : commandes d'arrêt envoyées (ou expirées) ».
   Ne sert **pas** en simulation. Les scripts ne sont pas installés : le chemin est celui de `src/` (à défaut d'être exécutable : `bash ~/ros2_ws/src/aspi_bot/scripts/stop_robot.sh`).
3. **Vérifier que le robot est immobile** (regarder le robot ; `ros2 topic echo --once /odom` deux fois, la position ne change plus).
4. Si le robot continue à rouler : **le soulever**, puis **couper l'alimentation** (interrupteur de l'OpenCR). Ne pas se fier au logiciel.
5. Le TurtleBot3 **garde la dernière consigne de vitesse** reçue. Après la fin d'un run A, le `random_walker` publie une **vitesse nulle à 10 Hz** et **écrase toute téléopération** : le robot semble refuser de bouger. Faire **Ctrl+C** sur le launch avant de reprendre la main au clavier. Ne **jamais** tuer un nœud avec `kill -9` (ni fermer brutalement le terminal) pendant que le robot roule : plus personne n'envoie l'arrêt.
6. Test préalable obligatoire : lancer la téléop, faire avancer le robot, puis tester le script d'arrêt **une fois** pour s'assurer qu'il fonctionne avant tout run autonome.

**Limites de sécurité (à connaître avant tout run autonome) :**

- **(a) Perte du lien PC–robot.** Si le réseau tombe, aucun code côté PC ne peut arrêter le robot : il garde la dernière consigne reçue. Rester à portée, prêt à le soulever ou à couper l'alimentation.
- **(b) Angle mort du LiDAR.** Les obstacles à moins de `range_min` (≈ 0,12 m pour le LDS-01, ≈ 0,16 m pour le LDS-02) sont invisibles. À 0,10 m/s avec `stop_distance` de 0,25 m, le cas nominal (mur en face) est sûr. Ce n'est pas le cas d'un pied ou d'un objet bas qui arrive par le côté.
- **(c) Stratégie B.** Après Ctrl+C, une dernière consigne de Nav2 peut rester appliquée. Toujours lancer `stop_robot.sh`, puis vérifier que le robot est immobile.

---

## 7. Zone de travail

Plan principal : **des murs en carton**, posés pour fermer une petite zone sur un sol plat.

- Dimensions conseillées : **2 m × 2 m** (environ 4 m² ; en simulation, la pièce faisait 13,9 m² atteignables, donc la zone réelle est plus petite).
- Murs d'au moins **20 cm de haut**, **opaques** et mats (le LiDAR voit mal les surfaces très brillantes ou transparentes). Fixer au scotch pour qu'ils ne glissent pas quand le robot les touche.
- Fermer les angles (pas de trou entre deux cartons : le LiDAR verrait « à travers » et Nav2 y enverrait le robot).
- Éviter les obstacles dans la zone au premier essai ; en ajouter un (cube) si le temps le permet.
- Marquer **au sol, au scotch**, la **position de départ** et l'orientation du robot (une croix + une flèche). Le robot sera toujours replacé là.
- Mesurer et noter les dimensions réelles de la zone, pour le journal.

Option si on ne peut pas construire de murs fermés : limiter virtuellement la zone.

**Stratégie A, barrière virtuelle** (rectangle en repère odom, centré sur le départ). Le robot traite le bord comme un obstacle.

Argument `fence:="[xmin, ymin, xmax, ymax]"`, en mètres, **repère odom**. Par défaut `[]` : pas de barrière.
Sur le robot réel, l'odométrie vaut 0 au lancement du bringup sur le point de départ : le rectangle est donc **relatif au point de départ**.
La barrière est en repère odom : elle **glisse avec la dérive d'odométrie**. AMCL corrige `map → odom`, pas la barrière. Prévoir de la **marge par rapport aux murs**.
Sans `allowed_area` explicite, la zone mesurée reprend le rectangle `fence` (hypothèse : map ≈ odom au départ). Si le robot n'est pas parti exactement de la croix, cette hypothèse est fausse : donner `allowed_area` (repère map).
Comportement testé en simulation : le robot reste dans le rectangle, s'arrête environ 0,25 m avant le bord (`stop_distance`), dépassement maximal observé environ 0,13 m.

**[WSL]** (exemple : départ au centre d'une zone de 2 m × 2 m, rectangle volontairement plus petit que les murs) :

```bash
ros2 launch aspi_bot aspi_real_random.launch.py \
  map:=$HOME/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml \
  fence:="[-0.8, -0.8, 0.8, 0.8]" seed:=1
```

**Stratégie B, keepout filter** (masque d'interdiction dans Nav2, plus un rectangle autorisé pour le planner).

Règle impérative : la zone autorisée doit **contenir le point de départ (0, 0) avec au moins 0,5 m de marge** de chaque côté. Sinon le robot ne bouge jamais (collision détectée par le contrôleur dès le premier pas). Utiliser le **même rectangle** pour le masque et pour `allowed_area` (repère map).

1. Générer le masque, **[WSL]** (arguments : carte, xmin, ymin, xmax, ymax) :

   ```bash
   python3 ~/ros2_ws/src/aspi_bot/scripts/make_keepout_mask.py \
     ~/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml -0.8 -0.8 0.8 0.8
   ```

   Options : `--sortie DOSSIER` (défaut : dossier de la carte), `--nom` (défaut `keepout`), `--depart X Y` (défaut `0 0`), `--marge` (défaut `0.5` m).
   Attendu : `keepout.yaml/.pgm écrits dans ... : N cellules autorisées (... m2)`. Si le départ est à moins de 0,5 m du bord : message `ERREUR`, code de sortie 1, aucun fichier écrit. Agrandir le rectangle.
   Les valeurs négatives s'écrivent telles quelles (`-0.8`), sans `--` : vérifié (carré de ±0.8 m sur `world.yaml` → 1024 cellules autorisées). Aide : `python3 ~/ros2_ws/src/aspi_bot/scripts/make_keepout_mask.py --help`.
2. Lancer avec le keepout, **[WSL]** (le masque est écrit dans `src/` : passer son chemin absolu évite de recompiler) :

   ```bash
   ros2 launch aspi_bot aspi_real_planned.launch.py \
     map:=$HOME/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml \
     keepout:=true \
     keepout_mask:=$HOME/ros2_ws/src/aspi_bot/maps/keepout.yaml \
     allowed_area:="[-0.8, -0.8, 0.8, 0.8]" seed:=1
   ```

   `keepout` vaut `false` par défaut. `allowed_area` limite aussi le balayage et la mesure à ce rectangle.

Limite à noter : les murs en carton sont réels et visibles par le LiDAR (donc dans la carte). La barrière et le keepout sont des **secours** si la zone n'est pas fermée.

---

## 8. Carte de la zone (Cartographer, temps réel)

But : produire `zone_reelle.yaml` / `.pgm`, qui servira de **carte de référence** (vérité terrain pour la mesure, et carte de Nav2 pour la stratégie B).

Prérequis : le robot est lancé (section 4), `ros2 topic hz /scan` est correct, l'horloge est alignée (section 3).

1. Poser le robot **sur la croix de départ**, dans le bon sens (scotch). **Ce point sera l'origine de la carte.**
2. **[WSL]**, terminal avec les variables de la section 2.4 :

   ```bash
   ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=False
   ```

   Attendu : RViz s'ouvre (via WSLg), la carte apparaît autour du robot et grandit.
   Si RViz est noir ou la carte ne se construit pas : vérifier `ros2 topic hz /scan` et `ros2 run tf2_ros tf2_echo odom base_footprint` (la TF `odom → base_footprint` doit venir du robot).
   Si erreurs « extrapolation » dans le log : horloges non alignées (section 3).
3. Dans un second terminal, téléop **lente** (section 6). Faire un tour complet de la zone, en longeant les murs, vitesse faible, **sans rotation brusque**. Revenir au point de départ.
4. Contrôler dans RViz : murs fermés, pas de « fantômes » ni de murs doublés. Si la carte est déformée : tout recommencer (Ctrl+C, relancer Cartographer, repartir de la croix).
5. Sauvegarder, **[WSL]** (terminal avec les variables ROS) :

   ```bash
   ros2 run nav2_map_server map_saver_cli -f ~/ros2_ws/src/aspi_bot/maps/zone_reelle
   ```

   Attendu : « Map saved successfully » et deux fichiers `zone_reelle.yaml` et `zone_reelle.pgm`.
6. Vérifier l'image :

   ```bash
   ls -l ~/ros2_ws/src/aspi_bot/maps/
   cat ~/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml
   ```

   Ouvrir `zone_reelle.pgm` (ex. depuis l'explorateur Windows via `\\wsl.localhost\Ubuntu-22.04\home\maxime\ros2_ws\src\aspi_bot\maps\`). Nom de la distribution vérifié : `Ubuntu-22.04`.
   Attendu : zone fermée, blanc à l'intérieur, noir sur les murs, résolution 0,05 m, `origin` cohérente avec la position de départ.
7. Arrêter Cartographer (Ctrl+C), puis recompiler pour installer la carte :

   ```bash
   cd ~/ros2_ws && colcon build --symlink-install --packages-select aspi_bot
   source install/setup.bash
   ```

   (`setup.py` installe `maps/*.yaml` et `maps/*.pgm` dans `share/aspi_bot/maps`. Un fichier créé après le build n'est pas lié automatiquement : le build est donc nécessaire pour que `zone_reelle` soit trouvée. Même règle pour `keepout.yaml` : sinon passer son chemin absolu via `keepout_mask:=`.)

Le point de départ de la carte est l'origine `(0, 0)` utilisée ensuite par AMCL, le planner et l'executor (pose initiale (0, 0, 0) en dur).

Si la carte n'est pas exploitable après 2 essais : noter l'impasse (cause probable : vitesse trop élevée, murs trop bas ou brillants, odométrie qui dérive) et travailler avec la meilleure carte obtenue.

---

## 9. Runs : stratégie A puis stratégie B

Durée **courte** : **3 à 5 minutes** par run (contre 10 min en simulation). Noter la durée choisie : elle n'est pas comparable telle quelle aux chiffres de la simulation.

**Avant chaque run (liste de contrôle) :**

- [ ] Batterie **supérieure à 11,3 V** (`ros2 topic echo --once /battery_state`). À 11,03 V les moteurs se coupent alors que le LiDAR tourne : le run est alors invalide (incident 6).
- [ ] `robot_check.sh` passé avec succès (section 4.0), onglets avec `ROS_DOMAIN_ID=1`.
- [ ] Robot **replacé sur la croix**, **même orientation**, à chaque run. Sinon `map → odom` est faux et la mesure aussi.
- [ ] `ros2 topic hz /scan` et `/odom` corrects.
- [ ] Zone dégagée, murs en place, personne dans la zone.
- [ ] Une personne prête à soulever le robot ; une main sur le clavier (terminal du run, Ctrl+C prêt).
- [ ] Horloges alignées (section 3).
- [ ] Vitesses par défaut : 0,10 m/s d'avance (A : `forward_speed`, B : `desired_linear_vel`), 0,6 rad/s de rotation.
- [ ] **Enregistrer un rosbag à CHAQUE run** (obligatoire), dans un terminal à part avant le launch, nom de dossier différent à chaque run (il ne doit pas exister) :
  `ros2 bag record -o ~/ros2_ws/results/robot_reel/bag_A_seed1 /coverage_status /odom /tf` (arrêt par Ctrl+C après le run).
  Raison : sans rosbag, le run « complet » de la séance (RANDOM_2, 72,1 %) n'a pas pu être expliqué. Sa distance est restée figée à 11,94 m de 146,5 s à 300,5 s, et sa couverture figée aussi, alors que le LiDAR continuait. Il n'est valide que jusqu'à 146,5 s.
- [ ] Après le run, relire le CSV : la distance doit croître jusqu'à la fin. Sinon, le run n'est pas complet.
- [ ] Les CSV du robot réel vont dans `~/ros2_ws/results/robot_reel/` (argument `output_dir`) : ils ne se mélangent pas avec ceux de la simulation.
- [ ] Les durées par défaut sont de 300 s (`run_duration`, argument des deux launch). Un run B à 0,10 m/s couvre peu : en simulation, 12,2 % en 120 s (environ 22 s par waypoint). Des runs de 3 à 5 min donneront une couverture faible : c'est attendu, à noter.

### 9.1 Run A (aléatoire)

**[WSL]** :

```bash
ros2 launch aspi_bot aspi_real_random.launch.py \
  map:=$HOME/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml \
  seed:=1 run_duration:=300.0
```

Arguments utiles (valeurs par défaut) : `seed` (1), `run_duration` (300.0 s), `use_sim_time` (`false`, à laisser ainsi sur le robot), `localization` (`amcl`, repli `static`), `forward_speed` (0.10), `turn_speed` (0.6), `fence` (`[]`, voir section 7), `allowed_area` (`[]`, repère map), `near_collision_distance` (0.20), `use_rviz` (`true`), `output_dir` (`~/ros2_ws/results/robot_reel`).
Pour les runs 2 et 3 : `seed:=2`, `seed:=3`. Avec une barrière : ajouter `fence:="[-0.8, -0.8, 0.8, 0.8]"`.

Attendu : le robot avance doucement, tourne devant les obstacles, le tracker publie `/coverage_status` et écrit un CSV dans `~/ros2_ws/results/robot_reel/`. La carte de couverture se colore dans RViz.
Suivi : `ros2 topic echo /coverage_status` (type `aspi_interfaces/msg/CoverageStatus`).
Fin : arrêt automatique à la durée demandée (le walker publie alors une vitesse nulle à 10 Hz : Ctrl+C avant toute téléopération, section 6) ; sinon Ctrl+C, puis **toujours** `~/ros2_ws/src/aspi_bot/scripts/stop_robot.sh`, puis vérifier que le robot est immobile (section 6).
Si le robot ne bouge pas : `/scan` reçu ? `/cmd_vel` publié ? (`ros2 topic echo --once /cmd_vel`). Si le robot tourne sans fin : `/scan` vu comme obstacle partout (LiDAR bouché ou `range_min` mal géré).
Si la couverture reste à 0 % : TF `map → odom` absente ou fausse. Vérifier `ros2 run tf2_ros tf2_echo map base_footprint`.

### 9.2 Run B (planifiée)

Replacer le robot sur la croix, même orientation. Puis **[WSL]** :

```bash
ros2 launch aspi_bot aspi_real_planned.launch.py \
  map:=$HOME/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml \
  seed:=1 run_duration:=300.0
```

Arguments utiles (valeurs par défaut) : `seed` (1, numéro du run dans le nom du CSV), `run_duration` (300.0 s), `use_sim_time` (`false`), `nav2_params` (`config/nav2_params_real.yaml`, déjà la valeur par défaut : vitesse 0,10 m/s, pose initiale AMCL (0, 0, 0)), `keepout` (`false`), `keepout_mask` (`maps/keepout.yaml` installé), `allowed_area` (`[]`, repère map), `near_collision_distance` (0.20), `use_rviz` (`true`), `output_dir` (`~/ros2_ws/results/robot_reel`).
Avec keepout : voir la commande complète de la section 7 (rectangle autorisé avec au moins 0,5 m de marge autour du départ).
Fin : arrêt automatique à `run_duration` (l'executor s'arrête 10 s après) ; sinon Ctrl+C (l'executor annule le but), puis **toujours** `~/ros2_ws/src/aspi_bot/scripts/stop_robot.sh`, puis vérifier que le robot est immobile.

Attendu : Nav2 s'active (log « Nav2 actif »), le chemin de balayage apparaît dans RViz (`/coverage_path`), le robot suit les lignes.
En simulation, Nav2 mettait jusqu'à environ 90 s pour devenir actif. Si absent après 90 s : arrêter et relancer (piège connu).
**État au 2026-10-09 : le run B réel n'a pas abouti** (incident 10). Ne pas le lancer directement : suivre la section 12.
Si le robot ne démarre pas : la pose initiale d'AMCL est-elle bonne (robot sur la croix) ? Si AMCL est mal calée : utiliser le repli `localization:=static` (TF statique identité ; la dérive d'odométrie devient une limite à noter).
Si le robot touche un mur : Ctrl+C immédiat, puis `stop_robot.sh`. Noter la cause (carte, `inflation`, localisation).

**Après chaque run :** noter le nom du CSV produit et la durée, relever les observations (section 11), puis remettre le robot sur la croix.

---

## 10. Vidéo (optionnelle)

La vidéo n'a pas été faite en simulation (décision de l'étudiant). Sur le robot réel, une **courte vidéo au téléphone** (20 à 30 s, robot dans la zone + écran RViz si possible) reste possible **si l'école l'autorise** et si aucune personne n'est filmée sans accord.
Pas de montage prévu. Ne pas la filmer au détriment des runs : la prendre seulement si un run est déjà réussi.

---

## 11. À noter pour le journal

Ne rien reconstituer de mémoire le soir : noter **au fil de la journée**, dans `docs/JOURNAL.md` (format : date · contexte · options envisagées · choix · justification · résultat / leçon).

À relever systématiquement :

- **Réponses du prof** (section 1) : version ROS du robot, LiDAR, domaine, réseau.
- **Réseau** : le mode mirrored a-t-il marché du premier coup ? Quelle règle de pare-feu a été nécessaire ? Le multicast passait-il ? Quel plan (A, B, C) a finalement servi ?
- **Bugs et impasses**, chacun avec : symptôme, commande qui l'a montré, cause trouvée (ou hypothèse), correction, **leçon**. Une impasse documentée vaut des points.
- **Écart d'horloge** mesuré et correction faite.
- **Valeurs mesurées** : fréquence de `/scan` et `/odom`, `range_min` du LiDAR, dimensions réelles de la zone, vitesse réelle du robot (distance / temps).
- **Carte** : nombre d'essais, qualité, nombre de cellules libres atteignables (log du planner).
- **Pour chaque run** : stratégie, seed, durée, fichier CSV, % final de couverture, distance, near_collisions, incidents (collision, arrêt d'urgence, relance).
- **Comparaison avec la simulation** : écarts de comportement (patinage, bruit du LiDAR, dérive d'odométrie) et limites (une zone, peu de runs, durée courte). Ne pas conclure plus que ce que les chiffres montrent.
- **Remise en état** en fin de journée : `.wslconfig` (retour au NAT si besoin), règle de pare-feu Hyper-V (retour à l'état d'origine), configuration Wi-Fi du robot restaurée, variables ROS (le `.bashrc` n'ayant pas été modifié, rien à défaire).
- Commit git de la carte, des CSV et du journal.

---

## 12. Débloquer le run B (procédure de la prochaine séance)

**Problème (incident 10)** : Nav2 s'active, mais les transformations du robot arrivent trop vieilles (environ 2,4 s de retard sur l'horloge du PC, message `Transform data too old`). Nav2 déclare alors des waypoints atteints sans que le robot bouge : **14 waypoints « réussis » en 12 s, robot immobile**. Aucun run B réel n'est mesurable en l'état.

**Leçon** : le statut de Nav2 ne prouve pas le mouvement. Toujours vérifier l'odométrie.

Les `transform_tolerance` à 1,0 s de `nav2_params_real.yaml` (contrôleur, costmaps) sont un **contournement, pas une correction** : ils masquent un retard de 2,4 s, ils ne le suppriment pas. Avec ces tolérances, `bt_navigator` restait inactif (AMCL et la costmap locale : « timestamp earlier than all the data in the transform cache »).

Chaque étape : où, commande, attendu, si échec. Ne passer à la suivante que si l'étape est réussie.

### Étape 0. Règle : ne jamais remettre le robot à l'heure avec des nœuds actifs côté PC

Si on remet l'horloge du robot à l'heure alors que Nav2, AMCL ou le tracker tournent, leurs mémoires de transformations contiennent des données « du futur » : message `timestamp earlier than all the data in the transform cache`. Elles ne s'en remettent pas.

Règle : **horloge d'abord, nœuds du PC ensuite**. Si on a remis le robot à l'heure en cours de route : **tout arrêter et tout relancer côté PC** (Nav2, tracker, executor, RViz).

### Étape 1. `robot_check.sh` AVANT tout lancement côté PC

**[WSL]**, aucun nœud ROS du projet ne doit tourner :

```bash
bash ~/ros2_ws/src/aspi_bot/scripts/robot_check.sh
```

Attendu : ligne « écart PC - robot » **inférieure à 100 ms** (le script ne corrige qu'au-delà de 300 ms ; si l'écart est entre 100 et 300 ms, le relancer ne le change pas : voir étape 6), tous les topics et la TF en `OK`.
Si l'écart reste supérieur à 100 ms après remise à l'heure : le retard résiduel est celui d'un aller-retour Wi-Fi. Relancer le script (nouvelle remise à l'heure) ; noter les valeurs.
Si `robot_check.sh` échoue : section 4.0.

### Étape 2. Diagnostic `diag_b.sh` (sans `--sim`)

**[WSL]**, environ 40 s, lecture seule (il ne remet jamais le robot à l'heure) :

```bash
bash ~/ros2_ws/src/aspi_bot/scripts/diag_b.sh
```

Lancer de préférence Nav2 avant (étape 3), pour que le script voie l'état de Nav2 ; sans Nav2, l'étape Nav2 est ignorée.
Il mesure : écart d'horloge (seuil 100 ms), **âge de `/scan` et de `/odom` à l'arrivée sur le PC (seuil 0,3 s)**, fréquences (`/scan` ≈ 5 Hz, `/odom` ≈ 30 Hz), états lifecycle des nœuds Nav2, TF `map -> base_footprint` et `odom -> base_footprint`, charge CPU du PC et du robot (4 coeurs : plus de 3 = surchargé).
Verdict affiché, à lire ainsi :

| Verdict | Signification | Action |
|---|---|---|
| HORLOGE | écart d'horloge supérieur à 100 ms | `robot_check.sh`, puis relancer tous les nœuds du PC |
| RÉSEAU | robot injoignable, ou topics muets | Wi-Fi, alimentation, bringup, `ROS_DOMAIN_ID=1` |
| RÉSEAU/CPU | horloges proches, mais âge des messages supérieur à 0,3 s | rapprocher le PC du robot, fermer Gazebo et les applis lourdes |
| NAV2 | horloge et réseau corrects, Nav2 ou TF pas prêts | relancer Nav2, lire son log, vérifier la pose initiale |
| OK | tout semble sain | étape 3 |

Lecture : âge à peu près égal à l'écart d'horloge = problème d'horloge ; âge très supérieur = latence Wi-Fi ou CPU.
Si le verdict n'est pas OK : traiter la cause, puis refaire l'étape 2. Noter chaque écart et âge mesurés (matière de l'impasse, étape 7).

### Étape 3. Nav2 seul, UN objectif à 0,5 m

**[WSL]**, premier terminal : Nav2 avec la carte, **sans** nos nœuds de couverture (ni planner, ni executor, ni tracker). Les fichiers utilisés existent (vérifié), la commande n'a pas encore été essayée sur le robot réel :

```bash
ros2 launch nav2_bringup bringup_launch.py \
  map:=$HOME/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml \
  params_file:=$HOME/ros2_ws/install/aspi_bot/share/aspi_bot/config/nav2_params_real.yaml \
  use_sim_time:=false
```

Deuxième terminal, **[WSL]** :

```bash
rviz2 -d /opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz
```

Dans RViz : la pose initiale est normalement fixée par la config (`set_initial_pose: true`, pose (0, 0, 0) dans `nav2_params_real.yaml`). Si AMCL n'a pas la pose (robot mal placé sur la carte), utiliser « 2D Pose Estimate » sur la croix. Puis **un seul** « Nav2 Goal » à environ **0,5 m** devant le robot, dans la zone, loin des murs.
Attendu : le robot **se déplace réellement** d'environ 0,5 m et s'arrête.
Vérification obligatoire, deux fois à quelques secondes d'écart, **[WSL]** :

```bash
ros2 topic echo --once /odom --field pose.pose.position
```

La position doit avoir changé d'environ 0,5 m. Regarder aussi le robot.
Critère de réussite : le robot bouge réellement (odométrie avant/après), pas seulement le message de Nav2.
Fin du test : Ctrl+C dans les deux terminaux, puis `bash ~/ros2_ws/src/aspi_bot/scripts/stop_robot.sh`.
Si Nav2 annonce « objectif atteint » mais que l'odométrie n'a pas bougé : **c'est le défaut de l'incident 10**. Arrêter (Ctrl+C, `stop_robot.sh`), refaire les étapes 1 et 2, puis passer aux étapes 5 à 7.
Si le robot ne bouge pas et Nav2 n'est pas actif : `diag_b.sh` (étape 2), attendre jusqu'à 120 s.

### Étape 4. Run B court (120 s)

Seulement si l'étape 3 a réussi. Robot sur la croix, même orientation. **[WSL]** :

```bash
ros2 launch aspi_bot aspi_real_planned.launch.py \
  map:=$HOME/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml run_duration:=120.0
```

Lancer le rosbag avant (section 9), une main sur Ctrl+C, une personne près du robot.
Deux garde-fous de l'executor :

- **Détecteur de progression anormale** (`check_progress`, actif par défaut) : si des waypoints sont validés **en moins de 2 s** sans déplacement odométrique correspondant, le run est arrêté. **Code de sortie 1** et message dans le log. C'est exactement le faux succès de l'incident 10.
- **Délai d'attente de Nav2** (`nav2_timeout`, 120 s) : si Nav2 n'est pas actif au bout de 120 s, l'executor s'arrête avec le **code de sortie 2**. Relancer (arrêt propre avant, `stop_robot.sh`).

Attendu : « Nav2 actif », chemin de balayage dans RViz, robot qui suit les lignes, CSV dans `~/ros2_ws/results/robot_reel/`, distance croissante jusqu'à la fin.
Après : `stop_robot.sh`, vérifier l'immobilité, relire le CSV (distance en fonction du temps).
**Limite connue** : un échec Nav2 **rapide** (moins de 2 s, sans recoveries) sur deux waypoints de suite déclencherait aussi l'arrêt (code 1). Peu probable : les waypoints sont dans l'espace libre érodé.
Si code 1 : l'odométrie ne suit pas les consignes de Nav2. Retour aux étapes 1 et 2 ; essayer l'étape 5.
Si code 2 : relancer ; si ça se répète, étape 2 puis étape 6.

### Étape 5. Repli si AMCL pose problème : `localization:=static`

Nav2 **sans AMCL** : `map -> odom` est une transformation statique fixe (décalage `odom_x`, `odom_y`, à 0 sur le robot réel, car l'odométrie vaut 0 au lancement sur la croix).

```bash
ros2 launch aspi_bot aspi_real_planned.launch.py \
  map:=$HOME/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml \
  localization:=static run_duration:=120.0
```

Le paramètre `localization` est contrôlé : seules les valeurs `amcl` et `static` sont acceptées, une faute de frappe est refusée au lancement.

**Ne pas téléopérer ni déplacer le robot entre `robot_check.sh` et le launch en mode static.** `odom_x = odom_y = 0` suppose que le robot est sur la croix depuis le bringup. Sinon, relancer `robot_check.sh` (et le bringup, si le robot a bougé).

**Honnêtement** : le mode static supprime AMCL, mais pas un éventuel retard de `odom → base_footprint`. Si la cause est l'horloge du robot, static ne la corrige pas.

Résultat en **simulation** (pas sur le robot réel) : 14,6 à 14,8 % en 150 s avec `static`, contre 15,4 % avec AMCL : même ordre de grandeur.
**Limite** : la dérive d'odométrie n'est pas corrigée. Sur 2 m x 2 m et 2 à 5 min, la dérive reste probablement faible ; à mesurer, pas à supposer.
Dans ce mode, l'executor n'attend pas de pose initiale (`use_amcl` faux), et `diag_b.sh` attend 6 nœuds Nav2 actifs au lieu de 7.
Si ça ne change rien au retard des TF : l'AMCL n'est pas la cause. Étape 6.

### Étape 6. Si les transformations restent rejetées

Deux pistes, par ordre de coût. **À vérifier** : aucune n'a été essayée.

1. **Synchronisation propre de l'horloge avec chrony, le PC servant de serveur de temps.**
   - Sur le PC : `sudo apt install chrony` (**à lancer par l'étudiant** dans son terminal ; je ne le fais pas).
   - Sur le robot : installer et configurer chrony comme client du PC. **Demander l'accord du prof avant de configurer le robot.** La configuration exacte (serveur côté PC, autorisation du réseau du robot, client côté robot) est **à vérifier** dans la documentation de chrony.
   - Intérêt : le robot garde l'écart faible en continu, au lieu d'une remise à l'heure ponctuelle. Limite : cela corrige l'horloge, pas la latence Wi-Fi.
2. **Nav2 sur le Raspberry Pi du robot** : plus de transformations qui traversent le Wi-Fi pour la navigation. **À vérifier** : charge CPU du Pi (Nav2 y est probablement trop lourd, `diag_b.sh` affiche la charge du robot). Accord du prof nécessaire.

### Étape 7. Si rien ne marche en 1 h : impasse documentée

Ne pas s'acharner (règle du projet). Consigner dans `docs/JOURNAL.md` : écarts d'horloge mesurés (`robot_check.sh`), âges de `/scan`, `/odom` et des TF (`diag_b.sh`), verdicts, essais `localization:=static`, rosbags, pistes non testées (étape 6).
Conclusion à présenter : **le B réel reste un bonus**. La comparaison officielle A/B est celle de la **simulation**. Le run A réel (valide jusqu'à 146,5 s pour RANDOM_2) sert d'illustration.

---

## 13. Pièges d'environnement

- **Port de Gazebo occupé (WSL en réseau `mirrored`)** : en mode mirrored, WSL partage les ports de Windows. Une application Windows peut occuper le port de Gazebo, **11345** (constaté : Zwift). Gazebo ne démarre pas et affiche `bind: Address already in use`.
  - Contournement 1 : choisir un autre port **avant** le lancement, dans le terminal de Gazebo : `export GAZEBO_MASTER_URI=http://localhost:11350`.
  - Contournement 2 : fermer l'application Windows qui occupe le port.
  - Ce piège concerne la simulation, pas le robot réel.
- **Diagnostic en simulation** : `bash ~/ros2_ws/src/aspi_bot/scripts/diag_b.sh --sim`. Le mode `--sim` garde l'environnement ROS courant, saute le SSH (horloge, charge du robot) et l'âge des messages (les stamps sont en temps simulé : l'âge n'aurait aucun sens). Il vérifie les fréquences, l'état de Nav2 et les TF.
- **Deux modes de variables** : en simulation, `ROS_DOMAIN_ID=30` et `ROS_LOCALHOST_ONLY=1` ; sur le robot, `ROS_DOMAIN_ID=1` et `ROS_LOCALHOST_ONLY=0`. Les scripts du robot (`robot_check.sh`, `stop_robot.sh`, `diag_b.sh` sans `--sim`) forcent les valeurs du robot dans leur propre processus.

---

## Références vérifiées

- Microsoft Learn, « Accessing network applications with WSL » : <https://learn.microsoft.com/en-us/windows/wsl/networking> (mode mirrored, Windows 11 22H2+, multicast, commande `Set-NetFirewallHyperVVMSetting`, identifiant de VM WSL, pare-feu Hyper-V par défaut avec WSL 2.0.9+).
- Microsoft Learn, « Advanced settings configuration in WSL » : <https://learn.microsoft.com/en-us/windows/wsl/wsl-config> (fichier `%UserProfile%\.wslconfig`, section `[wsl2]`, clé `networkingMode`, `wsl --shutdown`, règle des 8 secondes).

Points repérés **à vérifier** (non confirmés par une source lue) : toutes les mentions marquées « À vérifier » ci-dessus, notamment les noms exacts des nœuds du bringup, le rôle précis de `LDS_MODEL`, la commande `Get-NetFirewallHyperVVMSetting`, le contenu exact d'un netplan Wi-Fi sur le robot, la configuration de chrony et le Fast DDS Discovery Server.

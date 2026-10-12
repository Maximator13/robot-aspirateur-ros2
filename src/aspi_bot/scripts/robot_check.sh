#!/usr/bin/env bash
# Relance propre du robot n°1 et vérification depuis le PC.
# Usage (onglet Ubuntu du PC) : bash ~/ros2_ws/src/aspi_bot/scripts/robot_check.sh
ROBOT=${ROBOT:-turtle@10.42.0.1}
ROBOT_DOMAIN_ID=${ROBOT_DOMAIN_ID:-1}
export ROS_DOMAIN_ID=$ROBOT_DOMAIN_ID ROS_LOCALHOST_ONLY=0
source /opt/ros/humble/setup.bash

echo "== 0a. Connexion SSH par clé (sans mot de passe)"
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$ROBOT" true 2>/dev/null; then
  echo "   la clé SSH n'est pas acceptée par le robot (ou robot injoignable)."
  echo "   PC bien sur le Wi-Fi du robot ? Puis : ssh-copy-id $ROBOT   et relance ce script."
  exit 1
fi

echo "== 0b. Heure du robot (pas d'horloge sauvegardée : elle repart en arrière à chaque extinction)"
# Écart SIGNÉ (PC - robot) en ms, mesuré au milieu de l'aller-retour SSH (latence compensée)
ecart_signe_ms() {
  local t0 r t1
  t0=$(date +%s%3N); r=$(ssh "$ROBOT" date +%s%3N); t1=$(date +%s%3N)
  echo $(( (t0 + t1) / 2 - r ))
}
abs() { echo ${1#-}; }
E=$(ecart_signe_ms)
[ -n "$E" ] || { echo "mesure d'heure impossible (SSH ?)"; exit 1; }
echo "   écart PC - robot : $(abs $E) ms"
if [ "$(abs $E)" -gt 100 ]; then
  # Mot de passe lu une fois, AVANT toute mesure (le temps de frappe ne fausse rien).
  read -rs -p "   heure à corriger. Mot de passe sudo du robot : " PW; echo
  for essai in 1 2 3; do
    E=$(ecart_signe_ms)
    # Correction relative appliquée PAR le robot à sa propre horloge : la durée du trajet
    # SSH n'entre plus dans l'heure réglée (contrairement à l'envoi d'une heure absolue).
    echo "$PW" | ssh "$ROBOT" "sudo -S -p '' date -s @\$(python3 -c 'import time; print(f\"{time.time() + $E / 1000:.3f}\")')" >/dev/null
    E=$(ecart_signe_ms)
    echo "   essai $essai : nouvel écart $(abs $E) ms"
    [ "$(abs $E)" -le 100 ] && break
  done
  unset PW
  [ "$(abs $E)" -le 100 ] || echo "   ATTENTION : écart encore > 100 ms (latence Wi-Fi irrégulière ?)"
fi

echo "== 1. Arrêt des anciens lancements sur le robot"
# Motifs à crochets ([t]urtlebot3_ros) : le shell distant contient lui-même la ligne de commande ;
# sans crochets, pkill -f se tuerait lui-même. « [t]x » correspond à « tx » mais pas à la chaîne « [t]x ».
ssh "$ROBOT" 'pkill -f "[t]urtlebot3_ros"; pkill -f "[l]d08_driver"; pkill -f "[r]obot_state_publisher"; pkill -f "[r]os2 launch turtlebot3_bringup"; sleep 2; pgrep -af "[t]urtlebot3_ros|[l]d08" || echo "plus rien ne tourne"'

echo "== 2. Relance du robot (journal sur le robot : ~/bringup.log)"
ssh "$ROBOT" "bash -ic 'export ROS_DOMAIN_ID=$ROBOT_DOMAIN_ID ROS_LOCALHOST_ONLY=0; nohup ros2 launch turtlebot3_bringup robot.launch.py > ~/bringup.log 2>&1 &'"
echo "   attente 15 s (calibration du gyroscope : ne pas bouger le robot)"
sleep 15
ssh "$ROBOT" 'grep -E "Run!|ERROR|LDS-02 started" ~/bringup.log'

echo "== 2b. Description du robot publiée aussi par le PC (/tf_static perdu sur le Wi-Fi sinon)"
# pkill -x (nom exact, tronqué à 15 caractères) : -f tuerait aussi ce script.
pkill -x robot_state_pub; sleep 1
nohup bash "$(dirname "$(readlink -f "$0")")/pc_robot_description.sh" > /tmp/state_publisher.log 2>&1 &
sleep 3

echo "== 3. Ce que voit le PC"
ros2 daemon stop >/dev/null 2>&1
sleep 3
timeout 15 ros2 topic list
for t in /cmd_vel /odom /scan /battery_state; do
  if timeout 15 ros2 topic list | grep -qx "$t"; then echo "OK       $t"; else echo "MANQUANT $t"; fi
done
timeout 6 stdbuf -oL ros2 run tf2_ros tf2_echo base_footprint base_scan > /tmp/tf_check.txt 2>&1
if grep -q Translation /tmp/tf_check.txt; then
  echo "OK       TF base_footprint -> base_scan"
else
  echo "MANQUANT TF base_footprint -> base_scan (voir /tmp/state_publisher.log)"
fi
echo "Si tout est OK : ros2 run turtlebot3_teleop teleop_keyboard"
echo "Pour arrêter le robot plus tard : ssh $ROBOT 'pkill -f [t]urtlebot3_bringup'"

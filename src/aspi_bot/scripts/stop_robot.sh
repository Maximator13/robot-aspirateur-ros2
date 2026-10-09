#!/bin/bash
# Arrêt d'urgence du robot RÉEL : publie une vitesse nulle sur /cmd_vel. Ne bloque jamais.
# Force ROS_LOCALHOST_ONLY=0 et le domaine du robot : ne sert PAS en simulation.
# 1) depuis le PC (en arrière-plan, plus rapide) ; 2) directement SUR le robot via SSH.
# Chaque voie est bornée par timeout.
# Usage : ~/ros2_ws/src/aspi_bot/scripts/stop_robot.sh
ROBOT=${ROBOT:-turtle@10.42.0.1}
ROBOT_DOMAIN_ID=${ROBOT_DOMAIN_ID:-1}
ZERO="{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=$ROBOT_DOMAIN_ID ROS_LOCALHOST_ONLY=0
timeout 5 ros2 topic pub -w 1 --times 10 -r 10 /cmd_vel geometry_msgs/msg/Twist "$ZERO" >/dev/null 2>&1 &
PC_PID=$!

timeout 10 ssh -o ConnectTimeout=3 -o BatchMode=yes "$ROBOT" \
  "source /opt/ros/humble/setup.bash; export ROS_DOMAIN_ID=$ROBOT_DOMAIN_ID; ros2 topic pub --times 10 -r 10 /cmd_vel geometry_msgs/msg/Twist '$ZERO'" \
  >/dev/null 2>&1 \
  || echo "SSH vers le robot impossible : arrêt depuis le PC seulement"
wait "$PC_PID"
echo "stop_robot : commandes d'arrêt envoyées (ou expirées)"

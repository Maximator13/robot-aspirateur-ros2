#!/bin/bash
# Arrêt d'urgence : publie une vitesse nulle sur /cmd_vel (10 messages à 10 Hz).
# Usage (après Ctrl+C du launch, environnement ROS 2 sourcé) :
#   ~/ros2_ws/src/aspi_bot/scripts/stop_robot.sh
ros2 topic pub --times 10 -r 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

#!/usr/bin/env bash
# Publie depuis le PC la description du TurtleBot3 burger (/tf_static : base_footprint ->
# base_link -> base_scan...). Le robot la publie aussi, mais une seule fois au démarrage,
# et elle se perd parfois sur le Wi-Fi (RobotModel rouge, AMCL figé). Valeurs identiques.
ROBOT_DOMAIN_ID=${ROBOT_DOMAIN_ID:-1}
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=$ROBOT_DOMAIN_ID ROS_LOCALHOST_ONLY=0
URDF=$(ros2 pkg prefix turtlebot3_description)/share/turtlebot3_description/urdf/turtlebot3_burger.urdf
# Comme le launch d'origine (turtlebot3_state_publisher.launch.py) : xacro avec namespace vide.
exec ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$(xacro "$URDF" namespace:=)"

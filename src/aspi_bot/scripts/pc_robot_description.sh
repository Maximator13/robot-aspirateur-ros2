#!/usr/bin/env bash
ROBOT_DOMAIN_ID=${ROBOT_DOMAIN_ID:-1}
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=$ROBOT_DOMAIN_ID ROS_LOCALHOST_ONLY=0
URDF=$(ros2 pkg prefix turtlebot3_description)/share/turtlebot3_description/urdf/turtlebot3_burger.urdf
exec ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$(xacro "$URDF" namespace:=)"

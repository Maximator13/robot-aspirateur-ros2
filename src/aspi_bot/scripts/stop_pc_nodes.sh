#!/usr/bin/env bash
NOEUDS="[r]os2 launch|[c]omponent_container|lib/rviz2/rviz2|lib/aspi_bot/|lib/nav2_|lib/tf2_ros/static_transform_publisher|lib/nav2_map_server/"
if ! pgrep -f "$NOEUDS" >/dev/null; then
  echo "aucun nœud ROS ne tourne sur le PC"
  exit 0
fi
echo "arrêt de :"; pgrep -af "$NOEUDS" | cut -c1-100
pkill -TERM -f "$NOEUDS"
for i in 1 2 3 4 5 6 7 8 9 10; do pgrep -f "$NOEUDS" >/dev/null || break; sleep 1; done
pkill -KILL -f "$NOEUDS" 2>/dev/null
sleep 1
if pgrep -f "$NOEUDS" >/dev/null; then
  echo "ATTENTION : encore actifs :"; pgrep -af "$NOEUDS" | cut -c1-100
else
  echo "tous les nœuds ROS du PC sont arrêtés"
fi

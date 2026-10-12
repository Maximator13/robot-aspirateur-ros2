#!/usr/bin/env bash
# Déblocage du run B sur le robot réel, en UNE commande et dans le bon ordre :
#   1. robot_check (horloge, bringup, description du robot) AVANT tout nœud côté PC ;
#   2. Nav2 seul (carte réelle) ; 3. diag_b ; 4. un objectif, mouvement vérifié sur /odom.
# Tout est enregistré dans results/robot_reel/debloque_<date>.log.
# Usage : PC sur le Wi-Fi du robot, robot sur la croix, AUCUN autre onglet ROS ouvert :
#   bash ~/ros2_ws/src/aspi_bot/scripts/debloque_b.sh            (Nav2 avec AMCL)
#   bash ~/ros2_ws/src/aspi_bot/scripts/debloque_b.sh static     (repli : Nav2 sans AMCL)
#   bash ~/ros2_ws/src/aspi_bot/scripts/debloque_b.sh static nocoll   (+ sans détection de collision RPP)
MODE=${1:-amcl}
S=$(dirname "$(readlink -f "$0")")
WS=$HOME/ros2_ws
CARTE=$WS/src/aspi_bot/maps/zone_reelle.yaml
PARAMS=$WS/install/aspi_bot/share/aspi_bot/config/nav2_params_real.yaml
if [ "${2:-}" = nocoll ]; then
  # Essai : RPP sans « collision ahead » (le planner global évite toujours les murs de la carte).
  # Copie hors dépôt, la config officielle n'est pas modifiée.
  sed 's/use_collision_detection: true/use_collision_detection: false/' "$PARAMS" > "$HOME/nav2_params_real_nocoll.yaml"
  PARAMS=$HOME/nav2_params_real_nocoll.yaml
fi
LOG=$WS/results/robot_reel/debloque_$(date +%Y%m%d-%H%M%S)_$MODE${2:+_$2}.log
mkdir -p "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1
source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"
export ROS_DOMAIN_ID=${ROBOT_DOMAIN_ID:-1} ROS_LOCALHOST_ONLY=0
echo "### debloque_b $(date) mode=$MODE"

# 0. Rien ne doit tourner côté PC (règle : horloge d'abord, nœuds ensuite) : on nettoie
# automatiquement les restes d'un lancement précédent au lieu de s'arrêter.
echo "=== 0/4 nettoyage des nœuds ROS restés sur le PC"
bash "$S/stop_pc_nodes.sh"

echo "=== 1/4 robot_check"
bash "$S/robot_check.sh" || { echo "STOP : robot_check a échoué (Wi-Fi du robot ? clé SSH ?)"; exit 1; }

echo "=== 2/4 Nav2 seul (log : /tmp/nav2_debloque.log)"
if [ "$MODE" = static ]; then
  # Sans AMCL : map -> odom identité (le robot vient d'être relancé sur la croix)
  ros2 run tf2_ros static_transform_publisher --frame-id map --child-frame-id odom > /tmp/tf_static_map.log 2>&1 &
  TFPID=$!
  ros2 launch nav2_bringup navigation_launch.py params_file:="$PARAMS" use_sim_time:=false \
    > /tmp/nav2_debloque.log 2>&1 &
  NAVPID=$!
  ros2 run nav2_map_server map_server --ros-args -p yaml_filename:="$CARTE" -p use_sim_time:=false > /tmp/map_server.log 2>&1 &
  MAPPID=$!
  sleep 3
  ros2 run nav2_util lifecycle_bringup map_server >> /tmp/map_server.log 2>&1
else
  ros2 launch nav2_bringup bringup_launch.py map:="$CARTE" params_file:="$PARAMS" use_sim_time:=false \
    > /tmp/nav2_debloque.log 2>&1 &
  NAVPID=$!
fi
arret() {
  # Les processus lancés en arrière-plan par un script ignorent SIGINT (pas de contrôle de
  # tâches) : l'ancien « kill -INT » ne les arrêtait pas. stop_pc_nodes envoie TERM puis KILL.
  echo "=== arrêt de Nav2 et du robot"
  bash "$S/stop_robot.sh"
  bash "$S/stop_pc_nodes.sh"
  cp /tmp/nav2_debloque.log "${LOG%.log}_nav2.log" 2>/dev/null
}
trap arret EXIT
echo "   attente 25 s (démarrage de Nav2)"
sleep 25

echo "=== 3/4 diagnostic diag_b"
bash "$S/diag_b.sh"

echo "=== 4/4 test de mouvement (un seul objectif, au centre de la zone)"
echo "   Une personne près du robot, la main prête à le soulever. Entrée pour lancer, Ctrl+C pour annuler."
read -r
# En mode static, goal_test attend controller_server au lieu d'AMCL
timeout 180 python3 "$S/goal_test.py" "$CARTE" "$( [ "$MODE" = static ] && echo static )"; R=$?

echo
echo "--- messages clés de Nav2 pendant le test"
sed -n '/Begin navigating/,$p' /tmp/nav2_debloque.log | grep -E "collision|Failed to make progress|Reached|too old|Extrapolation|Aborting|spin|backup" \
  | awk '!s[substr($0,60,60)]++' | cut -c1-160
case $R in
  0) echo "RÉSULTAT : Nav2 fait VRAIMENT bouger le robot."
     echo "Suite : remets le robot sur la croix, puis lance le run B court :"
     echo "  bash $S/robot_check.sh"
     echo "  ros2 launch aspi_bot aspi_real_planned.launch.py map:=$CARTE run_duration:=300.0$( [ "$MODE" = static ] && echo ' localization:=static')$( [ "${2:-}" = nocoll ] && echo " nav2_params:=$PARAMS")";;
  1) echo "RÉSULTAT : le robot n'a PAS bougé (faux succès ou échec de Nav2)."
     [ "$MODE" = static ] && echo "Suite : impasse documentée (JOUR_ROBOT.md section 12, étapes 6-7)." \
                          || echo "Suite : robot sur la croix, puis essaie le repli sans AMCL : bash $S/debloque_b.sh static";;
  124) echo "RÉSULTAT : Nav2 n'est jamais devenu actif en 180 s. Voir le log Nav2 : ${LOG%.log}_nav2.log";;
  *) echo "RÉSULTAT : erreur du test (code $R), voir le log.";;
esac
echo "Journal complet : $LOG"

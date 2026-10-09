#!/usr/bin/env bash
# Diagnostic d'environ 30 s pour le run B sur le robot réel :
# « le problème vient-il de l'horloge, du réseau ou de Nav2 ? »
# Ne remet JAMAIS le robot à l'heure et ne lance rien sur le robot (lecture seule).
# Usage (onglet Ubuntu du PC, Nav2 lancé si possible) :
#   bash ~/ros2_ws/src/aspi_bot/scripts/diag_b.sh          # robot réel
#   bash ~/ros2_ws/src/aspi_bot/scripts/diag_b.sh --sim    # simulation
# --sim : garde l'environnement ROS courant (ROS_DOMAIN_ID, ROS_LOCALHOST_ONLY),
# saute le SSH (horloge, charge robot) et l'âge des messages (en simulation,
# header.stamp est en temps simulé : l'âge mesuré n'aurait aucun sens).
SIM=0
for a in "$@"; do
  case "$a" in
    --sim) SIM=1 ;;
    *) echo "Option inconnue : $a (seule --sim existe)"; exit 2 ;;
  esac
done
ROBOT=${ROBOT:-turtle@10.42.0.1}
ROBOT_DOMAIN_ID=${ROBOT_DOMAIN_ID:-1}
if [ "$SIM" = 0 ]; then
  export ROS_DOMAIN_ID=$ROBOT_DOMAIN_ID ROS_LOCALHOST_ONLY=0
fi
export PYTHONUNBUFFERED=1
[ -f /opt/ros/humble/setup.bash ] && source /opt/ros/humble/setup.bash 2>/dev/null

SEUIL_HORLOGE_MS=100
SEUIL_AGE_S=0.3
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=5 -o ServerAliveInterval=2 -o ServerAliveCountMax=2"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

PB_HORLOGE=0; PB_AGE=0; PB_NAV2=0; PB_DONNEES=0; PB_TF=0
ECART="?"

# Comparaison de flottants : sup A B -> code 0 si A > B
sup() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a>b)}'; }

HAS_ROS=1
command -v ros2 >/dev/null 2>&1 || HAS_ROS=0

# Au plus 3 commandes ros2 simultanées (au-delà : « context is not valid »).
# lance_ros CMD... : démarre en arrière-plan ; fait un `wait` toutes les 3 commandes.
NB_JOBS=0
lance_ros() {
  "$@" &
  NB_JOBS=$((NB_JOBS + 1))
  if [ $((NB_JOBS % 3)) -eq 0 ]; then wait; fi
}
# Variante pour le pipeline tf2_echo (horodatage de chaque ligne)
tf_horodate() {
  timeout 8 ros2 run tf2_ros tf2_echo "$1" "$2" 2>&1 | while IFS= read -r l; do
    echo "$(date +%s.%N) $l"; done > "$TMP/tf_$1"
}

if [ "$SIM" = 1 ]; then
  echo "== Mode simulation : environnement ROS hérité (ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}, ROS_LOCALHOST_ONLY=${ROS_LOCALHOST_ONLY:-non défini})"
  echo "== 1. Écart d'horloge : ignoré en simulation (pas de robot, pas de SSH)"
else
echo "== 1. Écart d'horloge PC - robot (sans remise à l'heure)"
t0=$(date +%s%3N)
r=$(timeout 12 ssh $SSH_OPTS "$ROBOT" date +%s%3N 2>/dev/null)
t1=$(date +%s%3N)
if [[ "$r" =~ ^[0-9]+$ ]]; then
  e=$(( (t0 + t1) / 2 - r )); ECART=${e#-}
  if [ "$ECART" -lt "$SEUIL_HORLOGE_MS" ]; then
    echo "   OK      écart = ${ECART} ms (< ${SEUIL_HORLOGE_MS} ms)"
  else
    echo "   ALERTE  écart = ${ECART} ms (>= ${SEUIL_HORLOGE_MS} ms) : horloges désynchronisées."
    echo "           Ne remets PAS le robot à l'heure pendant que des nœuds tournent."
    echo "           Si tu le fais, relance TOUS les nœuds du PC (Nav2, tracker, executor...)."
    PB_HORLOGE=1
  fi
else
  echo "   ALERTE  robot injoignable en SSH par clé ($ROBOT) : écart d'horloge inconnu."
  PB_HORLOGE=2
fi
fi

# Mesures ROS par lots de 3 commandes max (chacune bornée par timeout), ~40 s au total.
if [ "$HAS_ROS" = 1 ]; then
  if [ "$SIM" = 0 ]; then
    for t in scan odom; do
      lance_ros timeout 10 bash -c "ros2 topic delay /$t > '$TMP/delay_$t' 2>&1"
    done
  fi
  for t in scan odom tf; do
    lance_ros timeout 10 bash -c "ros2 topic hz /$t > '$TMP/hz_$t' 2>&1"
  done
  for n in map_server amcl planner_server controller_server bt_navigator waypoint_follower behavior_server; do
    lance_ros timeout 5 bash -c "ros2 lifecycle get /$n > '$TMP/lc_$n' 2>&1"
  done
  for paire in "map base_footprint" "odom base_footprint"; do
    set -- $paire
    lance_ros tf_horodate "$1" "$2"
  done
fi

echo "== 6. Charge CPU (lecture pendant les mesures)"
echo "   PC/WSL   : $(uptime | sed 's/.*load average/load average/')"
top -bn1 2>/dev/null | head -12 | sed 's/^/   /'
if [ "$SIM" = 1 ]; then
  echo "   Robot    : sans objet en simulation (la charge du PC/WSL ci-dessus fait foi)."
else
  rl=$(timeout 12 ssh $SSH_OPTS "$ROBOT" uptime 2>/dev/null)
  if [ -n "$rl" ]; then
    echo "   Robot    : $(echo "$rl" | sed 's/.*load average/load average/')   (4 coeurs sur le Pi : > 3 = surchargé)"
  else
    echo "   ALERTE  charge du robot illisible (SSH impossible)."
  fi
fi

if [ "$HAS_ROS" = 0 ]; then
  echo "== 2-5. ALERTE  commande ros2 introuvable (source /opt/ros/humble/setup.bash) : mesures ROS impossibles."
  PB_DONNEES=1
else
  wait
  if [ "$SIM" = 1 ]; then
    echo "== 2. Âge des messages : ignoré en simulation (stamps en temps simulé)"
  else
  echo "== 2. Âge des messages à l'arrivée sur le PC (ros2 topic delay)"
  for t in scan odom; do
    d=$(grep -o 'average delay: *[-0-9.eE+]*' "$TMP/delay_$t" | tail -1 | awk '{print $3}')
    if [ -z "$d" ]; then
      echo "   ALERTE  /$t : aucun message reçu en 10 s (robot éteint, mauvais ROS_DOMAIN_ID=$ROS_DOMAIN_ID, Wi-Fi ?)"
      PB_DONNEES=1
    else
      da=$(awk -v d="$d" 'BEGIN{print (d<0?-d:d)}')
      if sup "$da" "$SEUIL_AGE_S"; then
        echo "   ALERTE  /$t : âge moyen = ${d} s (> ${SEUIL_AGE_S} s)"; PB_AGE=1
      else
        echo "   OK      /$t : âge moyen = ${d} s (< ${SEUIL_AGE_S} s)"
      fi
    fi
  done
  echo "   Lecture : âge ~ écart d'horloge (${ECART} ms) -> problème d'HORLOGE ;"
  echo "             âge >> écart d'horloge -> latence réseau/Wi-Fi ou charge CPU."
  fi

  echo "== 3. Fréquences (attendues : /scan ~5 Hz, /odom ~30 Hz, /tf plusieurs dizaines de Hz)"
  for t in scan odom tf; do
    f=$(grep -o 'average rate: *[0-9.]*' "$TMP/hz_$t" | tail -1 | awk '{print $3}')
    if [ -z "$f" ]; then
      echo "   ALERTE  /$t : aucune fréquence mesurée (pas de message)"; PB_DONNEES=1
    else
      echo "   info    /$t : ${f} Hz"
    fi
  done

  echo "== 4. Nav2 (état lifecycle)"
  actifs=0; vus=0; amcl_vu=0
  for n in map_server amcl planner_server controller_server bt_navigator waypoint_follower behavior_server; do
    etat=$(grep -oE '(unconfigured|inactive|active|finalized) \[[0-9]\]' "$TMP/lc_$n" | head -1)
    if [ -z "$etat" ]; then
      echo "   absent  /$n (nœud introuvable ou ne répond pas)"
    elif [[ "$etat" == active* ]]; then
      echo "   OK      /$n : $etat"; actifs=$((actifs+1)); vus=$((vus+1))
      [ "$n" = amcl ] && amcl_vu=1
    else
      echo "   ALERTE  /$n : $etat (attendu : active)"; vus=$((vus+1)); PB_NAV2=1
      [ "$n" = amcl ] && amcl_vu=1
    fi
  done
  if [ "$vus" -eq 0 ]; then
    echo "   Nav2 ne tourne pas (ou non visible) : étape ignorée dans le verdict."
  else
    attendus=7
    if [ "$amcl_vu" = 0 ]; then
      attendus=6
      echo "   info    /amcl absent : mode sans AMCL (localization:=static), 6 nœuds actifs attendus."
    fi
    [ "$actifs" -lt "$attendus" ] && PB_NAV2=1
  fi

  echo "== 5. TF (tf2_echo bornés)"
  for paire in "map base_footprint" "odom base_footprint"; do
    set -- $paire
    f="$TMP/tf_$1"
    ligne=$(grep 'At time' "$f" 2>/dev/null | tail -1)
    if [ -z "$ligne" ]; then
      echo "   ALERTE  TF $1 -> $2 : absente"
      [ "$1" = odom ] && PB_TF=1
      [ "$1" = map ] && [ "$vus" -gt 0 ] && PB_TF=1
      grep -iE 'exception|error|extrapolation|frame' "$f" 2>/dev/null | head -2 | sed 's/^[0-9.]* /           /'
    else
      if [ "$SIM" = 1 ]; then
        echo "   OK      TF $1 -> $2 : présente (âge ignoré en simulation, stamps en temps simulé)"
        continue
      fi
      tnow=$(echo "$ligne" | awk '{print $1}')
      tst=$(echo "$ligne" | awk '{print $NF}')
      age=$(awk -v n="$tnow" -v s="$tst" 'BEGIN{printf "%.2f", n-s}')
      if sup "$(awk -v a="$age" 'BEGIN{print (a<0?-a:a)}')" 1.0; then
        echo "   ALERTE  TF $1 -> $2 : présente, âge ~ ${age} s (> 1 s : Nav2 la rejettera)"; PB_AGE=1
      else
        echo "   OK      TF $1 -> $2 : présente, âge ~ ${age} s"
      fi
    fi
  done
fi

echo
echo "== Verdict"
if [ "$PB_HORLOGE" = 2 ] && [ "$PB_DONNEES" = 1 ]; then
  echo "   RÉSEAU : robot injoignable (SSH) et aucune donnée ROS. Vérifie le Wi-Fi du robot, son alimentation,"
  echo "   le bringup (robot_check.sh) et ROS_DOMAIN_ID=$ROBOT_DOMAIN_ID."
elif [ "$PB_HORLOGE" = 1 ]; then
  echo "   HORLOGE : écart ${ECART} ms. Resynchroniser le robot (robot_check.sh), puis RELANCER tous les nœuds du PC."
elif [ "$PB_DONNEES" = 1 ]; then
  echo "   RÉSEAU/DDS : topics muets ou absents. Vérifie le bringup du robot, le Wi-Fi, ROS_DOMAIN_ID et ROS_LOCALHOST_ONLY=0."
elif [ "$PB_AGE" = 1 ]; then
  if [ "$SIM" = 1 ]; then ECART_TXT="horloges proches"; else ECART_TXT="horloges proches (écart ${ECART} ms)"; fi
  echo "   RÉSEAU/CPU : ${ECART_TXT} mais messages trop vieux : latence Wi-Fi ou charge CPU"
  echo "   (voir étape 6). Action : rapprocher le PC du robot, fermer les applis lourdes (Gazebo, RViz), relancer."
elif [ "$PB_NAV2" = 1 ] || [ "$PB_TF" = 1 ]; then
  echo "   NAV2 : horloge et réseau corrects, mais Nav2 ou les TF ne sont pas prêts."
  echo "   Action : relancer Nav2 proprement, consulter son log (étape bt_navigator/amcl), vérifier la pose initiale."
else
  echo "   OK : horloge, réseau et Nav2 semblent sains. Si le robot ne bouge pas, vérifier /cmd_vel et le mouvement réel."
fi

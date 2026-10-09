"""Nœud coverage_executor : stratégie B (exécution du balayage par Nav2).

Interface fine et séquentielle : /coverage_path -> setInitialPose ->
wait_nav2_active -> followWaypoints -> suivi de la progression.
"""
import math
import signal
import sys
import time

import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped
from lifecycle_msgs.srv import GetState
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav_msgs.msg import Odometry, Path
from rclpy.executors import ExternalShutdownException
from rclpy.qos import (QoSDurabilityPolicy, QoSProfile,
                       QoSReliabilityPolicy, qos_profile_sensor_data)
from rclpy.signals import SignalHandlerOptions

from aspi_bot.progress_check import ProgressMonitor, segment_length


class Nav2Timeout(Exception):
    """Nav2 pas actif avant le délai global `nav2_timeout` (temps monotone)."""

    def __init__(self, manquant):
        super().__init__(manquant)
        self.manquant = manquant


def verifier_delai(deadline, manquant):
    """Lève Nav2Timeout si le délai global (time.monotonic) est dépassé."""
    if time.monotonic() > deadline:
        raise Nav2Timeout(manquant)


def pause(nav, duree):
    """Vraie pause de `duree` s (temps réel), interruptible, qui traite les callbacks.

    spin_once(timeout_sec=X) ne suffit pas : il rend la main au premier callback
    (/clock arrive à ~10 Hz), donc il dure ~0,1 s et non X.
    """
    t0 = time.monotonic()
    while rclpy.ok() and time.monotonic() - t0 < duree:
        rclpy.spin_once(nav, timeout_sec=0.1)


def wait_for_path(nav):
    """Attend un message /coverage_path (spin_once, sans callback bloquant)."""
    qos = QoSProfile(depth=1,
                     reliability=QoSReliabilityPolicy.RELIABLE,
                     durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
    received = []
    nav.create_subscription(Path, '/coverage_path', received.append, qos)
    waited = 0
    while rclpy.ok() and not received:
        rclpy.spin_once(nav, timeout_sec=1.0)
        waited += 1
        if waited % 10 == 0:
            nav.get_logger().info(
                f'En attente de /coverage_path ({waited} s)...')
    return received[0] if received else None


class OdomDistance:
    """Cumule la distance parcourue d'après /odom (somme des normes entre positions)."""

    def __init__(self, nav):
        self.total = 0.0
        self.count = 0  # nombre de messages reçus (0 = pas d'odométrie)
        self._last = None
        # Best effort : compatible avec un éditeur fiable OU best effort
        # (un abonné fiable ne recevrait rien d'un éditeur best effort).
        nav.create_subscription(Odometry, '/odom', self._on_odom,
                                qos_profile_sensor_data)

    def _on_odom(self, msg):
        p = msg.pose.pose.position
        if self._last is not None:
            self.total += math.hypot(p.x - self._last[0], p.y - self._last[1])
        self._last = (p.x, p.y)
        self.count += 1


def check_validated(nav, monitor, odom, poses, start_xy, last_wp, new_wp, state):
    """Contrôle les waypoints validés par Nav2 entre deux feedbacks.

    Waypoints validés = indices last_wp .. new_wp-1. Pour chacun,
    expected = longueur du segment depuis le précédent (le 1er : depuis la pose
    initiale). Règle si plusieurs waypoints sont validés d'un coup : la distance
    odométrique ET le temps écoulé (horloge du nœud) depuis la dernière validation
    sont répartis au prorata des segments attendus (même ratio pour tous). Ainsi
    un lot lent (waypoints sautés après échec Nav2) donne des temps élevés, un lot
    instantané sans mouvement reste suspect.
    Retourne True si une progression anormale est détectée.
    """
    log = nav.get_logger()
    traveled = odom.total - state['odom_at_last']
    state['odom_at_last'] = odom.total
    now = nav.get_clock().now()
    delta_t = (now - state['time_at_last']).nanoseconds / 1e9
    state['time_at_last'] = now
    idx = list(range(max(last_wp, 0), new_wp))
    pts = [start_xy] + [(p.pose.position.x, p.pose.position.y) for p in poses]
    expected = [segment_length(pts[i], pts[i + 1]) for i in idx]  # pts[i] = précédent
    total = sum(expected)
    for i, exp in zip(idx, expected):
        ratio = exp / total if total > 0.0 else 1.0 / len(idx)
        share = traveled * ratio
        dt = delta_t * ratio
        if monitor.on_waypoint_reached(exp, share, dt):
            # Partie « en moins de X s » seulement si le critère de temps est actif
            if math.isfinite(monitor.max_elapsed):
                critere = f' en moins de {monitor.max_elapsed:g} s'
            else:
                critere = ''
            log.error(f'progression anormale : {monitor.suspects} waypoints validés '
                      f'sans déplacement réel (odométrie){critere} — arrêt '
                      f'(waypoint {i + 1}/{len(poses)} : attendu {exp:.2f} m, '
                      f'parcouru {share:.2f} m, en {dt:.1f} s)')
            return True
    return False


def make_initial_pose(nav):
    """Pose initiale (frame map) construite depuis les paramètres."""
    yaw = nav.get_parameter('initial_yaw').value
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = nav.get_clock().now().to_msg()  # temps simulé
    pose.pose.position.x = nav.get_parameter('initial_x').value
    pose.pose.position.y = nav.get_parameter('initial_y').value
    # Rotation autour de z seulement : quaternion (0, 0, sin(yaw/2), cos(yaw/2))
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose


def cancel_task(nav, timeout=5.0):
    """Annule le but Nav2 avec un délai max (cancelTask() attend sans limite).

    N'échoue jamais : une erreur (ou un 2e Ctrl+C pendant l'arrêt) est loggée
    pour ne pas masquer la sortie du programme.
    """
    if nav.result_future is None or nav.goal_handle is None:
        return
    try:
        future = nav.goal_handle.cancel_goal_async()
        rclpy.spin_until_future_complete(nav, future, timeout_sec=timeout)
    except (Exception, KeyboardInterrupt) as err:
        nav.get_logger().warn(f'Annulation impossible : {err}')


def wait_node_active(nav, name, deadline, timeout=2.0):
    """Attend que le nœud lifecycle `name` soit actif (service GetState).

    Pourquoi pas nav.waitUntilNav2Active() ? Sa boucle appelle
    spin_until_future_complete(future) SANS timeout : si la réponse du service
    get_state est perdue (DDS sous WSL), elle attend indéfiniment sans jamais
    renvoyer la requête (blocage observé 2 lancements sur 5, voir JOURNAL).
    Ici chaque attente a un timeout : on renvoie la requête, et rclpy.ok() est
    testé à chaque tour.
    Retourne False si rclpy s'arrête avant que le nœud soit actif.
    """
    log = nav.get_logger()
    client = nav.create_client(GetState, f'/{name}/get_state')
    active = False
    while rclpy.ok() and not active:
        verifier_delai(deadline, name)
        if not client.wait_for_service(timeout_sec=1.0):
            log.info(f'/{name}/get_state indisponible, attente...',
                     throttle_duration_sec=5.0)
            continue
        future = client.call_async(GetState.Request())
        rclpy.spin_until_future_complete(nav, future, timeout_sec=timeout)
        if future.result() is None:
            future.cancel()  # réponse perdue : on oublie cette requête
            log.warn(f'/{name}/get_state : pas de réponse, nouvel essai',
                     throttle_duration_sec=5.0)
            continue
        label = future.result().current_state.label
        active = label == 'active'
        if not active:
            log.info(f'{name} : état "{label}", attente...',
                     throttle_duration_sec=5.0)
            pause(nav, 1.0)  # pause réelle entre deux interrogations GetState
    nav.destroy_client(client)
    if not rclpy.ok():
        return False
    log.info(f'{name} actif')
    return True


def wait_initial_pose(nav, deadline):
    """Republie la pose initiale jusqu'à la réception de /amcl_pose.

    Même boucle que _waitForInitialPose de BasicNavigator (callback du navigator
    qui positionne initial_pose_received). ~1 s entre deux publications :
    chacune réinitialise le filtre d'AMCL.
    """
    log = nav.get_logger()
    while rclpy.ok() and not nav.initial_pose_received:
        verifier_delai(deadline, 'amcl (pas de /amcl_pose après la pose initiale)')
        # Même appel que _waitForInitialPose ; API privée de BasicNavigator,
        # elle peut changer selon la version de nav2_simple_commander.
        nav._setInitialPose()
        log.info('Pose initiale publiée, attente de /amcl_pose...')
        pause(nav, 1.0)


def wait_action_server(nav, deadline):
    """Attend le serveur d'action FollowWaypoints (boucle bornée, interruptible)."""
    while rclpy.ok() and not nav.follow_waypoints_client.wait_for_server(
            timeout_sec=1.0):
        verifier_delai(deadline, 'waypoint_follower (serveur d\'action FollowWaypoints)')
        nav.get_logger().info('Serveur FollowWaypoints indisponible, attente...',
                              throttle_duration_sec=5.0)


def wait_nav2_active(nav):
    """Séquence d'attente de Nav2 ; retourne False si l'arrêt est demandé.

    Le lifecycle_manager active les nœuds en séquence : waypoint_follower (dernier,
    il dépend de bt_navigator) doit être actif ET son serveur d'action visible
    avant d'envoyer FollowWaypoints, sinon le but est rejeté.
    Délai global `nav2_timeout` (temps monotone) : lève Nav2Timeout au-delà.
    """
    deadline = time.monotonic() + nav.get_parameter('nav2_timeout').value
    if nav.get_parameter('use_amcl').value:
        nav.get_logger().info('Mode use_amcl=True : attente d\'amcl + pose initiale')
        if not wait_node_active(nav, 'amcl', deadline):
            return False
        wait_initial_pose(nav, deadline)
    else:
        nav.get_logger().info('Mode use_amcl=False (localisation statique) : '
                              'amcl et pose initiale ignorés')
    if not wait_node_active(nav, 'bt_navigator', deadline):
        return False
    if not wait_node_active(nav, 'waypoint_follower', deadline):
        return False
    wait_action_server(nav, deadline)
    if rclpy.ok():
        nav.get_logger().info('Nav2 actif')
    return rclpy.ok()


def run(nav):
    log = nav.get_logger()

    path = wait_for_path(nav)
    if path is None:
        return
    poses = list(path.poses)
    log.info(f'/coverage_path reçu : {len(poses)} waypoints')
    if not poses:
        log.error('Trajet vide : rien à exécuter')
        return

    # Stamp nul = « dernière transformation TF disponible » : évite les
    # erreurs d'extrapolation si le Path a été publié bien avant l'envoi.
    for pose in poses:
        pose.header.frame_id = 'map'
        pose.header.stamp = Time()

    # Ordre recommandé : pose initiale AVANT l'attente de Nav2
    # (wait_initial_pose la republie jusqu'à recevoir /amcl_pose).
    if nav.get_parameter('use_amcl').value:
        nav.setInitialPose(make_initial_pose(nav))
    log.info('Attente de Nav2 (amcl + bt_navigator + waypoint_follower)...'
             if nav.get_parameter('use_amcl').value else
             'Attente de Nav2 (bt_navigator + waypoint_follower)...')
    try:
        nav2_ok = wait_nav2_active(nav)
    except Nav2Timeout as err:
        log.error(f'Nav2 non actif après {nav.get_parameter("nav2_timeout").value:g} s '
                  f'(nœud manquant : {err.manquant}) : arrêter le launch et le relancer')
        return 2
    if not nav2_ok:
        log.warn('Arrêt demandé pendant l\'attente de Nav2')
        return

    # Limite connue (non corrigée) : followWaypoints() de BasicNavigator attend
    # l'acceptation du but sans délai (robot_navigator.py:175). Conséquence : si
    # la réponse à send_goal est perdue, l'appel bloque. Ctrl+C reste efficace
    # car /clock réveille l'attente ~10 fois par seconde.
    # Nouvel essai en cas de rejet (serveur pas encore prêt) : 5 essais max.
    max_essais = 5
    for essai in range(1, max_essais + 1):
        if nav.followWaypoints(poses):
            break
        if not rclpy.ok():
            return
        if essai == max_essais:
            log.error(f'followWaypoints refusé par Nav2 ({max_essais} essais) : abandon')
            return
        log.warn(f'followWaypoints refusé (essai {essai}/{max_essais}), '
                 'nouvel essai dans 2 s')
        pause(nav, 2.0)
    log.info('Suivi du balayage démarré')

    # Détecteur de faux succès (Nav2 « atteint » des waypoints sans que le robot bouge)
    odom = None
    monitor = None
    if nav.get_parameter('check_progress').value:
        odom = OdomDistance(nav)
        monitor = ProgressMonitor(
            min_ratio=nav.get_parameter('progress_min_ratio').value,
            min_expected=nav.get_parameter('progress_min_expected').value,
            max_suspects=nav.get_parameter('progress_max_suspects').value,
            max_elapsed=nav.get_parameter('progress_max_elapsed').value)
    start_xy = (nav.get_parameter('initial_x').value,
                nav.get_parameter('initial_y').value)
    t_start = nav.get_clock().now()  # temps simulé (use_sim_time)
    state = {'odom_at_last': 0.0, 'time_at_last': t_start}
    max_duration = nav.get_parameter('max_duration').value
    last_wp = -1
    lost_since = None  # début (temps MONOTONE) de l'indisponibilité du serveur
    status_known = False
    # On n'utilise PAS nav.isTaskComplete() : il appelle spin_until_future_complete
    # sans jamais rendre la main si rclpy est arrêté (boucle chaude) et ajoute
    # un callback au future à chaque appel (fuite mémoire). spin_once + done() suffit.
    while rclpy.ok():
        rclpy.spin_once(nav, timeout_sec=0.1)
        if nav.result_future.done():
            nav.status = nav.result_future.result().status
            status_known = True
            break
        feedback = nav.getFeedback()
        if feedback is not None and feedback.current_waypoint != last_wp:
            new_wp = feedback.current_waypoint
            if monitor is not None and new_wp > max(last_wp, 0):
                if odom.count == 0:
                    log.warn('check_progress : aucune /odom reçue, contrôle '
                             'de progression désactivé', throttle_duration_sec=10.0)
                elif check_validated(nav, monitor, odom, poses, start_xy,
                                     last_wp, new_wp, state):
                    cancel_task(nav)
                    return 1
            last_wp = new_wp
            log.info(f'Waypoint {last_wp + 1}/{len(poses)}')
        # La découverte DDS peut vaciller sous WSL : on ne sort qu'après
        # ~3 s d'échecs consécutifs (compteur remis à zéro dès que ça répond).
        # Mesuré en temps monotone : si /clock s'arrête, le temps simulé ne
        # progresse plus et le délai n'expirerait jamais.
        if nav.follow_waypoints_client.server_is_ready():
            lost_since = None
        else:
            now = time.monotonic()
            if lost_since is None:
                lost_since = now
            if now - lost_since >= 3.0:
                log.error('Serveur FollowWaypoints disparu depuis 3 s : '
                          'annulation et arrêt de l\'executor')
                cancel_task(nav, timeout=2.0)
                return
        elapsed = (nav.get_clock().now() - t_start).nanoseconds / 1e9
        if max_duration > 0.0 and elapsed >= max_duration:
            log.info(f'max_duration atteinte ({elapsed:.0f} s) : annulation')
            cancel_task(nav)
            return
    if not status_known:
        log.warn('Arrêt de rclpy demandé : fin sans résultat')
        return

    result = nav.getResult()
    if result == TaskResult.SUCCEEDED:
        log.info('Résultat : SUCCEEDED (balayage terminé)')
    elif result == TaskResult.CANCELED:
        log.warn('Résultat : CANCELED')
    elif result == TaskResult.FAILED:
        log.error('Résultat : FAILED')
    else:
        log.warn('Résultat : UNKNOWN')

    # En Humble, getResult() ne renvoie que l'enum : les waypoints sautés
    # sont dans le message de résultat brut de l'action.
    if nav.result_future is not None and nav.result_future.result():
        missed = list(nav.result_future.result().result.missed_waypoints)
        log.info(f'Waypoints manqués (sautés) : {len(missed)} '
                 f'{missed if missed else ""}')


def _ignorer_signaux():
    # Un 2e Ctrl+C ou le SIGTERM de launch ne doit pas interrompre l'annulation
    # du but Nav2 ni la destruction du nœud.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)


def main(args=None):
    # SignalHandlerOptions.NO : rclpy n'installe pas son gestionnaire SIGINT
    # (qui éteindrait le contexte et ferait tourner à vide les boucles de
    # BasicNavigator pendant l'attente de Nav2). Python lève alors
    # KeyboardInterrupt partout, et le contexte reste valide pour annuler le but.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    nav = BasicNavigator()  # use_sim_time et --ros-args viennent du launch
    nav.declare_parameter('initial_x', 0.0)
    nav.declare_parameter('initial_y', 0.0)
    nav.declare_parameter('initial_yaw', 0.0)
    # 0.0 = illimité ; sinon durée (s simulées) après laquelle on annule et on quitte
    nav.declare_parameter('max_duration', 0.0)
    # Localisation : False = Nav2 sans AMCL (map->odom statique), pas de pose initiale à attendre
    nav.declare_parameter('use_amcl', True)
    # Délai global (s, temps monotone) d'attente de Nav2 ; sortie code 2 au-delà
    nav.declare_parameter('nav2_timeout', 120.0)
    # Détection des faux succès Nav2 (waypoints validés sans déplacement odométrique)
    nav.declare_parameter('check_progress', True)
    nav.declare_parameter('progress_min_ratio', 0.3)
    nav.declare_parameter('progress_min_expected', 0.15)
    nav.declare_parameter('progress_max_suspects', 2)
    # Un waypoint n'est suspect que s'il est validé en moins de ce délai (s)
    nav.declare_parameter('progress_max_elapsed', 2.0)
    code = 0
    try:
        code = run(nav) or 0
    except (KeyboardInterrupt, ExternalShutdownException):
        # Arrêt demandé (SIGINT) : le contexte rclpy peut déjà être détruit.
        # On n'annule la tâche Nav2 que s'il est encore utilisable
        # (cancel_task gère elle-même un 2e Ctrl+C).
        _ignorer_signaux()
        if rclpy.ok():
            cancel_task(nav)
        else:
            nav.get_logger().info('Arrêt demandé : contexte ROS déjà fermé')
    finally:
        _ignorer_signaux()
        try:
            nav.destroy_node()
        except Exception:
            pass  # contexte déjà détruit
        if rclpy.ok():
            rclpy.shutdown()
    if code:
        sys.exit(code)  # code d'erreur : 1 = progression anormale, 2 = Nav2 non actif


if __name__ == '__main__':
    main()

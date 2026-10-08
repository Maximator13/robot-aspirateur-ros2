"""Nœud coverage_executor : stratégie B (exécution du balayage par Nav2).

Interface fine et séquentielle : /coverage_path -> setInitialPose ->
wait_nav2_active -> followWaypoints -> suivi de la progression.
"""
import math
import time

import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped
from lifecycle_msgs.srv import GetState
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav_msgs.msg import Path
from rclpy.executors import ExternalShutdownException
from rclpy.qos import (QoSDurabilityPolicy, QoSProfile,
                       QoSReliabilityPolicy)
from rclpy.signals import SignalHandlerOptions


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
    """Annule le but Nav2 avec un délai max (cancelTask() attend sans limite)."""
    if nav.result_future is None or nav.goal_handle is None:
        return
    future = nav.goal_handle.cancel_goal_async()
    rclpy.spin_until_future_complete(nav, future, timeout_sec=timeout)


def wait_nav2_active(nav, nodes=('amcl', 'bt_navigator', 'waypoint_follower'),
                     timeout=2.0):
    """Attend que les nœuds Nav2 soient actifs, sans jamais bloquer sans limite.

    Pourquoi pas nav.waitUntilNav2Active() ? Sa boucle appelle
    spin_until_future_complete(future) SANS timeout : si la réponse du service
    get_state est perdue (DDS sous WSL), le processus reste dans rcl_wait (code C),
    Python ne reprend jamais la main et Ctrl+C (SIGINT) est ignoré.
    Ici chaque attente a un timeout : on retente, et rclpy.ok() est testé à chaque tour.

    Le lifecycle_manager active les nœuds en séquence : waypoint_follower (dernier,
    il dépend de bt_navigator) doit être actif ET son serveur d'action visible
    avant d'envoyer FollowWaypoints, sinon le but est rejeté.
    """
    log = nav.get_logger()
    for name in nodes:
        client = nav.create_client(GetState, f'/{name}/get_state')
        active = False
        while rclpy.ok() and not active:
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
        if name == 'amcl':
            # Comme _waitForInitialPose de BasicNavigator : republier la pose
            # initiale jusqu'à ce que /amcl_pose soit reçu (callback du navigator).
            # ~1 s entre deux publications : chacune réinitialise le filtre d'AMCL.
            while rclpy.ok() and not nav.initial_pose_received:
                nav._setInitialPose()
                log.info('Pose initiale publiée, attente de /amcl_pose...')
                pause(nav, 1.0)
    # Serveur d'action FollowWaypoints : boucle bornée par tour, interruptible.
    while rclpy.ok() and not nav.follow_waypoints_client.wait_for_server(
            timeout_sec=1.0):
        log.info('Serveur FollowWaypoints indisponible, attente...',
                 throttle_duration_sec=5.0)
    if rclpy.ok():
        log.info('Nav2 actif')
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
    # (wait_nav2_active la republie jusqu'à recevoir /amcl_pose).
    nav.setInitialPose(make_initial_pose(nav))
    log.info('Attente de Nav2 (amcl + bt_navigator + waypoint_follower)...')
    if not wait_nav2_active(nav):
        log.warn('Arrêt demandé pendant l\'attente de Nav2')
        return

    # Limite connue (non corrigée) : followWaypoints() de BasicNavigator attend
    # l'acceptation du but sans délai (robot_navigator.py:175).
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

    t_start = nav.get_clock().now()  # temps simulé (use_sim_time)
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
            last_wp = feedback.current_waypoint
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
                try:
                    cancel_task(nav, timeout=2.0)
                except (Exception, KeyboardInterrupt) as err:
                    log.warn(f'Annulation impossible : {err}')
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
    try:
        run(nav)
    except (KeyboardInterrupt, ExternalShutdownException):
        # Arrêt demandé (SIGINT) : le contexte rclpy peut déjà être détruit.
        # On n'annule la tâche Nav2 que s'il est encore utilisable.
        if rclpy.ok():
            try:
                cancel_task(nav)
            except (Exception, KeyboardInterrupt) as err:  # 2e Ctrl+C possible; arrêt en cours : ne pas masquer la sortie
                nav.get_logger().warn(f'cancelTask impossible : {err}')
        else:
            nav.get_logger().info('Arrêt demandé : contexte ROS déjà fermé')
    finally:
        try:
            nav.destroy_node()
        except Exception:
            pass  # contexte déjà détruit
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

"""Nœud coverage_executor : stratégie B (exécution du balayage par Nav2).

Interface fine et séquentielle : /coverage_path -> setInitialPose ->
waitUntilNav2Active -> followWaypoints -> suivi de la progression.
"""
import math

import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav_msgs.msg import Path
from rclpy.executors import ExternalShutdownException
from rclpy.qos import (QoSDurabilityPolicy, QoSProfile,
                       QoSReliabilityPolicy)


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

    # Ordre recommandé : pose initiale AVANT waitUntilNav2Active
    # (avec amcl, celui-ci republie la pose jusqu'à recevoir /amcl_pose).
    nav.setInitialPose(make_initial_pose(nav))
    log.info('Attente de Nav2 (amcl + bt_navigator)...')
    nav.waitUntilNav2Active(navigator='bt_navigator', localizer='amcl')

    if not nav.followWaypoints(poses):
        log.error('followWaypoints refusé par Nav2')
        return
    log.info('Suivi du balayage démarré')

    t_start = nav.get_clock().now()  # temps simulé (use_sim_time)
    max_duration = nav.get_parameter('max_duration').value
    last_wp = -1
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
        if not nav.follow_waypoints_client.server_is_ready():
            log.error('Serveur FollowWaypoints disparu : arrêt de l\'executor')
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
    rclpy.init(args=args)
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
            except Exception as err:  # arrêt en cours : ne pas masquer la sortie
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

"""Nœud coverage_follower : stratégie B SANS Nav2 (repli robot réel).

Interface fine : /coverage_path (waypoints du boustrophédon) + pose TF map -> base_footprint
-> follow_logic.follow_step -> /cmd_vel. Arrêt devant un obstacle (LiDAR avant) et fin de run.
Pourquoi : sur le robot réel, Nav2 tourne sur place sans avancer (journal du 12/10) ;
ce suiveur « tourner puis avancer » est le même principe que le random_walker.
Sécurité : sans /scan reçu, ou avec scan/TF plus vieux que data_timeout, le robot est arrêté.
"""
import math
import signal
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Path
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformException, TransformListener

from aspi_bot.follow_logic import follow_step
from aspi_bot.random_logic import front_min_distance

LATCHED_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)


class CoverageFollower(Node):
    def __init__(self):
        super().__init__('coverage_follower')
        p = self.declare_parameter
        self.linear_speed = p('linear_speed', 0.10).value
        self.angular_speed = p('angular_speed', 0.6).value
        self.goal_tolerance = p('goal_tolerance', 0.08).value
        self.heading_tolerance = p('heading_tolerance', 0.35).value
        self.stop_distance = p('stop_distance', 0.15).value  # obstacle devant : on n'avance pas
        self.front_angle = math.radians(p('front_angle_deg', 30.0).value)  # demi-secteur avant
        self.data_timeout = p('data_timeout', 1.0).value  # scan/TF plus vieux : arrêt (s)
        self.waypoint_timeout = p('waypoint_timeout', 40.0).value  # waypoint sauté au-delà (s)
        self.run_duration = p('run_duration', 0.0).value  # 0 = illimité
        self.map_frame = p('map_frame', 'map').value
        self.base_frame = p('base_frame', 'base_footprint').value

        self.waypoints = []
        self.index = 0
        self.driving = False
        self.front = None  # None = aucun /scan reçu : on ne roule pas
        self.last_scan_s = None
        self.start_s = None
        self.wp_start_s = None
        self.done = False

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Path, '/coverage_path', self.on_path, LATCHED_QOS)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_timer(0.1, self.on_timer)
        self.get_logger().info('coverage_follower démarré : attente de /coverage_path')

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def on_path(self, msg):
        self.waypoints = [(ps.pose.position.x, ps.pose.position.y) for ps in msg.poses]
        self.index = 0
        self.done = False
        self.driving = False
        self.wp_start_s = None
        self.get_logger().info(f'/coverage_path reçu : {len(self.waypoints)} waypoints')

    def on_scan(self, msg):
        self.front = front_min_distance(msg.ranges, msg.angle_min, msg.angle_increment,
                                        msg.range_min, msg.range_max, self.front_angle)
        self.last_scan_s = self.now_s()

    def pose(self):
        """(x, y, yaw) du robot dans map, ou None si la TF n'est pas disponible."""
        try:
            t = self.tf_buffer.lookup_transform(self.map_frame, self.base_frame, Time())
        except TransformException as e:
            self.get_logger().warn(f'TF {self.map_frame} -> {self.base_frame} indisponible : {e}',
                                   throttle_duration_sec=5.0)
            return None
        age = self.now_s() - Time.from_msg(t.header.stamp).nanoseconds * 1e-9
        if age > self.data_timeout:
            self.get_logger().warn(f'TF {self.map_frame} -> {self.base_frame} périmée '
                                   f'({age:.1f} s) : arrêt', throttle_duration_sec=2.0)
            return None
        q = t.transform.rotation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        return t.transform.translation.x, t.transform.translation.y, yaw

    def on_timer(self):
        now = self.now_s()
        if now == 0.0 or not self.waypoints or self.done:
            self.publish(0.0, 0.0)
            return
        if self.front is None:
            self.get_logger().warn('aucun /scan reçu : robot à l\'arrêt', throttle_duration_sec=2.0)
            self.publish(0.0, 0.0)
            return
        if now - self.last_scan_s > self.data_timeout:
            self.get_logger().warn(f'/scan périmé ({now - self.last_scan_s:.1f} s) : arrêt',
                                   throttle_duration_sec=2.0)
            self.publish(0.0, 0.0)
            return
        if self.start_s is None:
            self.start_s = now
        if self.wp_start_s is None:
            self.wp_start_s = now
        if self.run_duration > 0.0 and now - self.start_s > self.run_duration:
            self.get_logger().info('fin du run : robot à l\'arrêt (Ctrl+C pour quitter)',
                                   throttle_duration_sec=10.0)
            self.publish(0.0, 0.0)
            return
        pose = self.pose()
        if pose is None:
            self.publish(0.0, 0.0)
            return
        if now - self.wp_start_s > self.waypoint_timeout:
            self.get_logger().warn(f'waypoint {self.index + 1} non atteint en '
                                   f'{self.waypoint_timeout:.0f} s : sauté')
            self.next_waypoint(now)
            return
        tx, ty = self.waypoints[self.index]
        v, w, reached, self.driving = follow_step(
            *pose, tx, ty, self.driving, self.linear_speed, self.angular_speed,
            self.goal_tolerance, self.heading_tolerance)
        if reached:
            self.get_logger().info(f'waypoint {self.index + 1}/{len(self.waypoints)} atteint')
            self.next_waypoint(now)
            return
        if v > 0.0 and self.front < self.stop_distance:
            self.get_logger().warn(f'obstacle à {self.front:.2f} m devant : pause',
                                   throttle_duration_sec=2.0)
            v = 0.0
        self.publish(v, w)

    def next_waypoint(self, now):
        self.index += 1
        self.wp_start_s = now
        self.driving = False
        if self.index >= len(self.waypoints):
            self.done = True
            self.get_logger().info('trajet terminé : robot à l\'arrêt')
        self.publish(0.0, 0.0)

    def publish(self, v, w):
        msg = Twist()
        msg.linear.x = float(v)
        msg.angular.z = float(w)
        self.cmd_pub.publish(msg)


def _sigterm_vers_interruption(signum, frame):
    raise KeyboardInterrupt


def main(args=None):
    # Même arrêt propre que random_walker : contexte gardé valide pour publier des Twist nuls
    # (le TurtleBot3 réel garde sinon la dernière consigne).
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, _sigterm_vers_interruption)
    node = CoverageFollower()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if rclpy.ok():
            for _ in range(5):
                node.publish(0.0, 0.0)
                time.sleep(0.05)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

"""Nœud random_walker : stratégie A (bump and turn).

Interface fine : /scan -> distance frontale -> RandomWalkerLogic -> /cmd_vel.
Option robot réel : barrière virtuelle (paramètre `fence`, rectangle en repère odom) ;
la distance frontale devient min(LiDAR, distance à la barrière), pose lue sur /odom.
"""
import math
import signal
import time

import rclpy
from rclpy.parameter import Parameter
from rclpy.executors import ExternalShutdownException
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

from aspi_bot.random_logic import (RandomWalkerLogic, fence_distance_ahead,
                                  front_min_distance)


class RandomWalkerNode(Node):
    def __init__(self):
        super().__init__('random_walker')
        # Paramètres (valeurs par défaut du contrat TASKS.md)
        self.declare_parameter('seed', 1)
        self.declare_parameter('forward_speed', 0.15)
        self.declare_parameter('turn_speed', 1.0)
        self.declare_parameter('stop_distance', 0.25)
        self.declare_parameter('front_angle_deg', 30.0)
        self.declare_parameter('control_rate', 10.0)
        # Chien de garde : sans scan (ou odom si fence) plus récent, le robot s'arrête (s)
        self.declare_parameter('data_timeout', 0.5)
        self.data_timeout = self.get_parameter('data_timeout').value
        # Barrière virtuelle (robot réel) : [xmin, ymin, xmax, ymax] en repère odom,
        # [] = désactivée. Type explicite : un tableau vide n'a pas de type déductible.
        self.declare_parameter(
            'fence', Parameter.Type.DOUBLE_ARRAY)
        self.fence = [float(v) for v in (self.get_parameter_or('fence').value or [])]
        if self.fence and len(self.fence) != 4:
            raise ValueError('fence doit contenir 4 valeurs : xmin ymin xmax ymax')

        self.logic = RandomWalkerLogic(
            seed=self.get_parameter('seed').value,
            forward_speed=self.get_parameter('forward_speed').value,
            turn_speed=self.get_parameter('turn_speed').value,
            stop_distance=self.get_parameter('stop_distance').value)
        self.front_angle = math.radians(
            self.get_parameter('front_angle_deg').value)

        self.front_distance = None  # None tant qu'aucun scan reçu
        self.pose = None  # (x, y, yaw) odom, None tant qu'aucune odom reçue
        self.last_scan_s = None  # horloge du nœud à la dernière réception
        self.last_odom_s = None
        self.last_state = self.logic.state

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(
            LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        if self.fence:
            self.create_subscription(Odometry, '/odom', self.on_odom, 10)
            self.get_logger().info(f'barrière virtuelle active (repère odom) : {self.fence}')
        period = 1.0 / self.get_parameter('control_rate').value
        self.create_timer(period, self.on_timer)
        self.get_logger().info('random_walker démarré, état initial '
                               f'{self.logic.state}')

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def on_scan(self, msg):
        self.last_scan_s = self.now_s()
        # Distance minimale dans le secteur avant
        self.front_distance = front_min_distance(
            msg.ranges, msg.angle_min, msg.angle_increment,
            msg.range_min, msg.range_max, self.front_angle)

    def on_odom(self, msg):
        q = msg.pose.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        p = msg.pose.pose.position
        self.pose = (p.x, p.y, yaw)
        self.last_odom_s = self.now_s()

    def on_timer(self):
        now_s = self.now_s()
        if now_s == 0.0:  # pas encore de /clock
            return
        if self.front_distance is None:
            self.publish(0.0, 0.0)
            return
        # Chien de garde : distance périmée -> arrêt plutôt qu'avancer à l'aveugle
        stale = now_s - self.last_scan_s > self.data_timeout
        if self.fence and self.last_odom_s is not None:
            stale = stale or now_s - self.last_odom_s > self.data_timeout
        if stale:
            self.get_logger().warn(
                f'données /scan ou /odom plus anciennes que {self.data_timeout} s : arrêt',
                throttle_duration_sec=2.0)
            self.publish(0.0, 0.0)
            return
        distance = self.front_distance
        if self.fence:
            if self.pose is None:
                self.get_logger().warn('barrière active mais aucune /odom reçue : le robot reste à l\'arrêt',
                                       throttle_duration_sec=5.0)
                self.publish(0.0, 0.0)
                return
            distance = min(distance, fence_distance_ahead(
                *self.pose, self.fence, self.front_angle))
        linear, angular = self.logic.update(now_s, distance)
        if self.logic.state != self.last_state:
            self.get_logger().info(
                f'{self.last_state} -> {self.logic.state} '
                f'(distance avant {distance:.2f} m)')
            self.last_state = self.logic.state
        self.publish(linear, angular)

    def publish(self, linear, angular):
        msg = Twist()
        msg.linear.x = float(linear)
        msg.angular.z = float(angular)
        self.cmd_pub.publish(msg)

    def stop(self):
        """Publie une vitesse nulle (arrêt propre)."""
        try:
            self.publish(0.0, 0.0)
        except Exception:
            pass


def _sigterm_vers_interruption(signum, frame):
    # ros2 launch envoie SIGTERM si SIGINT ne suffit pas : on le traite comme un Ctrl+C
    # pour passer par le même arrêt propre (Twist nul).
    raise KeyboardInterrupt


def main(args=None):
    # SignalHandlerOptions.NO : rclpy n'installe pas son gestionnaire SIGINT, qui fermerait
    # le contexte AVANT le `finally` (publication impossible, le dernier /cmd_vel resterait
    # appliqué : le robot réel continuerait tout droit). Python lève KeyboardInterrupt et
    # le contexte reste valide pour publier l'arrêt.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, _sigterm_vers_interruption)
    node = RandomWalkerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        # Un 2e Ctrl+C ou le SIGTERM de launch ne doit pas interrompre l'envoi des
        # Twist nuls ni destroy_node.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        # Plusieurs Twist nuls (un seul message peut être perdu). time.sleep acceptable
        # ici : hors callback, à l'arrêt.
        if rclpy.ok():
            for _ in range(5):
                node.stop()
                time.sleep(0.05)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

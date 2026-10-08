"""Nœud random_walker : stratégie A (bump and turn).

Interface fine : /scan -> distance frontale -> RandomWalkerLogic -> /cmd_vel.
"""
import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

from aspi_bot.random_logic import RandomWalkerLogic, front_min_distance


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

        self.logic = RandomWalkerLogic(
            seed=self.get_parameter('seed').value,
            forward_speed=self.get_parameter('forward_speed').value,
            turn_speed=self.get_parameter('turn_speed').value,
            stop_distance=self.get_parameter('stop_distance').value)
        self.front_angle = math.radians(
            self.get_parameter('front_angle_deg').value)

        self.front_distance = None  # None tant qu'aucun scan reçu
        self.last_state = self.logic.state

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(
            LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        period = 1.0 / self.get_parameter('control_rate').value
        self.create_timer(period, self.on_timer)
        self.get_logger().info('random_walker démarré, état initial '
                               f'{self.logic.state}')

    def on_scan(self, msg):
        # Distance minimale dans le secteur avant
        self.front_distance = front_min_distance(
            msg.ranges, msg.angle_min, msg.angle_increment,
            msg.range_min, msg.range_max, self.front_angle)

    def on_timer(self):
        now_s = self.get_clock().now().nanoseconds * 1e-9
        if now_s == 0.0:  # pas encore de /clock
            return
        if self.front_distance is None:
            self.publish(0.0, 0.0)
            return
        linear, angular = self.logic.update(now_s, self.front_distance)
        if self.logic.state != self.last_state:
            self.get_logger().info(
                f'{self.last_state} -> {self.logic.state} '
                f'(distance avant {self.front_distance:.2f} m)')
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


def main(args=None):
    rclpy.init(args=args)
    node = RandomWalkerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

"""Nœud coverage_planner (stratégie B) : /map -> /coverage_path.

Interface fine : toute la logique est dans aspi_bot.planning (Python pur).
Une publication par carte reçue.
"""
import math

import rclpy
from rclpy.executors import ExternalShutdownException
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid, Path
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from aspi_bot import planning

# /map et /coverage_path : RELIABLE + TRANSIENT_LOCAL (abonné tardif possible)
LATCHED_QOS = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)


def yaw_to_quaternion(yaw):
    """Quaternion (x, y, z, w) d'une rotation d'angle yaw autour de z."""
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class CoveragePlanner(Node):
    def __init__(self):
        super().__init__('coverage_planner')
        self.robot_radius = self.declare_parameter('robot_radius', 0.105).value
        self.safety_margin = self.declare_parameter('safety_margin', 0.05).value
        self.sweep_spacing = self.declare_parameter('sweep_spacing', 0.18).value
        self.start_x = self.declare_parameter('start_x', 0.0).value
        self.start_y = self.declare_parameter('start_y', 0.0).value

        self.path_pub = self.create_publisher(Path, '/coverage_path', LATCHED_QOS)
        self.create_subscription(OccupancyGrid, '/map', self.on_map, LATCHED_QOS)
        self.get_logger().info('coverage_planner prêt, en attente de /map')

    def on_map(self, msg):
        info = msg.info
        free = planning.occupancy_to_free(msg.data, info.width, info.height)
        start = planning.world_to_cell(self.start_x, self.start_y,
                                       info.origin.position.x, info.origin.position.y,
                                       info.resolution)
        if not planning.in_bounds(free, *start):
            self.get_logger().error(
                f'Départ ({self.start_x}, {self.start_y}) hors de la carte : rien publié')
            return
        reachable = planning.reachable_mask(free, start, info.resolution,
                                            self.robot_radius, self.safety_margin)
        n_cells = int(reachable.sum())
        if n_cells == 0:
            self.get_logger().error('Masque atteignable vide : rien publié')
            return
        waypoints = planning.boustrophedon_waypoints(
            reachable, info.origin.position.x, info.origin.position.y,
            info.resolution, self.sweep_spacing)
        self.path_pub.publish(self.make_path(waypoints))
        # Même formule que planning.boustrophedon_waypoints
        eff_spacing = max(1, int(round(self.sweep_spacing / info.resolution))) * info.resolution
        self.get_logger().info(
            f'{n_cells} cellules atteignables, {len(waypoints)} waypoints publiés sur /coverage_path '
            f'(espacement demandé {self.sweep_spacing:.2f} m, effectif {eff_spacing:.2f} m)')

    def make_path(self, waypoints):
        path = Path()
        path.header.frame_id = 'map'
        path.header.stamp = self.get_clock().now().to_msg()
        for x, y, yaw in waypoints:
            pose = PoseStamped()
            pose.header = path.header
            pose.pose.position.x = x
            pose.pose.position.y = y
            (pose.pose.orientation.x, pose.pose.orientation.y,
             pose.pose.orientation.z, pose.pose.orientation.w) = yaw_to_quaternion(yaw)
            path.poses.append(pose)
        return path


def main(args=None):
    rclpy.init(args=args)
    node = CoveragePlanner()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

"""Nœud coverage_tracker : mesure commune aux stratégies A et B.

Pose via TF map -> base_footprint, marque les cellules nettoyées, publie
/coverage_status et /coverage_map à 1 Hz, écrit un CSV.
"""
import math
import os
from datetime import datetime

import numpy as np
import rclpy
from aspi_interfaces.msg import CoverageStatus
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import (QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy,
                       qos_profile_sensor_data)
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformException, TransformListener

from aspi_bot.planning import (coverage_percent, mark_covered,
                               occupancy_to_free, reachable_mask,
                               world_to_cell)


class CoverageTrackerNode(Node):
    def __init__(self):
        super().__init__('coverage_tracker')
        self._declare_params()
        p = self.get_parameter
        self.strategy = p('strategy').value
        self.seed = p('seed').value
        self.robot_radius = p('robot_radius').value
        self.safety_margin = p('safety_margin').value
        self.cleaning_radius = p('cleaning_radius').value
        self.near_dist = p('near_collision_distance').value
        self.run_duration = p('run_duration').value
        self.map_frame = p('map_frame').value
        self.base_frame = p('base_frame').value
        self.start_motion_threshold = p('start_motion_threshold').value

        # État de la mesure
        self.map_msg = None
        self.reachable = None
        self.covered = None
        self.radius_cells = 1
        self.last_xy = None
        self.distance = 0.0
        self.start_xy = None     # pose initiale (départ du robot)
        self.start_time = None   # temps sim du début de la mesure (s)
        self.near_collisions = 0
        self.was_near = False
        self.finished = False
        self.csv_file = None

        # Entrées : /map (RELIABLE + TRANSIENT_LOCAL), /scan (BEST_EFFORT), TF
        map_qos = QoSProfile(
            depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(OccupancyGrid, '/map', self.on_map, map_qos)
        self.create_subscription(
            LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Sorties
        self.status_pub = self.create_publisher(
            CoverageStatus, '/coverage_status', 10)
        self.map_pub = self.create_publisher(
            OccupancyGrid, '/coverage_map', map_qos)

        self.create_timer(1.0 / p('pose_rate').value, self.on_pose_timer)
        self.create_timer(1.0, self.on_status_timer)
        self.get_logger().info(
            f'coverage_tracker démarré (stratégie {self.strategy}, '
            f'durée {self.run_duration:.0f} s)')

    def _declare_params(self):
        for name, default in [
                ('strategy', 'RANDOM'), ('seed', 0),
                ('robot_radius', 0.105), ('safety_margin', 0.05),
                ('cleaning_radius', 0.09), ('near_collision_distance', 0.15),
                ('pose_rate', 10.0), ('run_duration', 600.0),
                ('output_dir', '~/ros2_ws/results'),
                ('map_frame', 'map'), ('base_frame', 'base_footprint'),
                ('start_motion_threshold', 0.01)]:
            self.declare_parameter(name, default)

    def open_csv(self):
        """Ouvre le CSV au début effectif de la mesure (pas de CSV vide)."""
        out_dir = os.path.expanduser(self.get_parameter('output_dir').value)
        os.makedirs(out_dir, exist_ok=True)
        date = datetime.now().strftime('%Y%m%d-%H%M%S')
        path = os.path.join(out_dir, f'{self.strategy}_{self.seed}_{date}.csv')
        self.csv_file = open(path, 'w')
        self.csv_file.write('time,coverage_percent,distance,near_collisions\n')
        self.csv_file.flush()
        self.get_logger().info(f'CSV : {path}')

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def elapsed(self):
        return 0.0 if self.start_time is None else self.now_s() - self.start_time

    # ---------- Callbacks d'entrée ----------
    def on_map(self, msg):
        # Carte de vérité terrain figée pour toute la durée du run
        if self.map_msg is not None:
            return
        self.get_logger().info(
            f'carte reçue : {msg.info.width}x{msg.info.height}, '
            f'résolution {msg.info.resolution} m (figée pour le run)')
        self.map_msg = msg

    def on_scan(self, msg):
        # Pas de comptage avant le début de la mesure ni après la fin du run
        if self.finished or self.start_time is None:
            return
        # Distance minimale valide sur 360 degrés
        valid = [r for r in msg.ranges
                 if math.isfinite(r) and msg.range_min <= r <= msg.range_max]
        if not valid:
            return
        near = min(valid) < self.near_dist
        if near and not self.was_near:  # front montant
            self.near_collisions += 1
        self.was_near = near

    # ---------- Pose et couverture ----------
    def read_pose(self):
        try:
            tf = self.tf_buffer.lookup_transform(
                self.map_frame, self.base_frame, rclpy.time.Time())
        except TransformException as e:
            self.get_logger().warn(
                f'TF {self.map_frame} -> {self.base_frame} indisponible : {e}',
                throttle_duration_sec=5.0)
            return None
        t = tf.transform.translation
        return t.x, t.y

    def init_masks(self, x, y):
        """Calcule le masque atteignable à la 1re pose."""
        info = self.map_msg.info
        free = occupancy_to_free(
            self.map_msg.data, info.width, info.height)
        start = world_to_cell(
            x, y, info.origin.position.x, info.origin.position.y,
            info.resolution)
        self.reachable = reachable_mask(
            free, start, info.resolution,
            self.robot_radius, self.safety_margin)
        self.covered = np.zeros_like(self.reachable, dtype=bool)
        self.radius_cells = max(1, round(self.cleaning_radius / info.resolution))
        self.get_logger().info(
            f'masque atteignable : {int(self.reachable.sum())} cellules')

    def on_pose_timer(self):
        if self.finished or self.now_s() == 0.0 or self.map_msg is None:
            return
        pose = self.read_pose()
        if pose is None:
            return
        x, y = pose
        if self.reachable is None:
            self.init_masks(x, y)
            self.start_xy = (x, y)
        if self.start_time is None:
            # Début de la mesure = 1er déplacement notable du robot. En
            # stratégie B, l'activation de Nav2 et le calcul du plan ne
            # doivent pas consommer le temps de nettoyage ; A et B sont
            # ainsi mesurées à partir du même événement (le robot bouge).
            if math.hypot(x - self.start_xy[0],
                          y - self.start_xy[1]) <= self.start_motion_threshold:
                return
            self.start_time = self.now_s()
            self.last_xy = self.start_xy
            self.open_csv()
            self.get_logger().info('début de la mesure')
        if self.last_xy is not None:
            self.distance += math.hypot(x - self.last_xy[0], y - self.last_xy[1])
        self.last_xy = (x, y)
        info = self.map_msg.info
        row, col = world_to_cell(
            x, y, info.origin.position.x, info.origin.position.y,
            info.resolution)
        mark_covered(self.covered, self.reachable, row, col, self.radius_cells)

    # ---------- Publication et CSV ----------
    def percent(self):
        if self.reachable is None:
            return 0.0
        return float(coverage_percent(self.covered, self.reachable))

    def build_coverage_map(self):
        msg = OccupancyGrid()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.map_frame
        msg.info = self.map_msg.info
        grid = np.full(self.reachable.shape, -1, dtype=np.int8)
        grid[self.reachable] = 0
        grid[self.covered & self.reachable] = 100
        msg.data = grid.flatten().tolist()
        return msg

    def on_status_timer(self):
        if self.finished or self.reachable is None:
            return
        elapsed = self.elapsed()
        pct = self.percent()

        status = CoverageStatus()
        status.stamp = self.get_clock().now().to_msg()
        status.strategy = self.strategy
        status.coverage_percent = pct
        status.distance_travelled = float(self.distance)
        status.elapsed_time = float(elapsed)
        status.near_collisions = int(self.near_collisions)
        self.status_pub.publish(status)
        self.map_pub.publish(self.build_coverage_map())

        if self.start_time is not None:
            self.write_csv_line(elapsed, pct)
            if elapsed >= self.run_duration:
                self.finish(pct, elapsed)

    def write_csv_line(self, elapsed, pct):
        if self.csv_file is None:
            return
        self.csv_file.write(
            f'{elapsed:.1f},{pct:.2f},{self.distance:.3f},'
            f'{self.near_collisions}\n')
        self.csv_file.flush()

    def finish(self, pct, elapsed):
        self.finished = True
        self.get_logger().info(f'fin du run : {pct:.1f} % en {elapsed:.0f} s')
        self.close_csv()

    def close_csv(self):
        if self.csv_file is not None and not self.csv_file.closed:
            self.csv_file.close()


def main(args=None):
    rclpy.init(args=args)
    node = CoverageTrackerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close_csv()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

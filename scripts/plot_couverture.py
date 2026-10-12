"""Carte de ce qui a vraiment été couvert en 10 min, pour A et pour B (simulation).

Rejoue un rosbag du protocole : positions /odom -> repère map, puis même marquage que le
coverage_tracker (disque de 2 cellules, seulement sur le masque atteignable de planning.py).
Le % recalculé est comparé au CSV officiel pour vérifier la reconstruction.
Écrit results/figures/couverture_A_B.png.
Usage (ROS sourcé) : python3 plot_couverture.py
"""
import glob
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Odometry

WS = os.path.expanduser('~/ros2_ws')
sys.path.insert(0, os.path.join(WS, 'src', 'aspi_bot'))
sys.path.insert(0, os.path.join(WS, 'scripts'))
from aspi_bot import planning  # noqa: E402
from plot_plans import load_map  # noqa: E402

BAGS = os.path.join(WS, 'results', 'bags')
SPAWN = (-2.0, -0.5)   # en simulation, odom est le repère du monde Gazebo ; map part du spawn
DURATION = 600.0       # durée mesurée par le tracker (s)
RADIUS_CELLS = 2       # rayon de nettoyage appliqué (0,10 m)


def odom_poses(bag_dir):
    """Liste (t, x, y) des messages /odom du rosbag, temps simulé en secondes."""
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=bag_dir, storage_id='sqlite3'),
                rosbag2_py.ConverterOptions('cdr', 'cdr'))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/odom']))
    poses = []
    while reader.has_next():
        _, data, _ = reader.read_next()
        msg = deserialize_message(data, Odometry)
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        poses.append((t, msg.pose.pose.position.x - SPAWN[0], msg.pose.pose.position.y - SPAWN[1]))
    return poses


def coverage(bag_name, reachable, ox, oy, res):
    poses = odom_poses(os.path.join(BAGS, bag_name))
    x0, y0 = poses[0][1], poses[0][2]
    # Le tracker démarre au premier déplacement de plus de 1 cm
    t0 = next(t for t, x, y in poses if math.hypot(x - x0, y - y0) > 0.01)
    covered = np.zeros_like(reachable)
    for t, x, y in poses:
        if t0 <= t <= t0 + DURATION:
            row, col = planning.world_to_cell(x, y, ox, oy, res)
            planning.mark_covered(covered, reachable, row, col, RADIUS_CELLS)
    return covered, planning.coverage_percent(covered, reachable)


def main():
    data, w, h, meta = load_map('world.yaml')
    res, (ox, oy) = meta['resolution'], meta['origin'][:2]
    free = planning.occupancy_to_free(data, w, h)
    reachable = planning.reachable_mask(free, planning.world_to_cell(0.0, 0.0, ox, oy, res), res)
    rows, cols = np.nonzero(free)
    print(f'pièce : {(cols.max() - cols.min() + 1) * res:.1f} m x {(rows.max() - rows.min() + 1) * res:.1f} m,'
          f' zone mesurée {reachable.sum() * res * res:.1f} m²')

    grid = np.asarray(data).reshape(h, w)
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    for ax, (bag, csv_name, title, color) in zip(axes, [
            ('RANDOM_1_fast', 'RANDOM_1_*.csv', 'A aléatoire, essai 1', (0.85, 0.45, 0.16)),
            ('BOUSTROPHEDON_1', 'BOUSTROPHEDON_1_*.csv', 'B planifié, essai 1', (0.12, 0.37, 0.60))]):
        covered, pct = coverage(bag, reachable, ox, oy, res)
        csv_path = glob.glob(os.path.join(WS, 'results', csv_name))[0]
        with open(csv_path) as f:
            official = float(f.read().strip().splitlines()[-1].split(',')[1])
        print(f'{title} : {pct:.1f} % recalculé, {official:.1f} % dans le CSV')
        img = np.ones((h, w, 3)) * 0.82
        img[grid == 0] = (0.97, 0.96, 0.93)
        img[grid >= 50] = (0.15, 0.17, 0.22)
        img[reachable] = (0.93, 0.90, 0.84)          # à couvrir, pas encore couvert
        img[covered] = color                          # couvert
        ax.imshow(img, origin='lower', extent=(ox, ox + w * res, oy, oy + h * res),
                  interpolation='nearest')
        ax.set_xlim(ox + cols.min() * res - 0.2, ox + (cols.max() + 1) * res + 0.2)
        ax.set_ylim(oy + rows.min() * res - 0.4, oy + (rows.max() + 1) * res + 0.2)
        xb, yb = ox + cols.min() * res, oy + rows.min() * res - 0.3   # barre d'échelle 1 m
        ax.plot([xb, xb + 1.0], [yb, yb], color='black', linewidth=4)
        ax.text(xb + 0.5, yb + 0.08, '1 m', ha='center', fontsize=20)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(WS, 'results', 'figures', 'couverture_A_B.png'), dpi=100)


if __name__ == '__main__':
    main()

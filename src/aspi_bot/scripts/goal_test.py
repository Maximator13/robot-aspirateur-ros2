#!/usr/bin/env python3
import math
import os
import sys

import numpy as np
import rclpy
import yaml
from geometry_msgs.msg import PoseStamped, Twist
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav_msgs.msg import Odometry, Path

from aspi_bot.planning import (cell_to_world, nearest_true_cell, occupancy_to_free,
                               reachable_mask, world_to_cell)

MOUVEMENT_MIN = 0.15
DUREE_MAX = 60.0


def lire_carte(chemin_yaml):
    meta = yaml.safe_load(open(chemin_yaml))
    pgm = os.path.join(os.path.dirname(chemin_yaml), meta['image'])
    brut = open(pgm, 'rb').read()
    champs, pos = [], 0
    while len(champs) < 4:
        while brut[pos:pos + 1].isspace():
            pos += 1
        if brut[pos:pos + 1] == b'#':
            pos = brut.index(b'\n', pos)
            continue
        fin = pos
        while not brut[fin:fin + 1].isspace():
            fin += 1
        champs.append(brut[pos:fin])
        pos = fin
    w, h = int(champs[1]), int(champs[2])
    img = np.frombuffer(brut[pos + 1:pos + 1 + w * h], dtype=np.uint8).reshape(h, w)
    img = img[::-1]
    occ = np.where(img > 250, 0, np.where(img < 50, 100, -1)).astype(np.int8)
    free = occupancy_to_free(occ.flatten(), w, h)
    ox, oy = meta['origin'][0], meta['origin'][1]
    return free, ox, oy, meta['resolution']


def choisir_but(chemin_yaml):
    free, ox, oy, res = lire_carte(chemin_yaml)
    depart = world_to_cell(0.0, 0.0, ox, oy, res)
    zone = reachable_mask(free, depart, res)
    if not zone.any():
        raise RuntimeError('aucune cellule atteignable depuis la croix (0, 0)')
    rows, cols = np.nonzero(zone)
    cell = nearest_true_cell(zone, int(rows.mean()), int(cols.mean()))
    return cell_to_world(cell[0], cell[1], ox, oy, res)


def main():
    statique = len(sys.argv) > 2 and sys.argv[2] == 'static'
    gx, gy = choisir_but(sys.argv[1])
    dist = math.hypot(gx, gy)
    print(f'[goal_test] but : ({gx:.2f}, {gy:.2f}), à {dist:.2f} m de la croix')
    if dist < MOUVEMENT_MIN * 1.5:
        print('[goal_test] but trop proche de la croix pour juger du mouvement : abandon')
        return 2

    rclpy.init()
    nav = BasicNavigator()
    odom = {}
    def sur_odom(m):
        q = m.pose.pose.orientation
        odom.update(x=m.pose.pose.position.x, y=m.pose.pose.position.y,
                    yaw=math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))
    nav.create_subscription(Odometry, '/odom', sur_odom, 10)

    cmd = {'/cmd_vel_nav': [], '/cmd_vel': []}
    for topic in cmd:
        nav.create_subscription(Twist, topic,
                                lambda m, t=topic: cmd[t].append((m.linear.x, m.angular.z)), 10)
    plan = {}
    nav.create_subscription(Path, '/plan', lambda m: plan.update(
        n=len(m.poses), poses=[(p.pose.position.x, p.pose.position.y) for p in m.poses]), 10)
    print('[goal_test] attente de Nav2 (pose initiale (0, 0, 0) = la croix)...')
    nav.waitUntilNav2Active(localizer='controller_server' if statique else 'amcl')
    while 'x' not in odom:
        rclpy.spin_once(nav, timeout_sec=0.2)
    x0, y0, yaw0 = odom['x'], odom['y'], odom['yaw']

    but = PoseStamped()
    but.header.frame_id = 'map'
    but.header.stamp = nav.get_clock().now().to_msg()
    but.pose.position.x, but.pose.position.y = gx, gy
    yaw = math.atan2(gy, gx)
    but.pose.orientation.z, but.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
    print('[goal_test] envoi du but : LE ROBOT VA BOUGER')
    nav.goToPose(but)
    t0 = nav.get_clock().now()
    prochain = 0.0
    while not nav.isTaskComplete():
        rclpy.spin_once(nav, timeout_sec=0.1)
        t = (nav.get_clock().now() - t0).nanoseconds * 1e-9
        if t >= prochain:
            prochain += 2.0
            c = cmd['/cmd_vel_nav'][-1] if cmd['/cmd_vel_nav'] else (0.0, 0.0)
            r = cmd['/cmd_vel'][-1] if cmd['/cmd_vel'] else (0.0, 0.0)
            print(f'[goal_test] t={t:4.1f}s odom=({odom["x"]:+.2f},{odom["y"]:+.2f}) '
                  f'cap={math.degrees(odom["yaw"]):+4.0f}° | contrôleur v={c[0]:+.2f} w={c[1]:+.2f} '
                  f'| robot v={r[0]:+.2f} w={r[1]:+.2f}')
        if t > DUREE_MAX:
            print(f'[goal_test] {DUREE_MAX:.0f} s écoulées : annulation')
            nav.cancelTask()
            break
    resultat = nav.getResult()
    for _ in range(10):
        rclpy.spin_once(nav, timeout_sec=0.1)
    bouge = math.hypot(odom['x'] - x0, odom['y'] - y0)
    print(f'[goal_test] statut Nav2 : {resultat}')
    tourne = math.degrees(abs(math.atan2(math.sin(odom['yaw'] - yaw0), math.cos(odom['yaw'] - yaw0))))
    print(f'[goal_test] déplacement RÉEL mesuré sur /odom : {bouge:.2f} m (but à {dist:.2f} m), '
          f'rotation nette {tourne:.0f}°')
    print(f'[goal_test] position finale : odom ({odom["x"]:.2f}, {odom["y"]:.2f}), but ({gx:.2f}, {gy:.2f})')
    for topic, msgs in cmd.items():
        if msgs:
            vmax = max(abs(v) for v, _ in msgs)
            wmax = max(abs(w) for _, w in msgs)
            avance = sum(1 for v, _ in msgs if abs(v) > 0.01)
            print(f'[goal_test] {topic} : {len(msgs)} messages, |v| max {vmax:.2f} m/s, |w| max {wmax:.2f} rad/s, '
                  f'{avance} messages avec v non nul')
        else:
            print(f'[goal_test] {topic} : AUCUN message reçu')
    if plan:
        p = plan['poses']
        long = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(p, p[1:]))
        print(f'[goal_test] /plan : {plan["n"]} points, longueur {long:.2f} m, '
              f'début ({p[0][0]:.2f},{p[0][1]:.2f}) fin ({p[-1][0]:.2f},{p[-1][1]:.2f})')
    else:
        print('[goal_test] /plan : aucun chemin reçu')
    ok = bouge >= MOUVEMENT_MIN
    if resultat == TaskResult.SUCCEEDED and not ok:
        print('[goal_test] FAUX SUCCÈS : Nav2 dit « réussi » mais le robot n\'a pas bougé (incident 10)')
    print('[goal_test] VERDICT : ' + ('MOUVEMENT RÉEL OK' if ok else 'PAS DE MOUVEMENT RÉEL'))
    rclpy.shutdown()
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

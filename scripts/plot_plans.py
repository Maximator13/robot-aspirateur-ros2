import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import yaml
from PIL import Image

WS = os.path.expanduser('~/ros2_ws')
sys.path.insert(0, os.path.join(WS, 'src', 'aspi_bot'))
from aspi_bot import planning

MAPS = os.path.join(WS, 'src', 'aspi_bot', 'maps')
OUT = os.path.join(WS, 'results', 'figures')


def load_map(yaml_name):
    with open(os.path.join(MAPS, yaml_name)) as f:
        meta = yaml.safe_load(f)
    pix = np.asarray(Image.open(os.path.join(MAPS, meta['image'])).convert('L'), dtype=float)
    p = (255.0 - pix) / 255.0
    data = np.full(pix.shape, -1, dtype=np.int16)
    data[p > meta['occupied_thresh']] = 100
    data[p < meta['free_thresh']] = 0
    data = np.flipud(data)
    h, w = data.shape
    return data.ravel(), w, h, meta


def plan(yaml_name, start, out_name):
    data, w, h, meta = load_map(yaml_name)
    res, (ox, oy) = meta['resolution'], meta['origin'][:2]
    free = planning.occupancy_to_free(data, w, h)
    start_cell = planning.world_to_cell(start[0], start[1], ox, oy, res)
    reachable = planning.reachable_mask(free, start_cell, res)
    wps = planning.boustrophedon_waypoints(reachable, ox, oy, res)
    xs = [wp[0] for wp in wps]
    ys = [wp[1] for wp in wps]

    grid = np.asarray(data).reshape(h, w)
    img = np.ones((h, w, 3)) * 0.82
    img[grid == 0] = (0.97, 0.96, 0.93)
    img[grid >= 50] = (0.15, 0.17, 0.22)
    img[reachable] = (0.93, 0.90, 0.84)
    extent = (ox, ox + w * res, oy, oy + h * res)

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(img, origin='lower', extent=extent, interpolation='nearest')
    ax.plot(xs, ys, color='#1F5F99', linewidth=2.2)
    ax.plot(start[0], start[1], marker='o', markersize=14, color='#B04A06')
    rows, cols = np.nonzero(reachable)
    ax.set_xlim(ox + cols.min() * res - 0.5, ox + (cols.max() + 1) * res + 0.5)
    ax.set_ylim(oy + rows.min() * res - 0.5, oy + (rows.max() + 1) * res + 0.5)
    xb = ox + cols.min() * res - 0.3
    yb = oy + rows.min() * res - 0.35
    ax.plot([xb, xb + 1.0], [yb, yb], color='black', linewidth=4)
    ax.text(xb + 0.5, yb + 0.06, '1 m', ha='center', fontsize=20)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, out_name), dpi=100)
    print(out_name, f'{int(reachable.sum())} cellules atteignables, {len(wps)} waypoints')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    plan('world.yaml', (0.0, 0.0), 'plan_simulation.png')
    plan('zone_reelle.yaml', (0.0, 0.0), 'plan_reel.png')

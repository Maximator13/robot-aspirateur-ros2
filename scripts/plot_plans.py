"""Dessine la carte et le trajet planifié par la stratégie B (pour le diaporama).

Même calcul que le nœud coverage_planner (fonctions de planning.py) :
carte -> masque libre -> masque atteignable depuis le départ -> lignes de balayage.
Écrit results/figures/plan_simulation.png et results/figures/plan_reel.png.
Usage : python3 plot_plans.py
"""
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
from aspi_bot import planning  # noqa: E402

MAPS = os.path.join(WS, 'src', 'aspi_bot', 'maps')
OUT = os.path.join(WS, 'results', 'figures')


def load_map(yaml_name):
    """Lit une carte map_server (mode trinary) et renvoie (data OccupancyGrid, largeur, hauteur, méta)."""
    with open(os.path.join(MAPS, yaml_name)) as f:
        meta = yaml.safe_load(f)
    pix = np.asarray(Image.open(os.path.join(MAPS, meta['image'])).convert('L'), dtype=float)
    p = (255.0 - pix) / 255.0  # probabilité d'occupation (negate: 0)
    data = np.full(pix.shape, -1, dtype=np.int16)
    data[p > meta['occupied_thresh']] = 100
    data[p < meta['free_thresh']] = 0
    data = np.flipud(data)  # l'image commence en haut, l'OccupancyGrid en bas
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
    img = np.ones((h, w, 3)) * 0.82          # inconnu : gris
    img[grid == 0] = (0.97, 0.96, 0.93)      # libre : clair
    img[grid >= 50] = (0.15, 0.17, 0.22)     # mur : foncé
    img[reachable] = (0.93, 0.90, 0.84)      # zone à couvrir (atteignable) : beige
    extent = (ox, ox + w * res, oy, oy + h * res)

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(img, origin='lower', extent=extent, interpolation='nearest')
    ax.plot(xs, ys, color='#1F5F99', linewidth=2.2)
    ax.plot(start[0], start[1], marker='o', markersize=14, color='#B04A06')
    rows, cols = np.nonzero(reachable)  # cadrage : zone atteignable + 0,5 m
    ax.set_xlim(ox + cols.min() * res - 0.5, ox + (cols.max() + 1) * res + 0.5)
    ax.set_ylim(oy + rows.min() * res - 0.5, oy + (rows.max() + 1) * res + 0.5)
    xb = ox + cols.min() * res - 0.3            # barre d'échelle 1 m sous la zone
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
    # Départ = origine de la carte (les deux cartes ont été faites depuis le point de départ)
    plan('world.yaml', (0.0, 0.0), 'plan_simulation.png')
    plan('zone_reelle.yaml', (0.0, 0.0), 'plan_reel.png')

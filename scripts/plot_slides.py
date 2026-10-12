"""Figures épurées pour le diaporama (une idée par figure, gros caractères).

Lit les CSV du tracker (temps, % couvert, distance, near_collisions) et écrit dans results/figures/ :
  slides_simulation.png : moyenne de A, moyenne de B1-B2, B3 à part ;
  slides_reel.png       : robot réel, A et B (moyenne des 2 essais, fourchette min-max) ;
  slides_jumeau.png     : distance parcourue, robot réel contre jumeau Gazebo.
Usage : python3 plot_slides.py   (depuis n'importe quel dossier)
"""
import csv
import glob
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

RES = os.path.expanduser('~/ros2_ws/results')
OUT = os.path.join(RES, 'figures')
ORANGE, BLUE, GREY = '#B04A06', '#1F5F99', '#8A909C'
plt.rcParams.update({'font.size': 20, 'axes.spines.top': False, 'axes.spines.right': False})


def read(path):
    """Renvoie (temps, % couvert, distance) d'un CSV du tracker."""
    with open(path) as f:
        rows = list(csv.DictReader(f))
    t = np.array([float(r['time']) for r in rows])
    c = np.array([float(r['coverage_percent']) for r in rows])
    d = np.array([float(r['distance']) for r in rows])
    return t, c, d


def on_grid(path, grid):
    """% couvert interpolé sur une grille de temps commune (valeur figée après la fin)."""
    t, c, _ = read(path)
    return np.interp(grid, t, c)


def finish(ax, xlabel, xmax):
    ax.axhline(80, color=GREY, linestyle=':', linewidth=2)
    ax.text(xmax, 81.5, 'objectif 80 %', color=GREY, ha='right', fontsize=18)
    ax.set_ylim(0, 100)
    ax.set_xlim(0, xmax)
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Surface couverte (%)')
    ax.grid(axis='y', alpha=0.3)


def simulation():
    grid = np.linspace(0, 600, 601)
    a = np.mean([on_grid(p, grid) for p in sorted(glob.glob(RES + '/RANDOM_*.csv'))], axis=0)
    b_paths = sorted(glob.glob(RES + '/BOUSTROPHEDON_*.csv'))
    b12 = np.mean([on_grid(p, grid) for p in b_paths[:2]], axis=0)
    b3 = on_grid(b_paths[2], grid)
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.plot(grid / 60, a, color=ORANGE, linewidth=4, label='A aléatoire (moyenne de 3 essais)')
    ax.plot(grid / 60, b12, color=BLUE, linewidth=4, label='B planifié (essais 1 et 2)')
    ax.plot(grid / 60, b3, color=BLUE, linewidth=3, linestyle='--', alpha=0.5, label='B essai 3 (bloqué)')
    finish(ax, 'Temps (min)', 10)
    ax.legend(loc='upper left', frameon=False)
    fig.tight_layout()
    fig.savefig(OUT + '/slides_simulation.png', dpi=100)


def reel():
    grid = np.linspace(0, 300, 301)
    a = np.array([on_grid(RES + '/robot_reel/' + n, grid) for n in
                  ('RANDOM_1_20261012-105211.csv', 'RANDOM_3_20261012-105805.csv')])
    b_files = ('BOUSTROPHEDON_1_20261012-103146.csv', 'BOUSTROPHEDON_2_20261012-110402.csv')
    t_end = min(read(RES + '/robot_reel/' + n)[0][-1] for n in b_files)  # B n°2 arrêté, trajet fini
    gb = grid[grid <= t_end]
    b = np.array([on_grid(RES + '/robot_reel/' + n, gb) for n in b_files])
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.fill_between(grid, a.min(0), a.max(0), color=ORANGE, alpha=0.2)
    ax.plot(grid, a.mean(0), color=ORANGE, linewidth=4, label='A aléatoire (2 essais)')
    ax.fill_between(gb, b.min(0), b.max(0), color=BLUE, alpha=0.2)
    ax.plot(gb, b.mean(0), color=BLUE, linewidth=4, label='B planifié (2 essais)')
    ax.annotate('trajet terminé', (gb[-1], b.mean(0)[-1]), xytext=(gb[-1] + 15, 88),
                fontsize=18, color=BLUE, arrowprops={'arrowstyle': '->', 'color': BLUE})
    finish(ax, 'Temps (s)', 300)
    ax.legend(loc='lower right', frameon=False)
    fig.tight_layout()
    fig.savefig(OUT + '/slides_reel.png', dpi=100)


def jumeau():
    dist = lambda p: read(p)[2][-1]
    real_a = np.mean([dist(RES + '/robot_reel/' + n) for n in
                      ('RANDOM_1_20261012-105211.csv', 'RANDOM_3_20261012-105805.csv')])
    real_b = np.mean([dist(RES + '/robot_reel/' + n) for n in
                      ('BOUSTROPHEDON_1_20261012-103146.csv', 'BOUSTROPHEDON_2_20261012-110402.csv')])
    twin_a = dist(RES + '/jumeau/RANDOM_1_20261012-112603.csv')
    twin_b = dist(RES + '/jumeau/BOUSTROPHEDON_1_20261012-113623.csv')
    fig, ax = plt.subplots(figsize=(12, 9))
    x = np.array([0, 1])
    ax.bar(x - 0.18, [real_a, real_b], 0.34, color=[ORANGE, BLUE], label='robot réel')
    ax.bar(x + 0.18, [twin_a, twin_b], 0.34, color=[ORANGE, BLUE], alpha=0.45, hatch='//',
           label='jumeau Gazebo')
    for xi, v in zip(np.r_[x - 0.18, x + 0.18], [real_a, real_b, twin_a, twin_b]):
        ax.text(xi, v + 0.4, f'{v:.1f} m'.replace('.', ','), ha='center', fontsize=20)
    ax.set_xticks(x, ['A aléatoire', 'B planifié'])
    ax.set_ylabel('Distance parcourue (m)')
    ax.set_ylim(0, 25)
    handles = [plt.Rectangle((0, 0), 1, 1, color=GREY), plt.Rectangle((0, 0), 1, 1, color=GREY, alpha=0.45, hatch='//')]
    ax.legend(handles, ['robot réel', 'jumeau Gazebo'], frameon=False)
    fig.tight_layout()
    fig.savefig(OUT + '/slides_jumeau.png', dpi=100)


def curves(series, xmax, out_name, legend_loc='lower right'):
    """Courbes simples : series = [(chemin CSV, libellé, couleur, style), ...]."""
    fig, ax = plt.subplots(figsize=(16, 9))
    for path, label, color, style in series:
        t, c, _ = read(path)
        keep = t <= xmax
        ax.plot(t[keep], c[keep], color=color, linewidth=4, linestyle=style, label=label)
    finish(ax, 'Temps (s)', xmax)
    ax.legend(loc=legend_loc, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, out_name), dpi=100)


def par_strategie():
    """Une figure par stratégie et par banc (robot réel, jumeau)."""
    R = RES + '/robot_reel/'
    J = RES + '/jumeau/'
    curves([(R + 'RANDOM_1_20261012-105211.csv', 'A, essai 1', ORANGE, '-'),
            (R + 'RANDOM_3_20261012-105805.csv', 'A, essai 2', ORANGE, ':')], 300, 'slides_reel_A.png')
    curves([(R + 'BOUSTROPHEDON_1_20261012-103146.csv', 'B, essai 1', BLUE, '-'),
            (R + 'BOUSTROPHEDON_2_20261012-110402.csv', 'B, essai 2 (arrêté, trajet fini)', BLUE, ':')],
           300, 'slides_reel_B.png')
    curves([(R + 'RANDOM_1_20261012-105211.csv', 'A robot réel, essai 1', ORANGE, '-'),
            (R + 'RANDOM_3_20261012-105805.csv', 'A robot réel, essai 2', ORANGE, ':'),
            (J + 'RANDOM_1_20261012-112603.csv', 'A jumeau Gazebo', GREY, '-')], 300, 'slides_jumeau_A.png')
    curves([(R + 'BOUSTROPHEDON_1_20261012-103146.csv', 'B suiveur, robot réel', BLUE, '-'),
            (J + 'BOUSTROPHEDON_1_20261012-113623.csv', 'B suiveur, jumeau Gazebo', GREY, '-'),
            (J + 'BOUSTROPHEDON_2_20261012-114404.csv', 'B avec Nav2, jumeau Gazebo', GREY, '--')],
           300, 'slides_jumeau_B.png')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    simulation()
    reel()
    jumeau()
    par_strategie()
    print('figures écrites dans', OUT)

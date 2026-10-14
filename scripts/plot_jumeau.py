#!/usr/bin/env python3
import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RACINE = Path(__file__).resolve().parent.parent / 'results'
DUREE = 300.0
RUNS = [
    ('A réel seed 1', 'robot_reel', 'RANDOM_1_20261012-105211', '#d95f02', '-'),
    ('A réel seed 3', 'robot_reel', 'RANDOM_3_20261012-105805', '#e6a35c', '-'),
    ('B réel n°1 (suiveur)', 'robot_reel', 'BOUSTROPHEDON_1_20261012-103146', '#1b6ca8', '-'),
    ('B réel n°2 (suiveur)', 'robot_reel', 'BOUSTROPHEDON_2_20261012-110402', '#6aa9d8', '-'),
    ('A jumeau seed 1', 'jumeau', 'RANDOM_1_20261012-112603', '#d95f02', '--'),
    ('B jumeau (suiveur)', 'jumeau', 'BOUSTROPHEDON_1_20261012-113623', '#1b6ca8', '--'),
    ('B Nav2 jumeau (bloqué)', 'jumeau', 'BOUSTROPHEDON_2_20261012-114404', '#777777', '--'),
]


def lire(dossier, nom):
    with open(RACINE / dossier / f'{nom}.csv', newline='') as f:
        lignes = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in lignes])
            for k in ('time', 'coverage_percent', 'distance', 'near_collisions')}


def fin_de_hausse(r):
    k = np.nonzero(np.diff(r['coverage_percent']) > 0)[0][-1] + 1
    return float(r['time'][k])


def main():
    donnees = {nom: lire(d, nom) for _, d, nom, _, _ in RUNS}
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
    for lab, _, nom, coul, st in RUNS:
        r = donnees[nom]
        t, c = r['time'], r['coverage_percent']
        ax.plot(t, c, color=coul, ls=st, lw=2, label=lab)
    ax.axhline(80, color='gray', ls=':', lw=1, label='80 %')
    ax.set_xlabel('Temps (s)')
    ax.set_ylabel('Surface couverte (%)')
    ax.set_title('Zone réelle en carton : robot réel (trait plein) et jumeau Gazebo (pointillés)')
    ax.set_xlim(0, DUREE)
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)
    ax.legend(loc='lower right', fontsize=8)
    fig.tight_layout()
    sortie = RACINE / 'figures' / 'jumeau_vs_reel.png'
    fig.savefig(sortie)
    print(f'Écrit : {sortie}\n')
    print('| Run | 30 s | 60 s | 120 s | % final (à) | 80 % | Dist. (m) | near_coll. | Dernière hausse |')
    print('|---|---|---|---|---|---|---|---|---|')
    for lab, _, nom, _, _ in RUNS:
        r = donnees[nom]
        t, c = r['time'], r['coverage_percent']
        v = [np.interp(x, t, c) for x in (30, 60, 120)]
        i80 = np.nonzero(c >= 80)[0]
        t80 = f'{t[i80[0]]:.0f} s' if i80.size else 'non atteint'
        print(f'| {lab} | {v[0]:.1f} | {v[1]:.1f} | {v[2]:.1f} | {c[-1]:.1f} % ({t[-1]:.0f} s) | {t80} | '
              f"{r['distance'][-1]:.1f} | {int(r['near_collisions'][-1])} | {fin_de_hausse(r):.0f} s |")


if __name__ == '__main__':
    main()

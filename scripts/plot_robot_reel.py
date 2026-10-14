#!/usr/bin/env python3
import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DOSSIER = Path(__file__).resolve().parent.parent / 'results' / 'robot_reel'
T_FIGE = 146.5
VALIDES = {
    'RANDOM_1_20261009-111324': ('seed 1, 11h13 (arrêt manuel à 249 s)', '#d95f02'),
    'RANDOM_2_20261009-120622': ('seed 2, 12h06 (arrêt manuel à 151 s)', '#1b6ca8'),
    'RANDOM_2_20261009-121427': ('seed 2, 12h14', '#1b9e77'),
}


def lire(nom):
    with open(DOSSIER / f'{nom}.csv', newline='') as f:
        lignes = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in lignes])
            for k in ('time', 'coverage_percent', 'distance', 'near_collisions')}


def main():
    fig, ax = plt.subplots(figsize=(8, 5))
    for nom, (etiquette, couleur) in VALIDES.items():
        d = lire(nom)
        t, c = d['time'], d['coverage_percent']
        if nom.endswith('121427'):
            m = t <= T_FIGE
            ax.plot(t[m], c[m], color=couleur, lw=2, label=etiquette + ' : mesuré jusqu\'à 146,5 s')
            ax.plot(t[~m | (t == t[m][-1])], c[~m | (t == t[m][-1])], color=couleur, lw=1.5,
                    ls=':', label='même run après 146,5 s : déplacement non mesuré')
        else:
            ax.plot(t, c, color=couleur, lw=2, label=etiquette)
    ax.axvline(T_FIGE, color='grey', lw=0.8, ls='--')
    ax.set_xlabel('Temps (s)')
    ax.set_ylabel('Zone couverte (%)')
    ax.set_title('Robot réel, stratégie aléatoire (zone en carton, 634 cellules)')
    ax.set_xlim(0, 300)
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)
    ax.legend(loc='lower right', fontsize=8)
    fig.tight_layout()
    sortie = DOSSIER / 'coverage_vs_time_reel.png'
    fig.savefig(sortie, dpi=150)
    print(f'Écrit : {sortie}')
    for nom in VALIDES:
        d = lire(nom)
        t = d['time']
        print(nom, [round(float(np.interp(x, t, d['coverage_percent'])), 1) for x in (60, 120, 146.5)],
              t[-1], d['distance'][-1], d['near_collisions'][-1])


if __name__ == '__main__':
    main()

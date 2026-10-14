#!/usr/bin/env python3
import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DOSSIER = Path(__file__).resolve().parent.parent / 'results' / 'robot_reel'
DUREE = 300.0
RUNS = {
    'RANDOM_1_20261012-105211': ('A seed 1', '#d95f02', '-', 'valide'),
    'RANDOM_3_20261012-105805': ('A seed 3', '#e6a35c', '-', 'valide'),
    'BOUSTROPHEDON_1_20261012-103146': ('B n°1 (10 h 31)', '#1b6ca8', '-', 'valide'),
    'BOUSTROPHEDON_2_20261012-110402': ('B n°2 (11 h 04)', '#6aa9d8', '-', 'valide'),
    'BOUSTROPHEDON_2_20261012-104557': ('B incident (10 h 45)', '#888888', '-', 'incident'),
}


def lire(nom):
    with open(DOSSIER / f'{nom}.csv', newline='') as f:
        lignes = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in lignes])
            for k in ('time', 'coverage_percent', 'distance', 'near_collisions')}


def instant_fin_de_hausse(r):
    k = np.nonzero(np.diff(r['coverage_percent']) > 0)[0][-1] + 1
    return float(r['time'][k])


def tableau(donnees):
    print('| Run | 30 s | 60 s | 120 s | % final (à) | 80 % | Dist. (m) | near_coll. | Dernière hausse de couverture |')
    print('|---|---|---|---|---|---|---|---|---|')
    for nom, (lab, _, _, statut) in RUNS.items():
        r = donnees[nom]
        t, c = r['time'], r['coverage_percent']
        v = [np.interp(x, t, c) for x in (30, 60, 120)]
        i80 = np.nonzero(c >= 80)[0]
        t80 = f'{t[i80[0]]:.0f} s' if i80.size else 'non atteint'
        print(f'| {lab} | {v[0]:.1f} | {v[1]:.1f} | {v[2]:.1f} | {c[-1]:.1f} % ({t[-1]:.0f} s) | {t80} | '
              f"{r['distance'][-1]:.1f} | {int(r['near_collisions'][-1])} | {instant_fin_de_hausse(r):.0f} s |")


def main():
    donnees = {nom: lire(nom) for nom in RUNS}
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
    for nom, (lab, coul, _, statut) in RUNS.items():
        r = donnees[nom]
        t, c = r['time'], r['coverage_percent']
        if statut == 'incident':
            ax.plot(t, c, color=coul, lw=1.4, ls='-.',
                    label=f'{lab} : incident, arrêté à {t[-1]:.0f} s (exclu)')
            continue
        if nom.startswith('BOUSTROPHEDON'):
            tf = instant_fin_de_hausse(r)
            masque = t <= tf
            ax.plot(t[masque], c[masque], color=coul, lw=2, label=f'{lab}')
            ax.plot([tf, DUREE], [c[-1], c[-1]], color=coul, lw=2, ls=':',
                    label=f'{lab} : valeur prolongée après la fin du trajet ({tf:.0f} s), non mesurée')
        else:
            ax.plot(t, c, color=coul, lw=2, label=lab)
    ax.axhline(80, color='gray', ls='--', lw=1, label='80 %')
    ax.set_xlabel('Temps (s)')
    ax.set_ylabel('Surface couverte (%)')
    ax.set_title('Robot réel, séance du 2026-10-12 : A (aléatoire) contre B (boustrophédon)')
    ax.set_xlim(0, DUREE)
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)
    ax.legend(loc='lower right', fontsize=7)
    fig.tight_layout()
    sortie = DOSSIER / 'coverage_vs_time_reel_12oct.png'
    fig.savefig(sortie)
    print(f'Écrit : {sortie}\n')
    tableau(donnees)


if __name__ == '__main__':
    main()

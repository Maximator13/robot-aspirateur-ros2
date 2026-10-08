#!/usr/bin/env python3
"""Analyse des CSV de résultats : courbe % couvert vs temps + tableau récapitulatif.

Usage :
    python3 scripts/plot_results.py [--results-dir DIR] [--duration 600]

Entrée : DIR/<STRATEGIE>_<seed>_<AAAAMMJJ-HHMMSS>.csv
         colonnes : time, coverage_percent, distance, near_collisions
Sortie : DIR/coverage_vs_time.png et DIR/summary.md
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')  # pas de fenêtre : on écrit seulement un PNG
import matplotlib.pyplot as plt

SEUIL = 80.0  # % de couverture visé
# Couleurs sobres, distinctes (y compris en niveaux de gris / daltonisme)
COULEURS = {'RANDOM': '#d95f02', 'BOUSTROPHEDON': '#1b6ca8'}
COULEUR_DEFAUT = '#555555'


def parse_nom(path):
    """Déduit (stratégie, seed) du nom <STRATEGIE>_<seed>_<date>.csv."""
    parts = path.stem.split('_')
    strategie = parts[0].upper()
    seed = parts[1] if len(parts) > 1 else '?'
    return strategie, seed


def lire_run(path):
    """Lit un CSV. Retourne un dict de tableaux numpy, ou None si vide/illisible."""
    try:
        with open(path, newline='') as f:
            lignes = list(csv.DictReader(f))
        if not lignes:
            raise ValueError('fichier vide')
        t = np.array([float(r['time']) for r in lignes])
        cov = np.array([float(r['coverage_percent']) for r in lignes])
        dist = np.array([float(r['distance']) for r in lignes])
        nc = np.array([float(r['near_collisions']) for r in lignes])
    except (OSError, ValueError, KeyError) as e:
        print(f'AVERTISSEMENT : {path.name} ignoré ({e})', file=sys.stderr)
        return None
    strategie, seed = parse_nom(path)
    return {'strategie': strategie, 'seed': seed, 't': t, 'cov': cov,
            'dist': dist, 'nc': nc}


def temps_pour_seuil(run, seuil=SEUIL):
    """Premier instant où la couverture atteint le seuil, ou None."""
    idx = np.nonzero(run['cov'] >= seuil)[0]
    return float(run['t'][idx[0]]) if idx.size else None


def courbe_sur_grille(run, grille):
    """Interpole la couverture sur la grille commune.

    Choix : la grille va jusqu'à --duration. Un run plus court est prolongé par
    sa dernière valeur (la couverture ne baisse jamais : un run fini garde son
    résultat). Cela évite de tronquer tous les runs au plus court.
    np.interp garde déjà la dernière valeur à droite.
    """
    return np.interp(grille, run['t'], run['cov'])


def tracer(runs_par_strat, duration, sortie):
    """Trace moyenne + enveloppe min/max + runs individuels par stratégie."""
    grille = np.arange(0, duration + 1, 1.0)
    x = grille / 60.0  # minutes
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
    for strat, runs in sorted(runs_par_strat.items()):
        c = COULEURS.get(strat, COULEUR_DEFAUT)
        courbes = np.array([courbe_sur_grille(r, grille) for r in runs])
        for y in courbes:
            ax.plot(x, y, color=c, lw=0.8, alpha=0.5)
        ax.fill_between(x, courbes.min(axis=0), courbes.max(axis=0),
                        color=c, alpha=0.2)
        ax.plot(x, courbes.mean(axis=0), color=c, lw=2.5,
                label=f'{strat} (moyenne, {len(runs)} run{"s" if len(runs) > 1 else ""})')
    ax.axhline(SEUIL, color='gray', ls='--', lw=1, label=f'{SEUIL:.0f} %')
    ax.set_xlabel('Temps simulé (min)')
    ax.set_ylabel('Surface couverte (%)')
    ax.set_title('Couverture en fonction du temps : stratégie aléatoire vs planifiée')
    ax.set_xlim(0, duration / 60.0)
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)
    ax.legend(loc='lower right')
    fig.tight_layout()
    fig.savefig(sortie)
    plt.close(fig)


def fmt_temps(t):
    return 'non atteint' if t is None else f'{t:.0f} s'


def ligne_run(r):
    t80 = temps_pour_seuil(r)
    return (f"| {r['strategie']} | {r['seed']} | {r['t'][-1]:.0f} s | "
            f"{r['cov'][-1]:.1f} % | {fmt_temps(t80)} | "
            f"{r['dist'][-1]:.1f} | {int(r['nc'][-1])} |")


def ligne_moyenne(strat, runs):
    """Ligne moyenne ± écart-type (temps 80 % : sur les runs qui l'atteignent)."""
    def ms(vals, fmt):
        v = np.array(vals, dtype=float)
        sd = v.std(ddof=1) if len(v) > 1 else 0.0
        return f'{fmt.format(v.mean())} ± {fmt.format(sd)}'
    t80 = [temps_pour_seuil(r) for r in runs]
    atteints = [t for t in t80 if t is not None]
    txt80 = (f'{ms(atteints, "{:.0f}")} s ({len(atteints)}/{len(runs)} runs)'
             if atteints else 'non atteint')
    return (f"| **{strat} moyenne** | n={len(runs)} | "
            f"{ms([r['t'][-1] for r in runs], '{:.0f}')} s | "
            f"{ms([r['cov'][-1] for r in runs], '{:.1f}')} % | {txt80} | "
            f"{ms([r['dist'][-1] for r in runs], '{:.1f}')} | "
            f"{ms([r['nc'][-1] for r in runs], '{:.1f}')} |")


def construire_tableau(runs_par_strat):
    """Tableau Markdown : une ligne par run, puis moyenne ± écart-type."""
    out = ['| Stratégie | Seed | Durée | % final | Temps pour 80 % | Distance (m) | near_collisions |',
           '|---|---|---|---|---|---|---|']
    for strat, runs in sorted(runs_par_strat.items()):
        out += [ligne_run(r) for r in runs]
        out.append(ligne_moyenne(strat, runs))
    return '\n'.join(out) + '\n'


def main():
    racine = Path(__file__).resolve().parent.parent / 'results'
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--results-dir', type=Path, default=racine)
    ap.add_argument('--duration', type=float, default=600,
                    help='durée de la grille de temps en s (défaut 600)')
    args = ap.parse_args()

    runs_par_strat = {}
    for p in sorted(args.results_dir.glob('*.csv')):
        run = lire_run(p)
        if run is not None:
            runs_par_strat.setdefault(run['strategie'], []).append(run)
    if not runs_par_strat:
        sys.exit(f'Aucun CSV exploitable dans {args.results_dir}')

    png = args.results_dir / 'coverage_vs_time.png'
    tracer(runs_par_strat, args.duration, png)
    tableau = construire_tableau(runs_par_strat)
    (args.results_dir / 'summary.md').write_text(
        '# Résumé des runs\n\n' + tableau, encoding='utf-8')
    print(tableau)
    print(f'Écrit : {png} et {args.results_dir / "summary.md"}')


if __name__ == '__main__':
    main()

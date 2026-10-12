#!/usr/bin/env python3
"""Génère un monde Gazebo (SDF 1.6) à partir d'une carte map_server (.yaml + .pgm).

But : un « jumeau numérique » de la zone réelle en carton. Chaque cellule « mur »
de la carte devient un morceau de boîte statique ; les cellules libres ou inconnues
ne génèrent rien.

Usage :
    python3 make_world_from_map.py CARTE.yaml SORTIE.world [--hauteur 0.25] [--seuil-occupe 0.65]

Algorithme de regroupement (glouton, exact) :
  1. sur chaque ligne de la grille, les cellules murs contiguës forment un segment [c0, c1) ;
  2. un segment identique (mêmes c0, c1) sur la ligne suivante prolonge le rectangle en cours ;
  3. sinon le rectangle en cours est fermé et un nouveau commence ;
  4. chaque cellule mur appartient à exactement une boîte (pas de trou, pas de recouvrement) ;
  5. coût O(H x W).

Repères : l'image PGM a sa ligne 0 en HAUT ; on la retourne pour que la ligne 0 de
la grille soit en BAS (convention OccupancyGrid). Le centre de la cellule (ligne, col)
est alors en x = origin_x + (col + 0.5) * res, y = origin_y + (ligne + 0.5) * res.
On suppose un yaw d'origine nul (cas des cartes map_saver).

Limites (à connaître) :
- les murs ont l'épaisseur des cellules de la carte (résolution, ex. 0,05 m), pas celle du carton réel ;
- les cellules inconnues ne créent pas de mur : un trou dans la carte devient une ouverture dans
  Gazebo (vérifier que la zone est fermée) ;
- le yaw d'origine doit être nul (vérifié au chargement).
"""

import argparse
import os

import numpy as np
import yaml


# ---------------------------------------------------------------------------
# Lecture de la carte
# ---------------------------------------------------------------------------

def lire_pgm(chemin):
    """Lit un PGM binaire (P5, 8 bits) à la main et renvoie un tableau numpy (H, W).

    Ligne 0 du tableau = ligne du HAUT de l'image (convention image).
    """
    with open(chemin, 'rb') as f:
        donnees = f.read()
    # L'en-tête contient 4 champs (P5, largeur, hauteur, maxval), avec des commentaires '#' possibles.
    champs = []
    i = 0
    while len(champs) < 4:
        # Sauter les espaces
        while donnees[i:i + 1].isspace():
            i += 1
        # Sauter un commentaire jusqu'à la fin de ligne
        if donnees[i:i + 1] == b'#':
            while donnees[i:i + 1] not in (b'\n', b''):
                i += 1
            continue
        debut = i
        while not donnees[i:i + 1].isspace():
            i += 1
        champs.append(donnees[debut:i])
    i += 1  # un seul blanc sépare l'en-tête des pixels
    if champs[0] != b'P5':
        raise ValueError(f'{chemin} : seul le format PGM binaire P5 est géré')
    largeur, hauteur, maxval = int(champs[1]), int(champs[2]), int(champs[3])
    if maxval > 255:
        raise ValueError(f'{chemin} : PGM 16 bits non géré')
    pixels = np.frombuffer(donnees, dtype=np.uint8, count=largeur * hauteur, offset=i)
    return pixels.reshape(hauteur, largeur)


def lire_carte(chemin_yaml):
    """Lit le yaml map_server et l'image. Renvoie (image retournée, résolution, origine, méta)."""
    with open(chemin_yaml, 'r') as f:
        meta = yaml.safe_load(f)
    chemin_image = meta['image']
    if not os.path.isabs(chemin_image):
        # Le chemin de l'image est relatif au dossier du yaml
        chemin_image = os.path.join(os.path.dirname(os.path.abspath(chemin_yaml)), chemin_image)
    image = lire_pgm(chemin_image)
    # Retournement vertical : ligne 0 = BAS de la carte (comme l'OccupancyGrid)
    image = np.flipud(image)
    resolution = float(meta['resolution'])
    origine = (float(meta['origin'][0]), float(meta['origin'][1]))
    # Une carte tournée n'est pas gérée : les boîtes seraient mal placées
    assert len(meta['origin']) < 3 or float(meta['origin'][2]) == 0.0, 'yaw d\'origine non nul'
    return image, resolution, origine, meta


def masque_murs(image, seuil_occupe, negate=0):
    """Renvoie un masque booléen : True = mur.

    p = (255 - v) / 255 (ou v / 255 si negate) ; mur si p > seuil_occupe.
    Les cellules inconnues (gris) ou libres ne sont pas des murs.
    """
    v = image.astype(np.float64)
    p = v / 255.0 if negate else (255.0 - v) / 255.0
    return p > seuil_occupe


# ---------------------------------------------------------------------------
# Regroupement des cellules en boîtes
# ---------------------------------------------------------------------------

def segments_ligne(ligne):
    """Liste des segments [c0, c1) de True contigus dans une ligne booléenne."""
    segments = []
    c = 0
    n = len(ligne)
    while c < n:
        if ligne[c]:
            c0 = c
            while c < n and ligne[c]:
                c += 1
            segments.append((c0, c))
        else:
            c += 1
    return segments


def regrouper_en_boites(murs):
    """Regroupe les cellules murs en rectangles (ligne0, ligne1, col0, col1), bornes hautes exclues.

    Glouton : segments horizontaux par ligne, puis fusion verticale des segments
    identiques empilés.
    """
    boites = []
    ouverts = {}  # (c0, c1) -> ligne de début du rectangle en cours
    for r in range(murs.shape[0]):
        segs = set(segments_ligne(murs[r]))
        # Fermer les rectangles qui ne continuent pas sur cette ligne
        for cle in list(ouverts):
            if cle not in segs:
                boites.append((ouverts.pop(cle), r, cle[0], cle[1]))
        # Ouvrir les nouveaux segments (ceux déjà ouverts se prolongent tout seuls)
        for cle in segs:
            if cle not in ouverts:
                ouverts[cle] = r
    # Fermer ce qui reste ouvert en haut de la grille
    for cle, r0 in ouverts.items():
        boites.append((r0, murs.shape[0], cle[0], cle[1]))
    return boites


# ---------------------------------------------------------------------------
# Écriture du monde SDF
# ---------------------------------------------------------------------------

# Bloc <physics> recopié de turtlebot3_gazebo/worlds/turtlebot3_world.world
PHYSIQUE = """    <physics type="ode">
      <real_time_update_rate>1000.0</real_time_update_rate>
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1</real_time_factor>
      <ode>
        <solver>
          <type>quick</type>
          <iters>150</iters>
          <precon_iters>0</precon_iters>
          <sor>1.400000</sor>
          <use_dynamic_moi_rescaling>1</use_dynamic_moi_rescaling>
        </solver>
        <constraints>
          <cfm>0.00001</cfm>
          <erp>0.2</erp>
          <contact_max_correcting_vel>2000.000000</contact_max_correcting_vel>
          <contact_surface_layer>0.01000</contact_surface_layer>
        </constraints>
      </ode>
    </physics>
"""

# Couleur carton (RGBA)
COULEUR_CARTON = '0.72 0.55 0.36 1'


def boite_vers_sdf(i, boite, resolution, origine, hauteur):
    """Texte SDF (collision + visual) d'une boîte, positionnée dans le repère de la carte."""
    r0, r1, c0, c1 = boite
    # Centre du rectangle = milieu entre le bord bas/gauche et le bord haut/droit
    x = origine[0] + 0.5 * (c0 + c1) * resolution
    y = origine[1] + 0.5 * (r0 + r1) * resolution
    sx = (c1 - c0) * resolution
    sy = (r1 - r0) * resolution
    pose = f'{x:.4f} {y:.4f} {hauteur / 2:.4f} 0 0 0'
    taille = f'{sx:.4f} {sy:.4f} {hauteur:.4f}'
    return f"""        <collision name="collision_{i}">
          <pose>{pose}</pose>
          <geometry><box><size>{taille}</size></box></geometry>
        </collision>
        <visual name="visual_{i}">
          <pose>{pose}</pose>
          <geometry><box><size>{taille}</size></box></geometry>
          <material>
            <ambient>{COULEUR_CARTON}</ambient>
            <diffuse>{COULEUR_CARTON}</diffuse>
          </material>
        </visual>
"""


def monde_sdf(boites, resolution, origine, hauteur):
    """Texte complet du monde : sol, soleil, physique, modèle statique zone_reelle."""
    corps = ''.join(boite_vers_sdf(i, b, resolution, origine, hauteur)
                    for i, b in enumerate(boites))
    return f"""<?xml version="1.0"?>
<!-- Monde généré par make_world_from_map.py : jumeau de la zone réelle en carton. -->
<sdf version="1.6">
  <world name="default">

    <include>
      <uri>model://ground_plane</uri>
    </include>

    <include>
      <uri>model://sun</uri>
    </include>

    <scene>
      <shadows>false</shadows>
    </scene>

{PHYSIQUE}
    <model name="zone_reelle">
      <static>1</static>
      <pose>0 0 0 0 0 0</pose>
      <link name="murs">
{corps}      </link>
    </model>

  </world>
</sdf>
"""


def main():
    parser = argparse.ArgumentParser(description='Carte map_server -> monde Gazebo SDF 1.6')
    parser.add_argument('carte', help='fichier .yaml de la carte')
    parser.add_argument('sortie', help='fichier .world à écrire')
    parser.add_argument('--hauteur', type=float, default=0.25, help='hauteur des murs (m)')
    parser.add_argument('--seuil-occupe', type=float, default=None,
                        help='seuil p au-delà duquel une cellule est un mur '
                             '(défaut : occupied_thresh du yaml, sinon 0.65)')
    args = parser.parse_args()

    image, resolution, origine, meta = lire_carte(args.carte)
    seuil = args.seuil_occupe
    if seuil is None:
        seuil = float(meta.get('occupied_thresh', 0.65))
    murs = masque_murs(image, seuil, int(meta.get('negate', 0)))
    boites = regrouper_en_boites(murs)

    if not boites:
        print('Attention : aucune cellule mur, le monde ne contiendra que le sol.')

    with open(args.sortie, 'w') as f:
        f.write(monde_sdf(boites, resolution, origine, args.hauteur))

    print(f'Grille : {image.shape[1]} x {image.shape[0]} cellules, résolution {resolution} m')
    print(f'Cellules murs : {int(murs.sum())}')
    print(f'Boîtes générées : {len(boites)}')
    print(f'Monde écrit : {args.sortie}')


if __name__ == '__main__':
    main()

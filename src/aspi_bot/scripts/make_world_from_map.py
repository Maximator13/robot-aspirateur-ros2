#!/usr/bin/env python3

import argparse
import os

import numpy as np
import yaml


def lire_pgm(chemin):
    with open(chemin, 'rb') as f:
        donnees = f.read()
    champs = []
    i = 0
    while len(champs) < 4:
        while donnees[i:i + 1].isspace():
            i += 1
        if donnees[i:i + 1] == b'#':
            while donnees[i:i + 1] not in (b'\n', b''):
                i += 1
            continue
        debut = i
        while not donnees[i:i + 1].isspace():
            i += 1
        champs.append(donnees[debut:i])
    i += 1
    if champs[0] != b'P5':
        raise ValueError(f'{chemin} : seul le format PGM binaire P5 est géré')
    largeur, hauteur, maxval = int(champs[1]), int(champs[2]), int(champs[3])
    if maxval > 255:
        raise ValueError(f'{chemin} : PGM 16 bits non géré')
    pixels = np.frombuffer(donnees, dtype=np.uint8, count=largeur * hauteur, offset=i)
    return pixels.reshape(hauteur, largeur)


def lire_carte(chemin_yaml):
    with open(chemin_yaml, 'r') as f:
        meta = yaml.safe_load(f)
    chemin_image = meta['image']
    if not os.path.isabs(chemin_image):
        chemin_image = os.path.join(os.path.dirname(os.path.abspath(chemin_yaml)), chemin_image)
    image = lire_pgm(chemin_image)
    image = np.flipud(image)
    resolution = float(meta['resolution'])
    origine = (float(meta['origin'][0]), float(meta['origin'][1]))
    assert len(meta['origin']) < 3 or float(meta['origin'][2]) == 0.0, 'yaw d\'origine non nul'
    return image, resolution, origine, meta


def masque_murs(image, seuil_occupe, negate=0):
    v = image.astype(np.float64)
    p = v / 255.0 if negate else (255.0 - v) / 255.0
    return p > seuil_occupe


def segments_ligne(ligne):
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
    boites = []
    ouverts = {}
    for r in range(murs.shape[0]):
        segs = set(segments_ligne(murs[r]))
        for cle in list(ouverts):
            if cle not in segs:
                boites.append((ouverts.pop(cle), r, cle[0], cle[1]))
        for cle in segs:
            if cle not in ouverts:
                ouverts[cle] = r
    for cle, r0 in ouverts.items():
        boites.append((r0, murs.shape[0], cle[0], cle[1]))
    return boites


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

COULEUR_CARTON = '0.72 0.55 0.36 1'


def boite_vers_sdf(i, boite, resolution, origine, hauteur):
    r0, r1, c0, c1 = boite
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

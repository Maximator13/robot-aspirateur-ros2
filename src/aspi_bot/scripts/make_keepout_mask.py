#!/usr/bin/env python3
import argparse
import os
import sys

import numpy as np

FREE_PIXEL = 254
OCC_PIXEL = 0


def read_pgm(path):
    with open(path, 'rb') as f:
        raw = f.read()
    tokens, pos = [], 0
    while len(tokens) < 4:
        while raw[pos:pos + 1].isspace():
            pos += 1
        if raw[pos:pos + 1] == b'#':
            while raw[pos:pos + 1] != b'\n':
                pos += 1
            continue
        start = pos
        while not raw[pos:pos + 1].isspace():
            pos += 1
        tokens.append(raw[start:pos])
    pos += 1
    if tokens[0] != b'P5' or int(tokens[3]) > 255:
        raise ValueError('PGM P5 8 bits attendu')
    width, height = int(tokens[1]), int(tokens[2])
    data = np.frombuffer(raw, dtype=np.uint8, count=width * height, offset=pos)
    return data.reshape(height, width)


def write_pgm(path, image):
    height, width = image.shape
    with open(path, 'wb') as f:
        f.write(f'P5\n{width} {height}\n255\n'.encode())
        f.write(image.astype(np.uint8).tobytes())


def read_map_yaml(path):
    info = {}
    with open(path) as f:
        for line in f:
            line = line.split('#')[0].strip()
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip()] = value.strip()
    return {
        'image': info['image'],
        'resolution': float(info['resolution']),
        'origin': [float(v) for v in info['origin'].strip('[]').split(',')],
        'mode': info.get('mode', 'trinary'),
        'negate': info.get('negate', '0'),
        'occupied_thresh': info.get('occupied_thresh', '0.65'),
        'free_thresh': info.get('free_thresh', '0.25'),
    }


def make_mask(height, width, origin_x, origin_y, resolution, rect):
    xmin, ymin, xmax, ymax = rect
    x = origin_x + (np.arange(width) + 0.5) * resolution
    y = origin_y + (height - 1 - np.arange(height) + 0.5) * resolution
    in_x = (x >= xmin) & (x <= xmax)
    in_y = (y >= ymin) & (y <= ymax)
    inside = in_y[:, None] & in_x[None, :]
    return np.where(inside, FREE_PIXEL, OCC_PIXEL).astype(np.uint8)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('carte', help='yaml de la carte de référence')
    parser.add_argument('xmin', type=float)
    parser.add_argument('ymin', type=float)
    parser.add_argument('xmax', type=float)
    parser.add_argument('ymax', type=float)
    parser.add_argument('--sortie', default=None,
                        help='dossier de sortie (défaut : dossier de la carte)')
    parser.add_argument('--nom', default='keepout', help='nom des fichiers (sans extension)')
    parser.add_argument('--depart', type=float, nargs=2, default=[0.0, 0.0],
                        metavar=('X', 'Y'), help='point de départ du robot (défaut : 0 0)')
    parser.add_argument('--marge', type=float, default=0.5,
                        help='marge minimale (m) entre le départ et le bord de la zone')
    args = parser.parse_args()
    if args.xmin >= args.xmax or args.ymin >= args.ymax:
        parser.error('rectangle invalide : il faut xmin < xmax et ymin < ymax')

    dx, dy = args.depart
    bord = min(dx - args.xmin, args.xmax - dx, dy - args.ymin, args.ymax - dy)
    if bord < args.marge:
        print(f'ERREUR : le point de départ ({dx}, {dy}) est à {bord:.2f} m du bord de la '
              f'zone autorisée (ou dehors) ; marge minimale exigée : {args.marge} m. '
              'Sinon le robot ne bouge pas (collision détectée dès le premier pas). '
              'Agrandissez la zone ou donnez --depart X Y / --marge.', file=sys.stderr)
        sys.exit(1)

    info = read_map_yaml(args.carte)
    map_dir = os.path.dirname(os.path.abspath(args.carte))
    image = read_pgm(os.path.join(map_dir, info['image']))
    height, width = image.shape
    mask = make_mask(height, width, info['origin'][0], info['origin'][1],
                     info['resolution'], (args.xmin, args.ymin, args.xmax, args.ymax))

    out_dir = args.sortie or map_dir
    os.makedirs(out_dir, exist_ok=True)
    write_pgm(os.path.join(out_dir, args.nom + '.pgm'), mask)
    with open(os.path.join(out_dir, args.nom + '.yaml'), 'w') as f:
        f.write(f'image: {args.nom}.pgm\n'
                f'mode: {info["mode"]}\n'
                f'resolution: {info["resolution"]}\n'
                f'origin: {info["origin"]}\n'
                f'negate: {info["negate"]}\n'
                f'occupied_thresh: {info["occupied_thresh"]}\n'
                f'free_thresh: {info["free_thresh"]}\n')
    n_free = int((mask == FREE_PIXEL).sum())
    print(f'{args.nom}.yaml/.pgm écrits dans {out_dir} : {width}x{height}, '
          f'{n_free} cellules autorisées ({n_free * info["resolution"] ** 2:.2f} m2)')


if __name__ == '__main__':
    main()

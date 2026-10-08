"""Algorithmes de couverture en Python pur (numpy, aucun import ROS).

Utilisé par :
- coverage_planner (stratégie B) : masque atteignable + balayage boustrophédon ;
- coverage_tracker (stratégies A et B) : même masque atteignable comme dénominateur
  du % couvert, marquage des cellules nettoyées.

Convention des grilles : tableau numpy de forme (height, width), indexé [row, col].
`row` correspond à y croissant et `col` à x croissant, comme OccupancyGrid.data
(stocké ligne par ligne, cellule (0, 0) = coin en bas à gauche, à `origin`).
La rotation de l'origine de la carte est ignorée (elle vaut 0 avec map_server).

Principe et complexité (N = nb de cellules, K = nb de cellules du disque d'érosion) :
- occupancy_to_free : seuillage, O(N).
- érosion par un disque : ET logique de K décalages de la grille, O(N.K).
- composante connexe : parcours en largeur (BFS) 4-voisinage, O(N).
- boustrophédon : une ligne sur `spacing`, découpée en segments contigus, O(N).
"""

import math
from collections import deque

import numpy as np


# ---------------------------------------------------------------------------
# Conversion carte <-> numpy, monde <-> cellule
# ---------------------------------------------------------------------------

def occupancy_to_free(data, width, height, occupied_threshold=50):
    """Convertit OccupancyGrid.data en masque booléen (True = libre).

    Valeurs : 0..100 = probabilité d'occupation, -1 = inconnu.
    L'inconnu (-1) est traité comme obstacle (prudent : on ne nettoie pas
    ce qu'on ne connaît pas). Une cellule est libre si 0 <= valeur < seuil.
    """
    if width * height == 0:
        return np.zeros((height, width), dtype=bool)
    grid = np.asarray(data, dtype=np.int16).reshape(height, width)
    return (grid >= 0) & (grid < occupied_threshold)


def world_to_cell(x, y, origin_x, origin_y, resolution):
    """Coordonnées monde (m) -> (row, col) de la cellule qui contient le point.

    floor (et non int()) pour rester correct aux coordonnées négatives.
    Pas de clamp : l'appelant doit vérifier les bornes avec in_bounds().
    """
    col = int(math.floor((x - origin_x) / resolution))
    row = int(math.floor((y - origin_y) / resolution))
    return row, col


def cell_to_world(row, col, origin_x, origin_y, resolution):
    """(row, col) -> coordonnées monde (m) du centre de la cellule."""
    x = origin_x + (col + 0.5) * resolution
    y = origin_y + (row + 0.5) * resolution
    return x, y


def in_bounds(grid, row, col):
    """True si (row, col) est une cellule valide de la grille."""
    height, width = grid.shape
    return 0 <= row < height and 0 <= col < width


# ---------------------------------------------------------------------------
# Disque, érosion, composante connexe
# ---------------------------------------------------------------------------

def disk_offsets(radius_cells):
    """Décalages (drow, dcol) des cellules d'un disque de rayon radius_cells.

    Une cellule appartient au disque si drow² + dcol² <= rayon².
    Rayon 0 -> seulement la cellule centrale. Renvoie un tableau (N, 2) d'entiers.
    """
    r = int(math.floor(radius_cells))
    offsets = [(dr, dc)
               for dr in range(-r, r + 1)
               for dc in range(-r, r + 1)
               if dr * dr + dc * dc <= radius_cells * radius_cells]
    return np.array(offsets, dtype=int).reshape(-1, 2)


def erode(free, radius_cells):
    """Érosion de l'espace libre par un disque (sans scipy).

    Une cellule reste libre si TOUT le disque centré sur elle est libre :
    c'est le ET logique de la grille décalée de chaque offset du disque.
    Les bords de la carte sont traités comme des obstacles (padding à False).
    """
    r = int(math.floor(radius_cells))
    height, width = free.shape
    padded = np.zeros((height + 2 * r, width + 2 * r), dtype=bool)
    padded[r:r + height, r:r + width] = free
    result = free.copy()
    for dr, dc in disk_offsets(radius_cells):
        result &= padded[r + dr:r + dr + height, r + dc:r + dc + width]
    return result


def nearest_true_cell(mask, row, col):
    """Cellule True de `mask` la plus proche de (row, col), ou None si aucune."""
    cells = np.argwhere(mask)
    if len(cells) == 0:
        return None
    dist2 = (cells[:, 0] - row) ** 2 + (cells[:, 1] - col) ** 2
    best = cells[int(np.argmin(dist2))]
    return int(best[0]), int(best[1])


def connected_component(mask, start_cell):
    """Composante connexe (4-voisinage) de `mask` contenant start_cell (BFS)."""
    component = np.zeros_like(mask, dtype=bool)
    row0, col0 = start_cell
    if not in_bounds(mask, row0, col0) or not mask[row0, col0]:
        return component
    component[row0, col0] = True
    queue = deque([start_cell])
    while queue:
        row, col = queue.popleft()
        for nr, nc in ((row + 1, col), (row - 1, col), (row, col + 1), (row, col - 1)):
            if in_bounds(mask, nr, nc) and mask[nr, nc] and not component[nr, nc]:
                component[nr, nc] = True
                queue.append((nr, nc))
    return component


def erosion_radius_cells(resolution, robot_radius=0.105, safety_margin=0.05):
    """Rayon d'érosion en cellules : ceil((robot_radius + safety_margin) / resolution).

    Arrondi au supérieur = choix prudent : on érode au moins de la marge demandée,
    quitte à perdre un peu de surface. Le -1e-9 évite qu'une erreur flottante
    (ex. 0.15 / 0.05 = 3.0000000000000004) ajoute une cellule de trop.
    """
    return int(math.ceil((robot_radius + safety_margin) / resolution - 1e-9))


def reachable_mask(free, start_cell, resolution, robot_radius=0.105, safety_margin=0.05):
    """Masque des cellules où le centre du robot peut aller depuis start_cell.

    1. Érosion de l'espace libre par un disque de (robot_radius + safety_margin).
    2. Si start_cell n'est pas libre après érosion (robot collé à un mur, hors
       carte...), on part de la cellule érodée libre la plus proche.
    3. Composante connexe (4-voisinage) contenant ce point de départ.
    Renvoie un masque vide si aucune cellule ne survit à l'érosion.
    """
    eroded = erode(free, erosion_radius_cells(resolution, robot_radius, safety_margin))
    row, col = start_cell
    if not (in_bounds(eroded, row, col) and eroded[row, col]):
        nearest = nearest_true_cell(eroded, row, col)
        if nearest is None:
            return np.zeros_like(free, dtype=bool)
        row, col = nearest
    return connected_component(eroded, (row, col))


# ---------------------------------------------------------------------------
# Mesure de couverture (tracker)
# ---------------------------------------------------------------------------

def mark_covered(covered, reachable, row, col, radius_cells):
    """Marque dans `covered` les cellules du disque centré en (row, col) ∩ reachable.

    `covered` est modifié en place. Renvoie le nombre de cellules nouvellement couvertes.
    Les cellules du disque hors de la grille sont ignorées.
    """
    offsets = disk_offsets(radius_cells)
    rows = offsets[:, 0] + row
    cols = offsets[:, 1] + col
    height, width = covered.shape
    inside = (rows >= 0) & (rows < height) & (cols >= 0) & (cols < width)
    rows, cols = rows[inside], cols[inside]
    new = reachable[rows, cols] & ~covered[rows, cols]
    covered[rows[new], cols[new]] = True
    return int(np.count_nonzero(new))


def coverage_percent(covered, reachable):
    """Pourcentage (0..100) des cellules atteignables qui sont couvertes."""
    total = int(np.count_nonzero(reachable))
    if total == 0:
        return 0.0
    done = int(np.count_nonzero(covered & reachable))
    return 100.0 * done / total


# ---------------------------------------------------------------------------
# Balayage boustrophédon (planner)
# ---------------------------------------------------------------------------

def row_segments(line):
    """Segments contigus de True d'une ligne booléenne : liste de (col_debut, col_fin) inclus."""
    padded = np.concatenate(([False], line, [False])).astype(np.int8)
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1) - 1
    return list(zip(starts.tolist(), ends.tolist()))


def sweep_rows(reachable, spacing_cells):
    """Indices des lignes de balayage, en ordre croissant, espacées de spacing_cells.

    Règle symétrique bas/haut : la 1re ligne est au plus à une demi-espacement du bord
    bas de la zone, la dernière au moins à une demi-espacement du bord haut. Ainsi un
    disque de nettoyage de rayon >= demi-espacement couvre aussi les deux bandes de bord
    (sans cela, la bande du haut pouvait rester non couverte : 98 % max sur pièce vide).

    Méthode : on prend juste assez d'intervalles pour aller de (bas + demi) à (haut - demi),
    puis on centre le bloc de lignes ; l'excédent (< spacing_cells) est réparti
    moitié en bas, moitié en haut. L'espacement reste régulier.
    """
    rows_with_cells = np.flatnonzero(reachable.any(axis=1))
    if len(rows_with_cells) == 0:
        return []
    row_min, row_max = int(rows_with_cells[0]), int(rows_with_cells[-1])
    half = spacing_cells // 2
    # Distance à franchir entre la 1re et la dernière ligne "idéales".
    inner = (row_max - half) - (row_min + half)
    if inner <= 0:
        # Zone plus fine qu'un espacement : une seule ligne au milieu.
        return [(row_min + row_max) // 2]
    n_gaps = math.ceil(inner / spacing_cells)  # nb d'intervalles entre lignes
    extra = n_gaps * spacing_cells - inner     # excédent, 0 <= extra < spacing_cells
    first = row_min + half - extra // 2        # reste >= row_min (extra // 2 <= half)
    return [first + k * spacing_cells for k in range(n_gaps + 1)]


def segment_waypoints(row, segment, left_to_right, origin_x, origin_y, resolution):
    """Waypoints (x, y, yaw) d'un segment parcouru dans le sens indiqué.

    2 waypoints (entrée, sortie) orientés dans le sens de passage :
    yaw = 0 vers +x, yaw = pi vers -x. Segment d'une cellule -> 1 waypoint.
    """
    col_start, col_end = segment
    yaw = 0.0 if left_to_right else math.pi
    cols = [col_start, col_end] if left_to_right else [col_end, col_start]
    if col_start == col_end:
        cols = [col_start]
    waypoints = []
    for col in cols:
        x, y = cell_to_world(row, col, origin_x, origin_y, resolution)
        waypoints.append((x, y, yaw))
    return waypoints


def boustrophedon_waypoints(reachable, origin_x, origin_y, resolution, sweep_spacing=0.18):
    """Trajet de balayage en serpentin sur le masque atteignable.

    - Lignes horizontales tous les sweep_spacing (arrondi au nombre de cellules, >= 1).
    - Sur chaque ligne, segments contigus de cellules atteignables.
    - Sens alterné d'une ligne (non vide) à l'autre : gauche->droite puis droite->gauche.
    - Waypoints = extrémités des segments, orientés dans le sens de passage.

    Limite assumée : si une ligne contient plusieurs segments (obstacle au milieu),
    on les enchaîne dans l'ordre du sens de passage. Ce n'est PAS une décomposition
    cellulaire de Choset : la transition entre segments (contournement de l'obstacle)
    est laissée au planificateur de Nav2, et certaines zones peuvent être visitées
    avec des allers-retours inutiles.
    """
    spacing_cells = max(1, int(round(sweep_spacing / resolution)))
    waypoints = []
    left_to_right = True
    for row in sweep_rows(reachable, spacing_cells):
        segments = row_segments(reachable[row])
        if not segments:
            continue  # ligne vide (zone non convexe) : on ne change pas le sens
        if not left_to_right:
            segments = segments[::-1]
        for segment in segments:
            waypoints += segment_waypoints(row, segment, left_to_right,
                                           origin_x, origin_y, resolution)
        left_to_right = not left_to_right
    return waypoints

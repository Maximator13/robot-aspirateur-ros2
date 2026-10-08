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
- transitions : test de ligne de vue exact O(L / résolution) par paire de waypoints ;
  si bloquée, Dijkstra 8-voisinage O(N log N) puis lissage par ligne de vue.
"""

import heapq
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


# ---------------------------------------------------------------------------
# Transitions entre waypoints (contournement des obstacles)
# ---------------------------------------------------------------------------
#
# Problème : boustrophedon_waypoints enchaîne parfois deux waypoints séparés par
# un obstacle (deux segments d'une même ligne de part et d'autre d'un pilier).
# Nav2 reçoit alors un but « derrière le pilier » et le contrôleur peut se bloquer.
# Solution : si la ligne droite entre deux waypoints sort du masque atteignable,
# on insère des points intermédiaires qui contournent l'obstacle.

def line_of_sight(reachable, p0, p1, origin_x, origin_y, resolution):
    """True si le segment monde p0 -> p1 ne traverse que des cellules de `reachable`.

    Test exact : on coupe le segment à chaque fois qu'il franchit une ligne de la
    grille (x = origin_x + k.res ou y = origin_y + k.res). Chaque morceau est alors
    entièrement dans une seule cellule : il suffit de tester son milieu.
    (Un simple échantillonnage n'est pas fiable : un segment qui passe pile par
    un coin de cellule donnait des résultats différents selon le pas choisi.)
    """
    (x0, y0), (x1, y1) = p0[:2], p1[:2]
    cuts = {0.0, 1.0}
    cuts |= _grid_crossings(x0, x1, origin_x, resolution)
    cuts |= _grid_crossings(y0, y1, origin_y, resolution)
    cuts = sorted(cuts)
    if x0 == x1 and y0 == y1:
        cuts = [0.0, 0.0]  # segment réduit à un point : on teste ce point
    for t_a, t_b in zip(cuts[:-1], cuts[1:]):
        t = 0.5 * (t_a + t_b)
        row, col = world_to_cell(x0 + t * (x1 - x0), y0 + t * (y1 - y0),
                                 origin_x, origin_y, resolution)
        if not (in_bounds(reachable, row, col) and reachable[row, col]):
            return False
    return True


def _grid_crossings(v0, v1, origin, resolution):
    """Paramètres t de ]0, 1[ où la coordonnée v0 + t.(v1 - v0) franchit une ligne de grille."""
    if v0 == v1:
        return set()
    lo, hi = sorted((v0, v1))
    k_first = int(math.floor((lo - origin) / resolution)) + 1
    k_last = int(math.ceil((hi - origin) / resolution)) - 1
    crossings = set()
    for k in range(k_first, k_last + 1):
        t = (origin + k * resolution - v0) / (v1 - v0)
        if 0.0 < t < 1.0:
            crossings.add(t)
    return crossings


def shortest_path_cells(reachable, start, goal):
    """Plus court chemin (liste de (row, col)) de start à goal dans `reachable`.

    Dijkstra en 8-voisinage : coût 1 en ligne droite, sqrt(2) en diagonale.
    Une diagonale n'est permise que si les deux cellules qu'elle longe sont
    atteignables (pas de « coin coupé » contre un obstacle).
    Renvoie None si goal n'est pas joignable depuis start.
    """
    dist = {start: 0.0}
    parent = {start: None}
    heap = [(0.0, start)]
    while heap:
        d, cell = heapq.heappop(heap)
        if cell == goal:
            break
        if d > dist[cell]:
            continue  # entrée périmée de la file de priorité
        for nxt, cost in _neighbors8(reachable, cell):
            nd = d + cost
            if nd < dist.get(nxt, math.inf):
                dist[nxt] = nd
                parent[nxt] = cell
                heapq.heappush(heap, (nd, nxt))
    if goal not in parent:
        return None
    path = []
    cell = goal
    while cell is not None:  # remontée des parents de goal vers start
        path.append(cell)
        cell = parent[cell]
    return path[::-1]


def _neighbors8(reachable, cell):
    """Voisins atteignables de `cell` (8-voisinage, sans coin coupé) avec leur coût."""
    row, col = cell
    result = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = row + dr, col + dc
            if not (in_bounds(reachable, nr, nc) and reachable[nr, nc]):
                continue
            if dr != 0 and dc != 0:
                if not (reachable[row + dr, col] and reachable[row, col + dc]):
                    continue  # la diagonale frôlerait un obstacle
                result.append(((nr, nc), math.sqrt(2.0)))
            else:
                result.append(((nr, nc), 1.0))
    return result


def simplify_path(points, reachable, origin_x, origin_y, resolution):
    """Lissage par ligne de vue d'une liste de points monde (x, y).

    On part du premier point ; on avance tant que la ligne droite depuis le
    dernier point gardé reste dans le masque ; dès qu'elle en sort, on garde
    le point précédent. Le premier et le dernier point sont toujours gardés.
    """
    if len(points) <= 2:
        return list(points)
    kept = [points[0]]
    for i in range(2, len(points)):
        if not line_of_sight(reachable, kept[-1], points[i], origin_x, origin_y, resolution):
            kept.append(points[i - 1])
    kept.append(points[-1])
    return kept


def split_long_legs(points, max_step):
    """Découpe chaque tronçon plus long que max_step en parts égales (points (x, y))."""
    if len(points) < 2:
        return list(points)
    result = [points[0]]
    for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
        n = max(1, int(math.ceil(math.hypot(x1 - x0, y1 - y0) / max_step)))
        for k in range(1, n + 1):
            result.append((x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n))
    return result


def _cell_in_mask(reachable, x, y, origin_x, origin_y, resolution):
    """Cellule de (x, y) si elle est atteignable, sinon la cellule atteignable la plus proche."""
    row, col = world_to_cell(x, y, origin_x, origin_y, resolution)
    if in_bounds(reachable, row, col) and reachable[row, col]:
        return row, col
    return nearest_true_cell(reachable, row, col)


def detour_points(reachable, wp_a, wp_b, origin_x, origin_y, resolution, max_step):
    """Points intermédiaires (x, y) pour aller de wp_a à wp_b en restant dans le masque.

    Renvoie la liste des points STRICTEMENT entre wp_a et wp_b (vide si la ligne
    droite suffit), ou None si les deux waypoints ne sont pas reliés dans le masque.
    """
    if line_of_sight(reachable, wp_a, wp_b, origin_x, origin_y, resolution):
        return []
    start = _cell_in_mask(reachable, wp_a[0], wp_a[1], origin_x, origin_y, resolution)
    goal = _cell_in_mask(reachable, wp_b[0], wp_b[1], origin_x, origin_y, resolution)
    if start is None or goal is None:
        return None
    cells = shortest_path_cells(reachable, start, goal)
    if cells is None:
        return None
    # Centres de cellules, encadrés par les positions exactes des deux waypoints.
    points = [tuple(wp_a[:2])]
    points += [cell_to_world(r, c, origin_x, origin_y, resolution) for r, c in cells]
    points.append(tuple(wp_b[:2]))
    points = simplify_path(points, reachable, origin_x, origin_y, resolution)
    points = split_long_legs(points, max_step)
    return points[1:-1]


def plan_transitions(reachable, waypoints, origin_x, origin_y, resolution, max_step=0.3):
    """Insère des points de contournement entre waypoints séparés par un obstacle.

    - Paire dont la ligne droite reste dans `reachable` : gardée telle quelle.
    - Sinon : plus court chemin dans le masque, lissé, découpé en tronçons
      <= max_step ; les points insérés sont orientés vers le point suivant.
    - Les waypoints d'origine sont tous conservés, avec leur yaw.

    Renvoie (nouveaux_waypoints, n_non_resolues) : n_non_resolues compte les paires
    qu'on n'a pas pu relier dans le masque (gardées en ligne droite ; ne devrait
    pas arriver puisque le masque est une seule composante connexe).
    Liste vide ou 1 waypoint : renvoyée telle quelle.
    """
    if len(waypoints) < 2:
        return list(waypoints), 0
    result = [waypoints[0]]
    n_unresolved = 0
    for wp_a, wp_b in zip(waypoints[:-1], waypoints[1:]):
        extra = detour_points(reachable, wp_a, wp_b, origin_x, origin_y, resolution, max_step)
        if extra is None:
            n_unresolved += 1
            extra = []
        result += _orient_towards_next(extra, wp_b)
        result.append(wp_b)
    return result, n_unresolved


def _orient_towards_next(points, next_wp):
    """Ajoute à chaque point (x, y) un yaw dirigé vers le point suivant de la liste."""
    oriented = []
    targets = list(points[1:]) + [next_wp[:2]]
    for (x, y), (tx, ty) in zip(points, targets):
        oriented.append((x, y, math.atan2(ty - y, tx - x)))
    return oriented

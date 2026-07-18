#!/usr/bin/env python3
"""
Maze Chase - A 2D top-down maze game with enemy pursuit cars.
Uses only Pygame, no external assets.
"""

import pygame
import random
import math
import sys
import os
from collections import deque

pygame.init()

# ─── Constants ───────────────────────────────────────────────────────────────

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 780
FPS = 60

GRID_COLS = 17
GRID_ROWS = 17
TILE_SIZE = 40
MAZE_WIDTH = GRID_COLS * TILE_SIZE
MAZE_HEIGHT = GRID_ROWS * TILE_SIZE
MAZE_OFFSET_X = (SCREEN_WIDTH - MAZE_WIDTH) // 2
MAZE_OFFSET_Y = 60

WALL = 1
PATH = 0

CAR_W = 26
CAR_H = 18
SPRITE_W = 39
SPRITE_H = 27

NUM_ENEMIES = 6
INITIAL_LIVES = 3
PURSUIT_RANGE = 550
ENEMY_BASE_SPEED = 1.4
PLAYER_SPEED = 1.5 * ENEMY_BASE_SPEED
ENEMY_SPEED_VARIATION = 0.45
PREDICTION_FACTOR = 5
ENEMY_NOISE = {'accurate': 0.05, 'medium': 0.30}
ENEMY_BIAS = {'accurate': 0.50, 'medium': 0.25}
ENEMY_CENTER_THRESHOLD = 6
ENEMY_STUCK_SNAP = 8
INVULNERABLE_TIME = 180
EXPLOSION_DURATION = 30
SCORE_VALUES = {'wall': 100, 'medium': 200, 'accurate': 300}
EXIT_SCORE_BASE = 500
HIGHSCORE_FILE = '.highscore'
BULLET_SPEED = 7
BULLET_SIZE = 6
BULLET_LIFETIME = 50
SHOOT_COOLDOWN = 12

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
WALL_COLOR = (25, 25, 75)
FLOOR_COLOR = (45, 45, 45)
PLAYER_COLOR = (40, 140, 255)
ENEMY_COLORS = [
    (220, 50, 50),
    (240, 160, 20),
    (180, 50, 220),
    (220, 220, 30),
    (30, 200, 200),
    (240, 100, 140),
]
HEART_COLOR = (255, 60, 60)
EXPLOSION_COLORS = [
    (255, 200, 30),
    (255, 150, 30),
    (255, 100, 30),
    (255, 60, 30),
]
UI_BG = (20, 20, 30)

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRECTIONS = [UP, DOWN, LEFT, RIGHT]

# Sprites
BG_THRESHOLD = 230
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_car_sprite(path, size=(SPRITE_W, SPRITE_H)):
    img = pygame.image.load(path).convert_alpha()
    img = pygame.transform.smoothscale(img, size)
    w, h = img.get_size()
    for x in range(w):
        for y in range(h):
            r, g, b, a = img.get_at((x, y))
            if r > BG_THRESHOLD and g > BG_THRESHOLD and b > BG_THRESHOLD:
                img.set_at((x, y), (0, 0, 0, 0))
    sprites = {
        UP: img,
        DOWN: pygame.transform.rotate(img, 180),
        LEFT: pygame.transform.rotate(img, 90),
        RIGHT: pygame.transform.rotate(img, -90),
    }
    return sprites


def tint_sprite(sprites, color):
    tinted = {}
    for direction, surf in sprites.items():
        new_surf = surf.copy()
        w, h = new_surf.get_size()
        for x in range(w):
            for y in range(h):
                r, g, b, a = new_surf.get_at((x, y))
                if a > 0:
                    factor = 0.5
                    nr = int(r * (1 - factor) + color[0] * factor)
                    ng = int(g * (1 - factor) + color[1] * factor)
                    nb = int(b * (1 - factor) + color[2] * factor)
                    new_surf.set_at((x, y), (min(255, nr), min(255, ng), min(255, nb), a))
        tinted[direction] = new_surf
    return tinted


def turn_right(d):
    return (-d[1], d[0])


def turn_left(d):
    return (d[1], -d[0])


# ─── High Score ──────────────────────────────────────────────────────────────

def load_highscore():
    try:
        with open(HIGHSCORE_FILE, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, 'w') as f:
            f.write(str(score))
    except OSError:
        pass


# ─── Maze Generation ─────────────────────────────────────────────────────────

def generate_maze(cols, rows):
    """Recursive backtracker maze.  cols & rows must be odd."""
    grid = [[WALL for _ in range(cols)] for _ in range(rows)]

    def carve(x, y):
        grid[y][x] = PATH
        dirs = [(0, -2), (0, 2), (-2, 0), (2, 0)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] == WALL:
                grid[y + dy // 2][x + dx // 2] = PATH
                carve(nx, ny)

    carve(1, 1)
    return grid


def get_wall_rects(grid):
    gap = 2
    ws = TILE_SIZE - gap * 2
    rects = []
    for ri, row in enumerate(grid):
        for ci, cell in enumerate(row):
            if cell == WALL:
                rects.append(pygame.Rect(
                    MAZE_OFFSET_X + ci * TILE_SIZE + gap,
                    MAZE_OFFSET_Y + ri * TILE_SIZE + gap,
                    ws, ws))
    return rects


def random_path_pos(grid):
    paths = []
    for ri, row in enumerate(grid):
        for ci, cell in enumerate(row):
            if cell == PATH:
                paths.append((ci, ri))
    if not paths:
        return (MAZE_OFFSET_X + TILE_SIZE, MAZE_OFFSET_Y + TILE_SIZE)
    cx, cy = random.choice(paths)
    return (MAZE_OFFSET_X + cx * TILE_SIZE + TILE_SIZE // 2,
            MAZE_OFFSET_Y + cy * TILE_SIZE + TILE_SIZE // 2)


def find_exit_pos(grid):
    for ri in range(GRID_ROWS - 1, -1, -1):
        for ci in range(GRID_COLS - 1, -1, -1):
            if grid[ri][ci] == PATH:
                return (MAZE_OFFSET_X + ci * TILE_SIZE + TILE_SIZE // 2,
                        MAZE_OFFSET_Y + ri * TILE_SIZE + TILE_SIZE // 2)
    return (MAZE_OFFSET_X + (GRID_COLS - 2) * TILE_SIZE + TILE_SIZE // 2,
            MAZE_OFFSET_Y + (GRID_ROWS - 2) * TILE_SIZE + TILE_SIZE // 2)


def bfs_distance(grid, tx, ty):
    rows, cols = len(grid), len(grid[0])
    dist = [[-1] * cols for _ in range(rows)]
    if not (0 <= tx < cols and 0 <= ty < rows) or grid[ty][tx] != PATH:
        return dist
    dq = deque()
    dq.append((tx, ty))
    dist[ty][tx] = 0
    while dq:
        cx, cy = dq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] == PATH and dist[ny][nx] == -1:
                dist[ny][nx] = dist[cy][cx] + 1
                dq.append((nx, ny))
    return dist


def farthest_path_tile(grid, exit_col, exit_row):
    dist = bfs_distance(grid, exit_col, exit_row)
    rows, cols = len(dist), len(dist[0])
    candidates = []
    max_dist = 0
    for ri in range(rows):
        for ci in range(cols):
            if dist[ri][ci] > 0:
                if dist[ri][ci] > max_dist:
                    max_dist = dist[ri][ci]
                candidates.append((ci, ri, dist[ri][ci]))
    if not candidates:
        return (1, 1)
    threshold = max_dist * 0.85
    far = [(c, r) for c, r, d in candidates if d >= threshold]
    return random.choice(far)


def tile_center(col, row):
    return (MAZE_OFFSET_X + col * TILE_SIZE + TILE_SIZE // 2,
            MAZE_OFFSET_Y + row * TILE_SIZE + TILE_SIZE // 2)


def pos_to_tile(px, py):
    col = max(0, min(GRID_COLS - 1, int((px - MAZE_OFFSET_X) // TILE_SIZE)))
    row = max(0, min(GRID_ROWS - 1, int((py - MAZE_OFFSET_Y) // TILE_SIZE)))
    return (col, row)


def nearest_path_tile(maze, px, py):
    col, row = pos_to_tile(px, py)
    if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS and maze[row][col] == PATH:
        return col, row
    best = None
    best_dist = float('inf')
    for dr in range(-4, 5):
        for dc in range(-4, 5):
            nc, nr = col + dc, row + dr
            if 0 <= nc < GRID_COLS and 0 <= nr < GRID_ROWS and maze[nr][nc] == PATH:
                cx, cy = tile_center(nc, nr)
                dist = (px - cx) ** 2 + (py - cy) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best = (nc, nr)
    return best if best else (col, row)


def tile_neighbors_at(maze, col, row):
    neighbors = []
    for d in DIRECTIONS:
        nx, ny = col + d[0], row + d[1]
        if 0 <= nx < GRID_COLS and 0 <= ny < GRID_ROWS and maze[ny][nx] == PATH:
            neighbors.append(d)
    return neighbors


def choose_bfs_step(tile_neighbors, dist_map, col, row, noise):
    """Pick a cardinal step using BFS distances, with optional random noise at junctions."""
    if not tile_neighbors:
        return None
    if len(tile_neighbors) > 1 and random.random() < noise:
        return random.choice(tile_neighbors)
    best_list = []
    best_d = 9999
    for d in tile_neighbors:
        dv = dist_map[row + d[1]][col + d[0]]
        if dv == -1:
            continue
        if dv < best_d:
            best_d = dv
            best_list = [d]
        elif dv == best_d:
            best_list.append(d)
    return random.choice(best_list) if best_list else random.choice(tile_neighbors)


def is_path(maze, col, row):
    return 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS and maze[row][col] == PATH


def wall_follower_direction(maze, col, row, direction):
    """Right-hand rule: keep wall on your right side."""
    right = turn_right(direction)
    left = turn_left(direction)
    if not is_path(maze, col + right[0], row + right[1]):
        if is_path(maze, col + direction[0], row + direction[1]):
            return direction
        if is_path(maze, col + left[0], row + left[1]):
            return left
        return (-direction[0], -direction[1])
    return right


def move_enemy_on_grid(enemy, walls, maze):
    """Move enemy along grid paths with persistent tile targeting."""
    if enemy.target_tile is not None:
        tx, ty = tile_center(*enemy.target_tile)
        dist = math.hypot(enemy.x - tx, enemy.y - ty)
        if dist < 2.0:
            enemy.set_pos(tx, ty)
            enemy.target_tile = None
            return True
        dx = tx - enemy.x
        dy = ty - enemy.y
        scale = min(1.0, enemy.speed / dist)
        old_x, old_y = enemy.x, enemy.y
        enemy.move(dx * scale, dy * scale, walls)
        return math.hypot(enemy.x - old_x, enemy.y - old_y) > 0.01

    col, row = nearest_path_tile(maze, enemy.x, enemy.y)
    cx, cy = tile_center(col, row)
    d = enemy.direction
    ncol, nrow = col + d[0], row + d[1]
    can_advance = (0 <= ncol < GRID_COLS and 0 <= nrow < GRID_ROWS
                   and maze[nrow][ncol] == PATH)

    if can_advance:
        enemy.target_tile = (ncol, nrow)
        tx, ty = tile_center(ncol, nrow)
    else:
        tx, ty = cx, cy

    dx = tx - enemy.x
    dy = ty - enemy.y
    dist = math.hypot(dx, dy)
    if dist < 0.5:
        return False

    scale = min(1.0, enemy.speed / dist)
    old_x, old_y = enemy.x, enemy.y
    enemy.move(dx * scale, dy * scale, walls)
    return math.hypot(enemy.x - old_x, enemy.y - old_y) > 0.01


def unstuck_enemy(enemy, maze):
    col, row = nearest_path_tile(maze, enemy.x, enemy.y)
    enemy.set_pos(*tile_center(col, row))
    enemy.stuck_frames = 0


def move_player_on_grid(player, walls, maze):
    """Move player along grid, steering toward tile centers."""
    col, row = nearest_path_tile(maze, player.x, player.y)
    cx, cy = tile_center(col, row)
    d = player.direction
    ncol, nrow = col + d[0], row + d[1]
    can_advance = (0 <= ncol < GRID_COLS and 0 <= nrow < GRID_ROWS
                   and maze[nrow][ncol] == PATH)

    if d in (UP, DOWN):
        off_center = abs(player.x - cx) > 2
    else:
        off_center = abs(player.y - cy) > 2

    if off_center:
        tx, ty = cx, cy
    elif can_advance:
        tx, ty = tile_center(ncol, nrow)
    else:
        tx, ty = cx, cy

    dx = tx - player.x
    dy = ty - player.y
    dist = math.hypot(dx, dy)
    if dist < 0.5:
        return
    scale = min(1.0, player.speed / dist)
    player.move(dx * scale, dy * scale, walls)


# ─── Car ─────────────────────────────────────────────────────────────────────

class Car:
    def __init__(self, x, y, color, is_player=False, behavior=None, sprites=None):
        self.x = x
        self.y = y
        self.color = color
        self.is_player = is_player
        self.behavior = behavior
        self.direction = UP
        self.speed = PLAYER_SPEED if is_player else ENEMY_BASE_SPEED + random.uniform(-ENEMY_SPEED_VARIATION, ENEMY_SPEED_VARIATION)
        self.rect = pygame.Rect(0, 0, CAR_W, CAR_H)
        self.rect.center = (x, y)
        self.hitbox = pygame.Rect(0, 0, CAR_W - 6, CAR_H - 4)
        self.hitbox.center = (x, y)
        self.move_timer = random.randint(0, 60)
        self.move_dur = random.randint(30, 90)
        self.stuck_frames = 0
        self.target_tile = None
        self.sprites = sprites

    def set_pos(self, x, y):
        self.x, self.y = x, y
        self.rect.center = (x, y)
        self.hitbox.center = (x, y)

    def move(self, dx, dy, walls):
        self.hitbox.centerx = self.x + dx
        for w in walls:
            if self.hitbox.colliderect(w):
                self.hitbox.centerx = self.x
                break
        self.x = self.hitbox.centerx

        self.hitbox.centery = self.y + dy
        for w in walls:
            if self.hitbox.colliderect(w):
                self.hitbox.centery = self.y
                break
        self.y = self.hitbox.centery

        self.rect.center = (self.x, self.y)

        if self.is_player:
            if abs(dx) > abs(dy):
                self.direction = RIGHT if dx > 0 else LEFT
            elif abs(dy) > 0:
                self.direction = DOWN if dy > 0 else UP

    def draw(self, screen):
        if self.sprites:
            sprite = self.sprites.get(self.direction)
            if sprite:
                sprite_rect = sprite.get_rect(center=(self.x, self.y))
                screen.blit(sprite, sprite_rect)
                return

        body = pygame.Rect(0, 0, CAR_W, CAR_H)
        body.center = (self.x, self.y)
        pygame.draw.rect(screen, self.color, body, border_radius=4)

        cabin_w = int(CAR_W * 0.55)
        cabin_h = int(CAR_H * 0.6)
        cabin = pygame.Rect(0, 0, cabin_w, cabin_h)
        cabin.center = (self.x, self.y)
        lighter = tuple(min(255, c + 60) for c in self.color)
        pygame.draw.rect(screen, lighter, cabin, border_radius=2)

        w_sz = 4
        for ox, oy in [(-CAR_W // 2 + 1, -CAR_H // 2 - 1),
                       (CAR_W // 2 - 1, -CAR_H // 2 - 1),
                       (-CAR_W // 2 + 1, CAR_H // 2 + 1),
                       (CAR_W // 2 - 1, CAR_H // 2 + 1)]:
            r = pygame.Rect(0, 0, w_sz, w_sz)
            r.center = (self.x + ox, self.y + oy)
            pygame.draw.rect(screen, (30, 30, 30), r)

        dx, dy = self.direction
        tip_x = self.x + dx * (CAR_W // 2 + 2)
        tip_y = self.y + dy * (CAR_H // 2 + 2)
        if self.direction == UP:
            pts = [(tip_x, tip_y),
                   (self.x - 5, self.y - CAR_H // 2 + 2),
                   (self.x + 5, self.y - CAR_H // 2 + 2)]
        elif self.direction == DOWN:
            pts = [(tip_x, tip_y),
                   (self.x - 5, self.y + CAR_H // 2 - 2),
                   (self.x + 5, self.y + CAR_H // 2 - 2)]
        elif self.direction == LEFT:
            pts = [(tip_x, tip_y),
                   (self.x - CAR_W // 2 + 2, self.y - 5),
                   (self.x - CAR_W // 2 + 2, self.y + 5)]
        else:
            pts = [(tip_x, tip_y),
                   (self.x + CAR_W // 2 - 2, self.y - 5),
                   (self.x + CAR_W // 2 - 2, self.y + 5)]
        pygame.draw.polygon(screen, (220, 220, 220), pts)


# ─── Explosion ───────────────────────────────────────────────────────────────

class Explosion:
    def __init__(self, x, y):
        self.frame = 0
        self.max_frames = EXPLOSION_DURATION
        self.particles = []
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 5.5)
            self.particles.append({
                'x': x, 'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'size': random.randint(2, 7),
                'color': random.choice(EXPLOSION_COLORS),
            })

    def update(self):
        self.frame += 1
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vx'] *= 0.94
            p['vy'] *= 0.94
        return self.frame < self.max_frames

    def draw(self, screen):
        progress = self.frame / self.max_frames
        for p in self.particles:
            sz = max(1, int(p['size'] * (1.0 - progress * 0.6)))
            factor = 1.0 - progress
            r, g, b = p['color']
            color = (int(r * factor), int(g * factor), int(b * factor))
            pygame.draw.circle(screen, color, (int(p['x']), int(p['y'])), sz)


# ─── Bullet ──────────────────────────────────────────────────────────────────

class Bullet:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.dx = direction[0] * BULLET_SPEED
        self.dy = direction[1] * BULLET_SPEED
        self.lifetime = BULLET_LIFETIME
        self.rect = pygame.Rect(0, 0, BULLET_SIZE, BULLET_SIZE)
        self.rect.center = (x, y)

    def update(self, walls):
        self.x += self.dx
        self.y += self.dy
        self.rect.center = (self.x, self.y)
        self.lifetime -= 1
        for w in walls:
            if self.rect.colliderect(w):
                return False
        return self.lifetime > 0

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 100),
                           (int(self.x), int(self.y)), BULLET_SIZE // 2)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Caça ao Labirinto")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 32)
    big_font = pygame.font.Font(None, 72)

    player_sprites = load_car_sprite(os.path.join(SCRIPT_DIR, 'jogador.jpg'))
    enemy_sprites = load_car_sprite(os.path.join(SCRIPT_DIR, 'inimigos.jpg'))

    # Generate maze
    maze = generate_maze(GRID_COLS, GRID_ROWS)
    walls = get_wall_rects(maze)

    exit_x, exit_y = find_exit_pos(maze)
    exit_rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
    exit_rect.center = (exit_x, exit_y)

    # Player
    player = Car(0, 0, PLAYER_COLOR, is_player=True, sprites=player_sprites)

    def best_start_direction(px, py):
        col, row = pos_to_tile(px, py)
        best_dir, best_count = UP, -1
        for d in DIRECTIONS:
            count = 0
            for step in range(1, 8):
                nc, nr = col + d[0] * step, row + d[1] * step
                if 0 <= nc < GRID_COLS and 0 <= nr < GRID_ROWS and maze[nr][nc] == PATH:
                    count += 1
                else:
                    break
            if count > best_count:
                best_count = count
                best_dir = d
        return best_dir

    def spawn_player():
        exit_col, exit_row = pos_to_tile(exit_x, exit_y)
        far_col, far_row = farthest_path_tile(maze, exit_col, exit_row)
        x, y = tile_center(far_col, far_row)
        for e in enemies:
            if math.hypot(x - e.x, y - e.y) < 180:
                dist = bfs_distance(maze, exit_col, exit_row)
                rows, cols = len(dist), len(dist[0])
                max_d = max(dist[ri][ci] for ri in range(rows) for ci in range(cols) if dist[ri][ci] > 0)
                threshold = max_d * 0.85
                far = [(ci, ri) for ri in range(rows) for ci in range(cols) if dist[ri][ci] >= threshold]
                random.shuffle(far)
                for fc, fr in far:
                    tx, ty = tile_center(fc, fr)
                    if all(math.hypot(tx - e.x, ty - e.y) >= 180 for e in enemies):
                        x, y = tx, ty
                        break
                break
        player.set_pos(x, y)
        player.direction = best_start_direction(x, y)

    def spawn_enemy(enemy):
        enemy.target_tile = None
        if enemy.behavior == 'wall':
            exit_col, exit_row = pos_to_tile(exit_x, exit_y)
            far_col, far_row = farthest_path_tile(maze, exit_col, exit_row)
            x, y = tile_center(far_col, far_row)
            for e in enemies:
                if e is not enemy and math.hypot(x - e.x, y - e.y) < 60:
                    dist = bfs_distance(maze, exit_col, exit_row)
                    rows, cols = len(dist), len(dist[0])
                    max_d = max(dist[ri][ci] for ri in range(rows) for ci in range(cols) if dist[ri][ci] > 0)
                    threshold = max_d * 0.85
                    far = [(ci, ri) for ri in range(rows) for ci in range(cols) if dist[ri][ci] >= threshold]
                    random.shuffle(far)
                    for fc, fr in far:
                        tx, ty = tile_center(fc, fr)
                        if all(math.hypot(tx - o.x, ty - o.y) >= 60 or o is enemy or o is e for o in enemies):
                            x, y = tx, ty
                            break
                    break
            enemy.set_pos(x, y)
            col, row = pos_to_tile(x, y)
            neighbors = tile_neighbors_at(maze, col, row)
            enemy.direction = neighbors[0] if neighbors else random.choice(DIRECTIONS)
            return
        if enemy.behavior == 'medium':
            exit_col, exit_row = pos_to_tile(exit_x, exit_y)
            dist = bfs_distance(maze, exit_col, exit_row)
            rows, cols = len(dist), len(dist[0])
            max_d = max(dist[ri][ci] for ri in range(rows) for ci in range(cols) if dist[ri][ci] > 0)
            target_d = max_d // 2
            mid = [(ci, ri) for ri in range(rows) for ci in range(cols)
                   if abs(dist[ri][ci] - target_d) <= 2 and maze[ri][ci] == PATH]
            if mid:
                random.shuffle(mid)
                tx, ty = tile_center(mid[0][0], mid[0][1])
            else:
                tx, ty = random_path_pos(maze)
            enemy.set_pos(tx, ty)
            col, row = pos_to_tile(tx, ty)
            neighbors = tile_neighbors_at(maze, col, row)
            enemy.direction = neighbors[0] if neighbors else random.choice(DIRECTIONS)
            return
        for _ in range(100):
            x, y = random_path_pos(maze)
            if math.hypot(x - player.x, y - player.y) < 120:
                continue
            ok = True
            for e in enemies:
                if e is enemy:
                    continue
                if math.hypot(x - e.x, y - e.y) < 80:
                    ok = False
                    break
            if ok:
                enemy.set_pos(x, y)
                enemy.direction = random.choice(DIRECTIONS)
                return
        enemy.set_pos(*random_path_pos(maze))
        enemy.direction = random.choice(DIRECTIONS)

    enemy_behaviors = ['accurate', 'medium', 'medium', 'wall', 'wall', 'wall']
    enemies = [Car(0, 0, ENEMY_COLORS[i % len(ENEMY_COLORS)],
                   behavior=enemy_behaviors[i],
                   sprites=tint_sprite(enemy_sprites, ENEMY_COLORS[i % len(ENEMY_COLORS)]))
               for i in range(len(enemy_behaviors))]

    def apply_phase_difficulty():
        speed_mult = 1.0 + 0.15 * (phase - 1)
        for e in enemies:
            e.speed = (ENEMY_BASE_SPEED + random.uniform(-ENEMY_SPEED_VARIATION, ENEMY_SPEED_VARIATION)) * speed_mult

    # Game state
    lives = INITIAL_LIVES
    score = 0
    highscore = load_highscore()
    phase = 1

    apply_phase_difficulty()
    spawn_player()
    for e in enemies:
        spawn_enemy(e)

    invulnerable = INVULNERABLE_TIME
    explosions = []
    bullets = []
    shoot_cooldown = 0
    bfs_counter = 0
    dist_map = None
    game_over = False
    game_won = False
    phase_timer = 0
    running = True

    def advance_phase():
        nonlocal maze, walls, exit_rect, phase_timer, game_won, game_over, invulnerable
        maze = generate_maze(GRID_COLS, GRID_ROWS)
        walls = get_wall_rects(maze)
        exit_x, exit_y = find_exit_pos(maze)
        exit_rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        exit_rect.center = (exit_x, exit_y)
        for e in enemies:
            e.target_tile = None
            spawn_enemy(e)
        spawn_player()
        apply_phase_difficulty()
        invulnerable = INVULNERABLE_TIME
        explosions.clear()
        bullets.clear()
        shoot_cooldown = 0
        bfs_counter = 0
        dist_map = None
        game_won = False
        game_over = False
        phase_timer = 0

    def reset_game():
        nonlocal lives, score, phase
        lives = INITIAL_LIVES
        score = 0
        phase = 1
        advance_phase()
        highscore = load_highscore()

    while running:
        # ── Events ──────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                if event.key == pygame.K_c and game_won:
                    advance_phase()
                if event.key == pygame.K_r and game_over:
                    reset_game()

        if game_won and phase_timer > 0:
            phase_timer -= 1
            if phase_timer <= 0:
                advance_phase()

        if not game_over and not game_won:
            # ── Player input ────────────────────────────────────────────
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                player.direction = UP
            if keys[pygame.K_DOWN]:
                player.direction = DOWN
            if keys[pygame.K_LEFT]:
                player.direction = LEFT
            if keys[pygame.K_RIGHT]:
                player.direction = RIGHT
            dx = player.direction[0] * PLAYER_SPEED
            dy = player.direction[1] * PLAYER_SPEED
            move_player_on_grid(player, walls, maze)
            player.vx = dx
            player.vy = dy

            if keys[pygame.K_SPACE] and shoot_cooldown <= 0:
                bx = player.x + player.direction[0] * (CAR_W // 2 + 4)
                by = player.y + player.direction[1] * (CAR_H // 2 + 4)
                bullets.append(Bullet(bx, by, player.direction))
                shoot_cooldown = SHOOT_COOLDOWN
            if shoot_cooldown > 0:
                shoot_cooldown -= 1

            # ── Enemy AI ───────────────────────────────────────────────
            phase_pursuit = PURSUIT_RANGE + 50 * (phase - 1)
            phase_noise = max(0.01, 0.05 / (1 + 0.3 * (phase - 1)))
            phase_medium_noise = max(0.05, 0.30 / (1 + 0.3 * (phase - 1)))
            bfs_counter -= 1
            if bfs_counter <= 0:
                vx = getattr(player, 'vx', 0)
                vy = getattr(player, 'vy', 0)
                px = player.x + vx * TILE_SIZE * 1.5
                py = player.y + vy * TILE_SIZE * 1.5
                px = max(MAZE_OFFSET_X, min(MAZE_OFFSET_X + GRID_COLS * TILE_SIZE - 1, px))
                py = max(MAZE_OFFSET_Y, min(MAZE_OFFSET_Y + GRID_ROWS * TILE_SIZE - 1, py))
                pt_x, pt_y = pos_to_tile(px, py)
                if not (0 <= pt_x < GRID_COLS and 0 <= pt_y < GRID_ROWS and maze[pt_y][pt_x] == PATH):
                    pt_x, pt_y = pos_to_tile(player.x, player.y)
                dist_map = bfs_distance(maze, pt_x, pt_y)
                bfs_counter = 3

            for enemy in enemies:
                et_x, et_y = nearest_path_tile(maze, enemy.x, enemy.y)
                tile_neighbors = tile_neighbors_at(maze, et_x, et_y)
                if not tile_neighbors:
                    tile_neighbors = [enemy.direction]

                if enemy.behavior == 'wall':
                    if enemy.target_tile is None:
                        enemy.direction = wall_follower_direction(maze, et_x, et_y, enemy.direction)
                else:
                    dist = math.hypot(enemy.x - player.x, enemy.y - player.y)
                    noise = phase_noise if enemy.behavior == 'accurate' else phase_medium_noise
                    bias = ENEMY_BIAS[enemy.behavior]

                    if dist < phase_pursuit:
                        step = choose_bfs_step(tile_neighbors, dist_map, et_x, et_y, noise)
                        if step:
                            enemy.direction = step
                    else:
                        enemy.move_timer += 1
                        if enemy.move_timer >= enemy.move_dur:
                            if random.random() < bias:
                                step = choose_bfs_step(tile_neighbors, dist_map, et_x, et_y, noise=0.0)
                                enemy.direction = step or random.choice(tile_neighbors)
                            else:
                                enemy.direction = random.choice(tile_neighbors)
                            enemy.move_timer = 0
                            enemy.move_dur = random.randint(10, 35)

                moved = move_enemy_on_grid(enemy, walls, maze)
                if moved:
                    enemy.stuck_frames = 0
                else:
                    enemy.stuck_frames += 1
                    if enemy.stuck_frames >= ENEMY_STUCK_SNAP:
                        unstuck_enemy(enemy, maze)
                        enemy.target_tile = None
                        ncol, nrow = nearest_path_tile(maze, enemy.x, enemy.y)
                        fresh_neighbors = tile_neighbors_at(maze, ncol, nrow)
                        if enemy.behavior == 'wall':
                            enemy.direction = wall_follower_direction(maze, ncol, nrow, enemy.direction)
                        elif fresh_neighbors:
                            enemy.direction = random.choice(fresh_neighbors)
                    elif enemy.stuck_frames >= 2:
                        cur_col, cur_row = nearest_path_tile(maze, enemy.x, enemy.y)
                        alt_dirs = tile_neighbors_at(maze, cur_col, cur_row)
                        if alt_dirs:
                            enemy.direction = random.choice(alt_dirs)
                            enemy.target_tile = None

            # ── Collisions ────────────────────────────────────────────
            if invulnerable <= 0:
                for enemy in enemies:
                    if player.hitbox.colliderect(enemy.hitbox):
                        explosions.append(Explosion(player.x, player.y))
                        explosions.append(Explosion(enemy.x, enemy.y))
                        lives -= 1
                        invulnerable = INVULNERABLE_TIME
                        spawn_player()
                        spawn_enemy(enemy)
                        if lives <= 0:
                            game_over = True
                        break

            if invulnerable > 0:
                invulnerable -= 1

            explosions = [e for e in explosions if e.update()]

            new_bullets = []
            for bullet in bullets:
                if not bullet.update(walls):
                    continue
                hit = False
                for enemy in enemies:
                    if bullet.rect.colliderect(enemy.hitbox):
                        explosions.append(Explosion(enemy.x, enemy.y))
                        score += SCORE_VALUES.get(enemy.behavior, 100)
                        if score > highscore:
                            highscore = score
                            save_highscore(highscore)
                        spawn_enemy(enemy)
                        hit = True
                        break
                if not hit:
                    new_bullets.append(bullet)
            bullets = new_bullets

            if not game_won and player.hitbox.colliderect(exit_rect):
                exit_pts = EXIT_SCORE_BASE * phase
                score += exit_pts
                if score > highscore:
                    highscore = score
                    save_highscore(highscore)
                phase += 1
                phase_timer = 10 * FPS
                game_won = True

        # ── Draw ──────────────────────────────────────────────────────────
        screen.fill(BLACK)

        for ri, row in enumerate(maze):
            for ci, cell in enumerate(row):
                rect = pygame.Rect(MAZE_OFFSET_X + ci * TILE_SIZE,
                                   MAZE_OFFSET_Y + ri * TILE_SIZE,
                                   TILE_SIZE, TILE_SIZE)
                if cell == WALL:
                    gap = 2
                    wr = pygame.Rect(rect.x + gap, rect.y + gap,
                                     TILE_SIZE - gap * 2, TILE_SIZE - gap * 2)
                    pygame.draw.rect(screen, WALL_COLOR, wr)
                    pygame.draw.rect(screen, (40, 40, 100), wr, 1)
                else:
                    pygame.draw.rect(screen, FLOOR_COLOR, rect)

        pygame.draw.rect(screen, (0, 180, 60), exit_rect, border_radius=4)
        pygame.draw.rect(screen, (0, 255, 100), exit_rect, 2, border_radius=4)
        exit_label = font.render("SAÍDA", True, (255, 255, 255))
        screen.blit(exit_label, exit_label.get_rect(center=exit_rect.center))

        for e in enemies:
            e.draw(screen)

        if invulnerable <= 0 or (invulnerable // 4) % 2 == 0:
            player.draw(screen)

        for ex in explosions:
            ex.draw(screen)

        for b in bullets:
            b.draw(screen)

        # ── UI ──────────────────────────────────────────────────────────
        bar_rect = pygame.Rect(0, 0, SCREEN_WIDTH, MAZE_OFFSET_Y)
        pygame.draw.rect(screen, UI_BG, bar_rect)

        lives_label = font.render("VIDAS", True, (180, 180, 180))
        screen.blit(lives_label, (20, 10))
        for i in range(INITIAL_LIVES):
            hx = 110 + i * 34
            hy = 12
            if i < lives:
                pygame.draw.rect(screen, HEART_COLOR, (hx, hy, 26, 22),
                                 border_radius=5)
            else:
                pygame.draw.rect(screen, (60, 20, 20), (hx, hy, 26, 22),
                                 border_radius=5)
                pygame.draw.rect(screen, (80, 30, 30), (hx, hy, 26, 22), 1,
                                 border_radius=5)

        phase_text = font.render(f"FASE {phase}", True, (100, 200, 255))
        screen.blit(phase_text, (SCREEN_WIDTH - 120, 10))

        score_text = font.render(f"PONTOS {score}", True, (255, 220, 50))
        screen.blit(score_text, (20, 36))

        hi_text = font.render(f"RECORDE {highscore}", True, (180, 180, 180))
        hi_rect = hi_text.get_rect(center=(SCREEN_WIDTH // 2, 42))
        screen.blit(hi_text, hi_rect)

        if game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(140)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            go = big_font.render("FIM DE JOGO", True, (255, 50, 50))
            screen.blit(go, go.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 - 50)))
            sc = font.render(f"Pontos: {score}   Fase: {phase}", True, (255, 220, 50))
            screen.blit(sc, sc.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 + 0)))
            hi = font.render(f"Recorde: {highscore}", True, (180, 180, 180))
            screen.blit(hi, hi.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 + 30)))
            rs = font.render("Pressione R para reiniciar", True, WHITE)
            screen.blit(rs, rs.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 + 60)))

        if game_won:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(140)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            win = big_font.render("FASE COMPLETA!", True, (50, 255, 50))
            screen.blit(win, win.get_rect(center=(SCREEN_WIDTH // 2,
                                                   SCREEN_HEIGHT // 2 - 50)))
            sc = font.render(f"Pontos: {score}   Próxima: Fase {phase}", True, (255, 220, 50))
            screen.blit(sc, sc.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 + 0)))
            hi = font.render(f"Recorde: {highscore}", True, (180, 180, 180))
            screen.blit(hi, hi.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 + 30)))
            secs = max(0, phase_timer // FPS + (1 if phase_timer % FPS else 0))
            rs = font.render(f"Próxima fase em {secs}s  (C para pular)", True, WHITE)
            screen.blit(rs, rs.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 + 60)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Maze Chase - A 2D top-down maze game with enemy pursuit cars.
Uses only Pygame, no external assets.
"""

import pygame
import random
import math
import sys
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

PLAYER_SPEED = 2.5
NUM_ENEMIES = 6
INITIAL_LIVES = 3
PURSUIT_RANGE = 550
ENEMY_BASE_SPEED = 1.4
ENEMY_SPEED_VARIATION = 0.45
PREDICTION_FACTOR = 5
ENEMY_NOISE = {'accurate': 0.05, 'medium': 0.30}
ENEMY_BIAS = {'accurate': 0.50, 'medium': 0.25}
ENEMY_CENTER_THRESHOLD = 6
ENEMY_STUCK_SNAP = 8
INVULNERABLE_TIME = 90
EXPLOSION_DURATION = 30
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


def turn_right(d):
    return (-d[1], d[0])


def turn_left(d):
    return (d[1], -d[0])


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


def tile_center(col, row):
    return (MAZE_OFFSET_X + col * TILE_SIZE + TILE_SIZE // 2,
            MAZE_OFFSET_Y + row * TILE_SIZE + TILE_SIZE // 2)


def pos_to_tile(px, py):
    return (int((px - MAZE_OFFSET_X) // TILE_SIZE),
            int((py - MAZE_OFFSET_Y) // TILE_SIZE))


def nearest_path_tile(maze, px, py):
    col, row = pos_to_tile(px, py)
    if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS and maze[row][col] == PATH:
        return col, row
    best = None
    best_dist = float('inf')
    for dr in range(-2, 3):
        for dc in range(-2, 3):
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
    """Pick a cardinal step using BFS distances, with optional random noise."""
    if not tile_neighbors:
        return None
    if random.random() < noise:
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


def wall_follower_direction(maze, col, row, direction):
    """Right-hand rule on the grid: try right, forward, left, then back."""
    right = turn_right(direction)
    forward = direction
    left = turn_left(direction)
    back = (-direction[0], -direction[1])
    for d in (right, forward, left, back):
        nx, ny = col + d[0], row + d[1]
        if 0 <= nx < GRID_COLS and 0 <= ny < GRID_ROWS and maze[ny][nx] == PATH:
            return d
    return direction


def move_enemy_on_grid(enemy, walls, maze):
    """Move enemy along grid paths, centering on tiles to avoid corner jams."""
    col, row = nearest_path_tile(maze, enemy.x, enemy.y)
    cx, cy = tile_center(col, row)
    d = enemy.direction
    ncol, nrow = col + d[0], row + d[1]
    can_advance = (0 <= ncol < GRID_COLS and 0 <= nrow < GRID_ROWS
                   and maze[nrow][ncol] == PATH)

    dist_from_center = math.hypot(enemy.x - cx, enemy.y - cy)
    if can_advance and dist_from_center <= ENEMY_CENTER_THRESHOLD:
        tx, ty = tile_center(ncol, nrow)
    else:
        tx, ty = cx, cy

    dx = tx - enemy.x
    dy = ty - enemy.y
    dist = math.hypot(dx, dy)
    if dist < 0.5:
        if dist > 0.01:
            enemy.set_pos(tx, ty)
        return can_advance and dist_from_center <= ENEMY_CENTER_THRESHOLD

    scale = min(1.0, enemy.speed / dist)
    old_x, old_y = enemy.x, enemy.y
    enemy.move(dx * scale, dy * scale, walls)
    return math.hypot(enemy.x - old_x, enemy.y - old_y) > 0.01


def unstuck_enemy(enemy, maze):
    col, row = nearest_path_tile(maze, enemy.x, enemy.y)
    enemy.set_pos(*tile_center(col, row))
    enemy.stuck_frames = 0


# ─── Car ─────────────────────────────────────────────────────────────────────

class Car:
    def __init__(self, x, y, color, is_player=False, behavior=None):
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
    pygame.display.set_caption("Maze Chase")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 32)
    big_font = pygame.font.Font(None, 72)

    # Generate maze
    maze = generate_maze(GRID_COLS, GRID_ROWS)
    walls = get_wall_rects(maze)

    exit_x, exit_y = find_exit_pos(maze)
    exit_rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
    exit_rect.center = (exit_x, exit_y)

    # Player
    player = Car(0, 0, PLAYER_COLOR, is_player=True)

    def spawn_player():
        for _ in range(100):
            x, y = random_path_pos(maze)
            ok = True
            for e in enemies:
                if math.hypot(x - e.x, y - e.y) < 120:
                    ok = False
                    break
            if ok:
                player.set_pos(x, y)
                player.direction = UP
                return
        player.set_pos(*random_path_pos(maze))
        player.direction = UP

    def spawn_enemy(enemy):
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
                   behavior=enemy_behaviors[i])
               for i in range(NUM_ENEMIES)]
    spawn_player()
    for e in enemies:
        spawn_enemy(e)

    # Game state
    lives = INITIAL_LIVES
    invulnerable = 0
    explosions = []
    bullets = []
    shoot_cooldown = 0
    bfs_counter = 0
    dist_map = None
    game_over = False
    game_won = False
    running = True

    while running:
        # ── Events ──────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                if event.key == pygame.K_r and (game_over or game_won):
                    maze = generate_maze(GRID_COLS, GRID_ROWS)
                    walls = get_wall_rects(maze)
                    exit_x, exit_y = find_exit_pos(maze)
                    exit_rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
                    exit_rect.center = (exit_x, exit_y)
                    for e in enemies:
                        spawn_enemy(e)
                    spawn_player()
                    lives = INITIAL_LIVES
                    invulnerable = 0
                    explosions.clear()
                    bullets.clear()
                    shoot_cooldown = 0
                    bfs_counter = 0
                    game_over = False
                    game_won = False

        if not game_over and not game_won:
            # ── Player input ────────────────────────────────────────────
            keys = pygame.key.get_pressed()
            dx = dy = 0.0
            if keys[pygame.K_UP]:
                dy = -PLAYER_SPEED
            if keys[pygame.K_DOWN]:
                dy = PLAYER_SPEED
            if keys[pygame.K_LEFT]:
                dx = -PLAYER_SPEED
            if keys[pygame.K_RIGHT]:
                dx = PLAYER_SPEED
            if dx != 0 and dy != 0:
                dx *= 0.7071
                dy *= 0.7071
            player.move(dx, dy, walls)
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
                    enemy.direction = wall_follower_direction(maze, et_x, et_y, enemy.direction)
                else:
                    dist = math.hypot(enemy.x - player.x, enemy.y - player.y)
                    noise = ENEMY_NOISE[enemy.behavior]
                    bias = ENEMY_BIAS[enemy.behavior]

                    if dist < PURSUIT_RANGE:
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
                        if enemy.behavior == 'wall':
                            col, row = nearest_path_tile(maze, enemy.x, enemy.y)
                            enemy.direction = wall_follower_direction(maze, col, row, enemy.direction)
                        elif tile_neighbors:
                            enemy.direction = random.choice(tile_neighbors)

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
                        spawn_enemy(enemy)
                        hit = True
                        break
                if not hit:
                    new_bullets.append(bullet)
            bullets = new_bullets

            if not game_won and player.hitbox.colliderect(exit_rect):
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
        exit_label = font.render("EXIT", True, (255, 255, 255))
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

        lives_label = font.render("LIVES", True, (180, 180, 180))
        screen.blit(lives_label, (20, 18))
        for i in range(INITIAL_LIVES):
            hx = 100 + i * 34
            hy = 18
            if i < lives:
                pygame.draw.rect(screen, HEART_COLOR, (hx, hy, 26, 22),
                                 border_radius=5)
            else:
                pygame.draw.rect(screen, (60, 20, 20), (hx, hy, 26, 22),
                                 border_radius=5)
                pygame.draw.rect(screen, (80, 30, 30), (hx, hy, 26, 22), 1,
                                 border_radius=5)

        if invulnerable > 0:
            inv_text = font.render("INVULNERABLE", True, (255, 255, 100))
            screen.blit(inv_text, (SCREEN_WIDTH - 180, 18))

        if game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(140)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            go = big_font.render("GAME OVER", True, (255, 50, 50))
            screen.blit(go, go.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 - 30)))
            rs = font.render("Press R to restart", True, WHITE)
            screen.blit(rs, rs.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 + 30)))

        if game_won:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(140)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            win = big_font.render("YOU WIN!", True, (50, 255, 50))
            screen.blit(win, win.get_rect(center=(SCREEN_WIDTH // 2,
                                                   SCREEN_HEIGHT // 2 - 30)))
            rs = font.render("Press R to restart", True, WHITE)
            screen.blit(rs, rs.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 + 30)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

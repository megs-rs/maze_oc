Write a complete, single-file Python game using Pygame that meets the following requirements:

- 2D top-down view game
- Player controls a car that always moves forward; arrow keys change direction
- There is a maze made of walls (use a grid-based maze)
- Maze grid is 17×17 for greater layout complexity
- 6 enemy cars that move around the maze, each with a distinct behavior type:
  - 1 **accurate** enemy (20%): BFS shortest-path pursuit, 5% noise; wandering with 50% bias toward the player
  - 2 **medium** enemies (40%): BFS pursuit with 30% noise; wandering with 25% bias toward the player
  - 3 **wall-follower** enemies (40%): right-hand rule maze traversal — keep wall on right side; always active — never use BFS
- Enemy AI details:
  - **Pursuit mode** activates when an enemy is within ~550px of the player (Euclidean distance); otherwise it **wanders**
  - In pursuit, direction is re-evaluated every frame using BFS toward a predicted player position (current position + velocity offset)
  - BFS distance map is recalculated every few frames from the predicted player tile
  - **Noise** means that chance per frame of picking a random valid direction instead of the BFS-optimal step
  - In wandering, direction changes every 10–35 frames; **bias toward player** means that chance of picking the BFS-optimal step instead of a random valid direction (no noise applied in wandering)
  - Wall-followers always use the right-hand rule regardless of distance; direction choices use the grid (not pixel collision probes)
  - All enemies move along grid paths, steering toward tile centers to avoid getting stuck in corners; if stuck for several frames, snap back to the nearest path tile and pick a new direction
- Movement speeds: player ~2.1 px/frame; enemies ~1.0–1.8 px/frame (base 1.4 ± variation)
- When the player collides with any enemy car: both cars show a simple explosion effect, the player loses 1 life, both respawn elsewhere on open paths, and the player gets brief invulnerability (~3 s)
- The player also gets invulnerability (~3 s) when advancing to a new phase
- The player starts with 3 lives
- Player spawn position is always at the farthest reachable tile from the exit (BFS distance), with ~15% noise (tiles within 85% of max distance are candidates); if the chosen tile is too close to an enemy, try another candidate from the same group
- Display the remaining lives on screen (simple hearts or text)
- When lives reach 0, show "GAME OVER" and allow restart with R key
- There is an exit tile visible in the maze; when the player reaches it, the phase is completed and a new phase starts automatically after 10 seconds (press C to skip the countdown). Each new phase generates a new maze with harder enemies.
- Press R to restart the game (resets to phase 1).
- Press SPACE to shoot bullets in the direction the player is facing (short cooldown between shots; bullets stop on walls)
- Enemies hit by a bullet are destroyed (explosion effect) and respawn elsewhere, keeping the total enemy count constant
- Press Q at any time to quit the game
- Press C to skip the phase transition countdown and advance immediately
- Press R to restart the game after game over
- A new maze is generated on each phase (no fixed seed)
- Each phase increases difficulty: enemy speed +15%, noise decreases, pursuit range increases
- Use only Pygame. Draw cars using JPG sprites (jogador.jpg, inimigos.jpg) with transparent backgrounds, scaled to 39x27px
- Keep the code clean, well organized and fully runnable in one file
- Add basic collision detection and smooth movement

Make the maze reasonably complex but not too big. Use a simple algorithm to generate the maze. Prioritize working code over visual perfection.

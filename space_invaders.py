import pygame
import random
import math

# ----- Initialization -----
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Invaders Remake – Insert to Fire, Delete to Switch Weapon")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)
tiny_font = pygame.font.Font(None, 20)

# Colors
BLACK       = (0, 0, 0)
WHITE       = (255, 255, 255)
GREEN       = (0, 255, 0)
RED         = (255, 0, 0)
YELLOW      = (255, 255, 0)
CYAN        = (0, 255, 255)
ORANGE      = (255, 165, 0)
PURPLE      = (160, 32, 240)
BLUE        = (0, 0, 255)
DARKBLUE    = (0, 0, 100)

# Perspective (slower depth change)
PERSPECTIVE_FACTOR = 0.5
MIN_SCALE = 0.4
MAX_SCALE = 2.0
Z_SPEED = 1.5
DEFAULT_Z = 0

# ---------- Particle System ----------
particles = []

class Particle:
    def __init__(self, x, y, color, vx, vy, life, size=3):
        self.x = x
        self.y = y
        self.color = color
        self.vx = vx
        self.vy = vy
        self.life = life
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surf):
        if self.life > 0:
            alpha = min(255, self.life * 10)
            surf.set_alpha(alpha)
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.size)

def spawn_explosion(x, y, color, count=15):
    for _ in range(count):
        vx = random.uniform(-3, 3)
        vy = random.uniform(-3, 3)
        particles.append(Particle(x, y, color, vx, vy, random.randint(10, 30), random.randint(2, 5)))

# ---------- Starfield ----------
class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.speed = random.uniform(0.3, 1.5)
        self.size = random.randint(1, 2)
        self.brightness = random.randint(80, 200)

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, surf):
        color = (self.brightness, self.brightness, self.brightness)
        surf.fill(color, (self.x, self.y, self.size, self.size))

stars = [Star() for _ in range(100)]

# ---------- Player Class ----------
class Player:
    def __init__(self):
        self.base_width = 40
        self.base_height = 30
        self.x = WIDTH // 2 - self.base_width // 2
        self.z = DEFAULT_Z
        self.base_y = HEIGHT - 100
        self.speed = 4
        self.engine_flame = False
        self.weapons = [
            Blaster(), RapidFire(), SpreadShot(), LaserBeam(), HomingMissile()
        ]
        self.current_weapon = 0
        self.bullet_cooldown = 0

    def move(self, keys):
        self.engine_flame = False
        if keys[pygame.K_LEFT] and self.x > 0:
            self.x -= self.speed
            self.engine_flame = True
        if keys[pygame.K_RIGHT] and self.x < WIDTH - self.width:
            self.x += self.speed
            self.engine_flame = True
        if keys[pygame.K_UP]:
            self.z += Z_SPEED
        if keys[pygame.K_DOWN]:
            self.z -= Z_SPEED
        self.z = max(-30, min(30, self.z))

    @property
    def scale(self):
        s = 1.0 - self.z * 0.03
        return max(MIN_SCALE, min(MAX_SCALE, s))

    @property
    def width(self):
        return int(self.base_width * self.scale)

    @property
    def height(self):
        return int(self.base_height * self.scale)

    @property
    def screen_y(self):
        return self.base_y - self.z * PERSPECTIVE_FACTOR

    def draw(self):
        w, h = self.width, self.height
        cx = self.x + w // 2
        top_y = self.screen_y
        bot_y = self.screen_y + h
        body_points = [(cx, top_y), (cx - w//2, bot_y), (cx + w//2, bot_y)]
        pygame.draw.polygon(screen, GREEN, body_points)
        cockpit = ((cx, top_y + h//3), (cx - w//4, bot_y - h//4), (cx + w//4, bot_y - h//4))
        pygame.draw.polygon(screen, (0, 200, 0), cockpit)
        if self.engine_flame and self.z < 15:
            pygame.draw.polygon(screen, (255, 100, 0),
                                [(cx - w//4, bot_y), (cx + w//4, bot_y), (cx, bot_y + h//2)])

    def get_rect(self):
        return pygame.Rect(self.x, self.screen_y, self.width, self.height)

    def get_center(self):
        return (self.x + self.width // 2, self.screen_y + self.height // 2)

    def switch_weapon(self, index):
        if 0 <= index < len(self.weapons):
            self.current_weapon = index

    def next_weapon(self):
        """Cycle to the next weapon."""
        self.current_weapon = (self.current_weapon + 1) % len(self.weapons)

    def fire(self):
        weapon = self.weapons[self.current_weapon]
        cx, cy = self.get_center()
        spawn_y = self.screen_y
        bullets = weapon.fire(cx, spawn_y, self.get_center)
        if weapon.ammo == 0 and self.current_weapon != 0:
            self.switch_weapon(0)
        return bullets

# ---------- Weapons (fixed) ----------
class Weapon:
    def __init__(self, name, ammo, cooldown, color, infinite=False):
        self.name = name
        self.ammo = ammo
        self.max_ammo = ammo
        self.cooldown = cooldown
        self.color = color
        self.infinite = infinite
        self.ammo_consumed = 1

    def fire(self, x, y, get_center_func=None):
        if not self.infinite and self.ammo <= 0:
            return []
        if not self.infinite:
            self.ammo -= self.ammo_consumed
        return self._create_bullets(x, y, get_center_func)

    def _create_bullets(self, x, y, get_center_func):
        return [Bullet(x, y, 0, -6, self.color)]

    def add_ammo(self, amount):
        if not self.infinite:
            self.ammo = min(self.max_ammo, self.ammo + amount)

class Blaster(Weapon):
    def __init__(self):
        super().__init__("Blaster", None, 12, (0, 255, 0), infinite=True)   # Lime green

class RapidFire(Weapon):
    def __init__(self):
        super().__init__("Rapid Fire", 40, 5, YELLOW)

class SpreadShot(Weapon):
    def __init__(self):
        super().__init__("Spread", 30, 18, ORANGE)

    def _create_bullets(self, x, y, get_center_func):
        bullets = []
        for angle in [-15, 0, 15]:
            rad = math.radians(angle - 90)
            vx = 6 * math.cos(rad)
            vy = 6 * math.sin(rad)
            bullets.append(Bullet(x, y, vx, vy, self.color))
        return bullets

class LaserBeam(Weapon):
    def __init__(self):
        super().__init__("Laser", 25, 25, RED)

    def _create_bullets(self, x, y, get_center_func):
        return [Bullet(x, y, 0, 0, self.color, beam=True)]

class HomingMissile(Weapon):
    def __init__(self):
        super().__init__("Homing", 20, 28, PURPLE)

    def _create_bullets(self, x, y, get_center_func):
        return [HomingBullet(x, y, 0, -3, self.color)]

# ---------- Bullets ----------
class Bullet:
    def __init__(self, x, y, vx, vy, color, beam=False):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.radius = 5
        self.beam = beam
        self.life = 5 if beam else None

    def move(self):
        if not self.beam:
            self.x += self.vx
            self.y += self.vy
        else:
            self.life -= 1

    def off_screen(self):
        if self.beam:
            return self.life <= 0
        return (self.x < 0 or self.x > WIDTH or self.y < 0 or self.y > HEIGHT)

    def draw(self, surf):
        if self.beam:
            pygame.draw.line(surf, self.color, (self.x, self.y), (self.x, 0), 3)
        else:
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)

class HomingBullet(Bullet):
    def __init__(self, x, y, vx, vy, color):
        super().__init__(x, y, vx, vy, color)
        self.speed = 4

    def move(self, aliens):
        if aliens:
            nearest = None
            min_dist = float('inf')
            for a in aliens:
                dx = a.x + a.width/2 - self.x
                dy = a.y + a.height/2 - self.y
                dist = math.hypot(dx, dy)
                if dist < min_dist:
                    min_dist = dist
                    nearest = (dx, dy)
            if nearest:
                dx, dy = nearest
                dist = math.hypot(dx, dy)
                if dist > 0:
                    self.vx = (dx / dist) * self.speed
                    self.vy = (dy / dist) * self.speed
        self.x += self.vx
        self.y += self.vy

# ---------- Aliens ----------
class Alien:
    def __init__(self, x, y, alien_type="normal"):
        self.x = x
        self.y = y
        self.width = 30
        self.height = 20
        self.type = alien_type
        self.color = WHITE
        if alien_type == "normal":   pass
        elif alien_type == "spread": self.color = ORANGE
        elif alien_type == "fast":   self.color = YELLOW
        elif alien_type == "beam":   self.color = RED

    def draw(self):
        if self.type == "normal":
            pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
            pygame.draw.circle(screen, BLACK, (self.x+10, self.y+5), 3)
            pygame.draw.circle(screen, BLACK, (self.x+20, self.y+5), 3)
        elif self.type == "spread":
            pygame.draw.polygon(screen, self.color,
                                [(self.x, self.y), (self.x+self.width, self.y),
                                 (self.x+self.width//2, self.y+self.height)])
        elif self.type == "fast":
            pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height//2))
            pygame.draw.rect(screen, RED, (self.x+5, self.y+self.height//2, self.width-10, self.height//2))
        elif self.type == "beam":
            pygame.draw.circle(screen, self.color,
                               (self.x+self.width//2, self.y+self.height//2), self.width//2)

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def fire_bullets(self, target_x, target_y):
        cx = self.x + self.width // 2
        cy = self.y + self.height // 2
        if self.type == "normal":
            dx = target_x - cx; dy = target_y - cy
            dist = math.hypot(dx, dy)
            if dist != 0: vx, vy = (dx/dist)*4, (dy/dist)*4
            else: vx, vy = 0, 4
            return [Bullet(cx, cy, vx, vy, RED)]
        elif self.type == "spread":
            bullets = []
            for angle_offset in [-20, 0, 20]:
                rad = math.atan2(target_y - cy, target_x - cx) + math.radians(angle_offset)
                vx, vy = 4*math.cos(rad), 4*math.sin(rad)
                bullets.append(Bullet(cx, cy, vx, vy, ORANGE))
            return bullets
        elif self.type == "fast":
            dx = target_x - cx; dy = target_y - cy
            dist = math.hypot(dx, dy)
            if dist != 0: vx, vy = (dx/dist)*6, (dy/dist)*6
            else: vx, vy = 0, 6
            return [Bullet(cx, cy, vx, vy, YELLOW)]
        elif self.type == "beam":
            return [Bullet(cx, self.y + self.height, 0, 0, RED, beam=True)]
        return []

# ---------- Ammo Crate ----------
class AmmoCrate:
    def __init__(self, x, y):
        self.x = x; self.y = y
        self.width = 15; self.height = 15
        self.vy = 2
        self.life = 200
    def update(self):
        self.y += self.vy
        self.life -= 1
        if self.y > HEIGHT: self.life = 0
    def draw(self, surf):
        if self.life > 0:
            pygame.draw.rect(surf, (0,255,0), (self.x, self.y, self.width, self.height))
            pygame.draw.line(surf, WHITE, (self.x, self.y), (self.x+self.width, self.y+self.height), 2)
            pygame.draw.line(surf, WHITE, (self.x+self.width, self.y), (self.x, self.y+self.height), 2)
    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

# ---------- Level setup ----------
def get_level_aliens(level):
    rows = 5 + level
    cols = 8 + level
    aliens = []
    start_x, start_y = 100, 50
    gap_x, gap_y = 50, 40
    for r in range(rows):
        for c in range(cols):
            x = start_x + c * gap_x
            y = start_y + r * gap_y
            typ = "normal"
            if level >= 2 and r == 0: typ = "spread"
            if level >= 3 and r == 1: typ = "fast"
            if level >= 4 and r == 2: typ = "beam"
            if level >= 5 and r == rows-1: typ = "spread"
            aliens.append(Alien(x, y, typ))
    return aliens

def reset_level(player, level):
    aliens = get_level_aliens(level)
    alien_dir = 1
    alien_speed_x = 0.8 + level * 0.3
    alien_drop = 20
    alien_bullets = []
    player_bullets = []
    shoot_timer = 0
    score = player.score
    ammo_crates = []
    return (aliens, alien_dir, alien_speed_x, alien_drop,
            alien_bullets, player_bullets, shoot_timer, score, ammo_crates)

def get_shooters(alien_list):
    col_dict = {}
    for a in alien_list:
        if a.x not in col_dict or a.y > col_dict[a.x].y:
            col_dict[a.x] = a
    return list(col_dict.values())

# ---------- Game states ----------
MENU = 0
PLAYING = 1
LEVEL_COMPLETE = 2
GAME_OVER = 3

def draw_menu():
    for star in stars:
        star.update()
        star.draw(screen)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0,0,0,160))
    screen.blit(overlay, (0,0))

    title = font.render("SPACE INVADERS Remake", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))

    # Updated controls with Insert / Delete
    controls = [
        "Arrow Keys: Move (Left/Right & Depth Up/Down)",
        "Insert: Fire current weapon",
        "Delete: Switch to next weapon",
        "Right SHIFT: Restart after game over",
        "",
        "Pick up green ammo crates!",
    ]
    y = 120
    for line in controls:
        text = small_font.render(line, True, WHITE)
        screen.blit(text, (50, y))
        y += 25

    # Weapon showcase (unchanged)
    weapons_info = [
        ("Blaster", (0, 255, 0), "Unlimited ammo"),
        ("Rapid Fire", YELLOW, "Ammo 40"),
        ("Spread Shot", ORANGE, "Ammo 30"),
        ("Laser Beam", RED, "Ammo 25"),
        ("Homing Missile", PURPLE, "Ammo 20"),
    ]
    y += 10
    screen.blit(small_font.render("Weapons:", True, WHITE), (50, y))
    y += 30
    for name, color, ammo in weapons_info:
        pygame.draw.circle(screen, color, (70, y+8), 5)
        txt = tiny_font.render(f"{name}  {ammo}", True, color)
        screen.blit(txt, (90, y))
        y += 22

    y += 20
    prompt = font.render("Press any key to start", True, GREEN)
    screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, y))

# ---------- Main Game ----------
def main():
    state = MENU
    level = 1
    player = Player()
    player.score = 0
    (aliens, alien_dir, alien_speed_x, alien_drop,
     alien_bullets, player_bullets, shoot_timer, score, ammo_crates) = reset_level(player, level)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if state == MENU:
                    state = PLAYING
                    player = Player()
                    player.score = 0
                    level = 1
                    (aliens, alien_dir, alien_speed_x, alien_drop,
                     alien_bullets, player_bullets, shoot_timer, score, ammo_crates) = reset_level(player, level)
                elif state == PLAYING:
                    if event.key == pygame.K_RSHIFT:
                        player = Player()
                        player.score = 0
                        level = 1
                        (aliens, alien_dir, alien_speed_x, alien_drop,
                         alien_bullets, player_bullets, shoot_timer, score, ammo_crates) = reset_level(player, level)
                    # Cycle weapon with Delete
                    if event.key == pygame.K_DELETE:
                        player.next_weapon()
                    # Fallback: still allow direct selection with 1-5 if desired
                    if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                        player.switch_weapon(event.key - pygame.K_1)
                elif state in (GAME_OVER, LEVEL_COMPLETE):
                    if event.key == pygame.K_RSHIFT:
                        player = Player()
                        player.score = 0
                        level = 1
                        state = PLAYING
                        (aliens, alien_dir, alien_speed_x, alien_drop,
                         alien_bullets, player_bullets, shoot_timer, score, ammo_crates) = reset_level(player, level)
                    elif state == LEVEL_COMPLETE and event.key == pygame.K_RETURN:
                        state = PLAYING
                        (aliens, alien_dir, alien_speed_x, alien_drop,
                         alien_bullets, player_bullets, shoot_timer, score, ammo_crates) = reset_level(player, level)

        keys = pygame.key.get_pressed()

        # --- Update logic ---
        if state == PLAYING:
            player.move(keys)
            if player.bullet_cooldown > 0:
                player.bullet_cooldown -= 1
            # Fire with Insert key instead of Space
            if keys[pygame.K_INSERT] and player.bullet_cooldown == 0:
                new_bullets = player.fire()
                player_bullets.extend(new_bullets)
                player.bullet_cooldown = player.weapons[player.current_weapon].cooldown

            # (Rest of the update loop remains identical)
            # ... (alien movement, shooting, collisions, etc.)
            # I'll include the whole block for completeness but highlight only the changes.

            # Alien movement
            hit_edge = False
            for a in aliens:
                if (a.x + alien_dir * alien_speed_x < 0) or (a.x + a.width + alien_dir * alien_speed_x > WIDTH):
                    hit_edge = True
                    break
            if hit_edge:
                alien_dir *= -1
                for a in aliens:
                    a.y += alien_drop
                    if a.y + a.height >= player.screen_y + player.height:
                        state = GAME_OVER
            for a in aliens:
                a.x += alien_dir * alien_speed_x

            if aliens:
                alien_speed_x = 0.8 + level * 0.3 + (len(aliens) / 10) * 0.1
            else:
                state = LEVEL_COMPLETE
                level += 1 if level < 10 else 1   # cap at 10 to avoid endless growth
                (aliens, alien_dir, alien_speed_x, alien_drop,
                 alien_bullets, player_bullets, shoot_timer, score, ammo_crates) = reset_level(player, level)

            # Alien shooting
            shoot_timer += 1
            if shoot_timer > max(15, 35 - level*2):
                shoot_timer = 0
                if aliens:
                    shooters = get_shooters(aliens)
                    if shooters:
                        shooter = random.choice(shooters)
                        px, py = player.get_center()
                        alien_bullets.extend(shooter.fire_bullets(px, py))

            # Move bullets
            for b in player_bullets:
                if isinstance(b, HomingBullet):
                    b.move(aliens)
                else:
                    b.move()
            for b in alien_bullets:
                b.move()
            for crate in ammo_crates:
                crate.update()

            player_bullets = [b for b in player_bullets if not b.off_screen()]
            alien_bullets = [b for b in alien_bullets if not b.off_screen()]
            ammo_crates = [c for c in ammo_crates if c.life > 0]

            # Collisions (unchanged)
            # Player bullets vs aliens
            for pb in player_bullets[:]:
                if pb.beam:
                    for a in aliens[:]:
                        if a.x <= pb.x <= a.x + a.width and a.y <= pb.y:
                            aliens.remove(a)
                            spawn_explosion(a.x+a.width//2, a.y+a.height//2, a.color)
                            player.score += 10
                            if random.random() < 0.15:
                                ammo_crates.append(AmmoCrate(a.x+a.width//2, a.y+a.height))
                else:
                    pb_rect = pygame.Rect(pb.x-pb.radius, pb.y-pb.radius, pb.radius*2, pb.radius*2)
                    for a in aliens[:]:
                        if pb_rect.colliderect(a.get_rect()):
                            if pb in player_bullets: player_bullets.remove(pb)
                            aliens.remove(a)
                            spawn_explosion(a.x+a.width//2, a.y+a.height//2, a.color)
                            player.score += 10
                            if random.random() < 0.15:
                                ammo_crates.append(AmmoCrate(a.x+a.width//2, a.y+a.height))
                            break

            # Alien bullets vs player
            player_rect = player.get_rect()
            for ab in alien_bullets:
                if ab.beam:
                    if player_rect.left <= ab.x <= player_rect.right and player_rect.top <= ab.y:
                        state = GAME_OVER
                        spawn_explosion(player_rect.centerx, player_rect.centery, RED, 30)
                        break
                else:
                    ab_rect = pygame.Rect(ab.x-ab.radius, ab.y-ab.radius, ab.radius*2, ab.radius*2)
                    if ab_rect.colliderect(player_rect):
                        state = GAME_OVER
                        spawn_explosion(player_rect.centerx, player_rect.centery, RED, 30)
                        break

            # Ammo pickup
            player_rect = player.get_rect()
            for crate in ammo_crates[:]:
                if player_rect.colliderect(crate.get_rect()):
                    player.weapons[player.current_weapon].add_ammo(15)
                    ammo_crates.remove(crate)

            # Particles
            for p in particles: p.update()
            particles[:] = [p for p in particles if p.life > 0]

        # --- Drawing ---
        screen.fill(BLACK)
        for star in stars:
            star.update()
            star.draw(screen)

        if state == MENU:
            draw_menu()
        elif state == PLAYING:
            player.draw()
            for a in aliens: a.draw()
            for b in player_bullets: b.draw(screen)
            for b in alien_bullets: b.draw(screen)
            for crate in ammo_crates: crate.draw(screen)
            for p in particles: p.draw(screen)

            # HUD
            score_text = font.render(f"Score: {player.score}", True, WHITE)
            screen.blit(score_text, (10, 10))
            level_text = font.render(f"Level: {level}", True, WHITE)
            screen.blit(level_text, (WIDTH-100, 10))
            weapon = player.weapons[player.current_weapon]
            ammo_display = "∞" if weapon.infinite else str(weapon.ammo)
            weapon_text = font.render(f"{weapon.name}: {ammo_display}", True, weapon.color)
            screen.blit(weapon_text, (10, 50))
            # Show current weapon number
            wpn_num = tiny_font.render(f"Delete to cycle (now {player.current_weapon+1})", True, WHITE)
            screen.blit(wpn_num, (10, 80))
        elif state == LEVEL_COMPLETE:
            txt = font.render(f"Level {level-1} Complete! Press Enter for next level.", True, WHITE)
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2))
        elif state == GAME_OVER:
            txt = font.render("GAME OVER – Press Right Shift to restart", True, WHITE)
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 20))
            score_txt = font.render(f"Final Score: {player.score}", True, WHITE)
            screen.blit(score_txt, (WIDTH//2 - score_txt.get_width()//2, HEIGHT//2 + 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()

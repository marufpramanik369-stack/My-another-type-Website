import os
import time
import random
import sys

# ============================================================
#   TURBO RACER - Terminal Car Racing Game
#   Pure Python - No extra library needed!
#   Controls: A/D = Steer, SPACE = Boost, P = Pause, Q = Quit
# ============================================================

WIDTH  = 50
HEIGHT = 22

# --- Symbols ---
PLAYER_CAR  = "A"
ENEMY_CAR   = "V"
ROAD_LINE   = "|"
GRASS       = "#"
BOOST_PAD   = "="
COIN        = "o"
OIL         = "@"
BARRIER     = "X"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def hide_cursor():
    try:
        if os.name == 'nt':
            import ctypes
            class CCI(ctypes.Structure):
                _fields_ = [("dwSize", ctypes.c_int), ("bVisible", ctypes.c_int)]
            h = ctypes.windll.kernel32.GetStdHandle(-11)
            ci = CCI()
            ctypes.windll.kernel32.GetConsoleCursorInfo(h, ctypes.byref(ci))
            ci.bVisible = 0
            ctypes.windll.kernel32.SetConsoleCursorInfo(h, ctypes.byref(ci))
    except:
        pass

def show_cursor():
    try:
        if os.name == 'nt':
            import ctypes
            class CCI(ctypes.Structure):
                _fields_ = [("dwSize", ctypes.c_int), ("bVisible", ctypes.c_int)]
            h = ctypes.windll.kernel32.GetStdHandle(-11)
            ci = CCI()
            ctypes.windll.kernel32.GetConsoleCursorInfo(h, ctypes.byref(ci))
            ci.bVisible = 1
            ctypes.windll.kernel32.SetConsoleCursorInfo(h, ctypes.byref(ci))
    except:
        pass

def get_key():
    try:
        if os.name == 'nt':
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch()
                try:
                    return key.decode('utf-8').lower()
                except:
                    return ''
        else:
            import sys, tty, termios, select
            if select.select([sys.stdin], [], [], 0)[0]:
                old = termios.tcgetattr(sys.stdin)
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
                return ch.lower()
    except:
        pass
    return ''

# ============================================================
#   ROAD GENERATOR
# ============================================================

class Road:
    def __init__(self):
        self.road_x    = WIDTH // 2
        self.road_w    = 18
        self.rows      = []
        self.curve_dir = 1
        self.curve_amt = 0
        self.curve_timer = 0
        for _ in range(HEIGHT):
            self.rows.append(self._make_row(self.road_x, self.road_w))

    def _make_row(self, cx, rw, obj=None):
        left  = cx - rw // 2
        right = cx + rw // 2
        row   = []
        for x in range(WIDTH):
            if x < left or x > right:
                row.append(GRASS)
            elif x == left or x == right:
                row.append(ROAD_LINE)
            else:
                row.append(" ")
        if obj and left < obj[0] < right:
            row[obj[0]] = obj[1]
        return row

    def scroll(self, speed, obj=None):
        # Curve logic
        self.curve_timer += 1
        if self.curve_timer >= random.randint(30, 60):
            self.curve_timer = 0
            self.curve_dir  = random.choice([-1, 1])
            self.curve_amt  = random.randint(0, 2)

        self.road_x += self.curve_dir * self.curve_amt * 0.3
        self.road_x  = max(self.road_w // 2 + 2, min(WIDTH - self.road_w // 2 - 2, self.road_x))

        # Narrow/widen road by level
        new_row = self._make_row(int(self.road_x), self.road_w, obj)
        self.rows.pop()
        self.rows.insert(0, new_row)

    def get_road_bounds(self, y):
        row = self.rows[y]
        left, right = 0, WIDTH - 1
        for x in range(WIDTH):
            if row[x] == ROAD_LINE:
                left = x
                break
        for x in range(WIDTH - 1, -1, -1):
            if row[x] == ROAD_LINE:
                right = x
                break
        return left, right

# ============================================================
#   OBJECTS ON ROAD
# ============================================================

class RoadObject:
    def __init__(self, x, y, symbol):
        self.x      = x
        self.y      = y
        self.symbol = symbol
        self.alive  = True

# ============================================================
#   PLAYER
# ============================================================

class Player:
    def __init__(self):
        self.x         = WIDTH // 2
        self.y         = HEIGHT - 3
        self.speed     = 3
        self.boost     = False
        self.boost_timer = 0
        self.boost_fuel  = 100
        self.max_boost   = 100
        self.hp          = 5
        self.max_hp      = 5
        self.score       = 0
        self.distance    = 0
        self.coins       = 0
        self.skid        = 0
        self.invincible  = 0
        self.drift_x     = 0.0

    def move_left(self):
        if self.skid == 0:
            self.x -= 2 if self.boost else 1
            self.drift_x = -1.5
        self.x = max(1, self.x)

    def move_right(self):
        if self.skid == 0:
            self.x += 2 if self.boost else 1
            self.drift_x = 1.5
        self.x = min(WIDTH - 2, self.x)

    def use_boost(self):
        if self.boost_fuel > 10:
            self.boost       = True
            self.boost_timer = 20
            self.boost_fuel  = max(0, self.boost_fuel - 20)

    def update(self):
        if self.boost_timer > 0:
            self.boost_timer -= 1
            if self.boost_timer == 0:
                self.boost = False
        if self.boost_fuel < self.max_boost:
            self.boost_fuel += 0.5

        if self.skid > 0:
            self.skid -= 1
            self.x += random.randint(-1, 1)
            self.x = max(1, min(WIDTH - 2, self.x))

        if self.invincible > 0:
            self.invincible -= 1

        self.drift_x *= 0.7

# ============================================================
#   ENEMY CAR
# ============================================================

class EnemyCar:
    def __init__(self, x, y, color=None):
        self.x       = x
        self.y       = y
        self.alive   = True
        self.speed   = random.uniform(0.3, 0.8)
        self.swerve  = random.choice([-1, 0, 0, 1])
        self.timer   = 0
        self.symbol  = random.choice(["V", "U", "T"])

    def update(self):
        self.timer += 1
        if self.timer % 8 == 0:
            self.swerve = random.choice([-1, 0, 0, 0, 1])
        self.x += self.swerve
        self.x  = max(2, min(WIDTH - 3, self.x))

# ============================================================
#   GAME
# ============================================================

class Game:
    def __init__(self):
        self.player      = Player()
        self.road        = Road()
        self.enemies     = []
        self.road_objs   = []
        self.frame       = 0
        self.base_speed  = 1
        self.game_over   = False
        self.paused      = False
        self.level       = 1
        self.level_timer = 0
        self.message     = ""
        self.msg_timer   = 0
        self.high_score  = 0
        self.scroll_frac = 0.0
        self.spawn_timer = 0
        self.obj_timer   = 0
        self.weather     = "clear"
        self.weather_timer = 0
        self.particles   = []

    def show_msg(self, msg):
        self.message   = msg
        self.msg_timer = 50

    def get_speed(self):
        spd = self.base_speed + self.level * 0.3
        if self.player.boost:
            spd *= 1.8
        return spd

    def spawn_enemy(self):
        left, right = self.road.get_road_bounds(2)
        if right - left < 4:
            return
        x = random.randint(left + 2, right - 2)
        self.enemies.append(EnemyCar(x, 1))

    def spawn_road_obj(self):
        left, right = self.road.get_road_bounds(3)
        if right - left < 4:
            return
        x    = random.randint(left + 2, right - 2)
        kind = random.choices(
            [COIN, BOOST_PAD, OIL, BARRIER],
            weights=[50, 20, 15, 15]
        )[0]
        self.road_objs.append(RoadObject(x, 1, kind))

    def update(self):
        if self.game_over or self.paused:
            return

        self.frame      += 1
        self.level_timer += 1
        p                = self.player

        # Level up every 300 frames
        if self.level_timer >= 300:
            self.level_timer = 0
            self.level      += 1
            self.base_speed += 0.2
            self.show_msg(f"LEVEL {self.level}! Speed up!")
            if self.level % 3 == 0:
                self.road.road_w = max(10, self.road.road_w - 1)

        # Weather
        self.weather_timer += 1
        if self.weather_timer >= 400:
            self.weather_timer = 0
            self.weather = random.choice(["clear", "clear", "rain", "fog"])
            if self.weather == "rain":
                self.show_msg("Rain! Slippery road!")
            elif self.weather == "fog":
                self.show_msg("Fog! Reduced visibility!")

        spd = self.get_speed()

        # Scroll road
        self.scroll_frac += spd
        while self.scroll_frac >= 1:
            self.scroll_frac -= 1

            # Pick object to embed in new row
            obj = None
            self.road.scroll(spd, obj)

            # Scroll enemies
            for e in self.enemies:
                e.y += 1

            # Scroll road objects
            for ro in self.road_objs:
                ro.y += 1

        # Spawn enemies
        self.spawn_timer += 1
        spawn_interval = max(15, 40 - self.level * 2)
        if self.spawn_timer >= spawn_interval:
            self.spawn_timer = 0
            if random.random() < 0.7:
                self.spawn_enemy()

        # Spawn road objects
        self.obj_timer += 1
        if self.obj_timer >= 20:
            self.obj_timer = 0
            if random.random() < 0.6:
                self.spawn_road_obj()

        # Update enemies
        for e in self.enemies:
            e.update()

        # Update player
        p.update()
        p.distance += spd
        p.score     = int(p.distance * 0.1) + p.coins * 50

        # Remove off-screen enemies
        self.enemies   = [e for e in self.enemies if e.y < HEIGHT and e.alive]
        self.road_objs = [r for r in self.road_objs if r.y < HEIGHT and r.alive]

        # Check if player on grass
        left, right = self.road.get_road_bounds(p.y)
        if p.x <= left or p.x >= right:
            p.skid = 10
            if p.invincible == 0:
                p.hp -= 1
                p.invincible = 30
                self.show_msg("Off road! -1 HP")
                if p.hp <= 0:
                    self.game_over = True
                    if p.score > self.high_score:
                        self.high_score = p.score

        # Rain effect: more skid
        if self.weather == "rain" and random.random() < 0.03:
            p.skid = max(p.skid, 3)

        # Collision: player vs enemy
        for e in self.enemies:
            if abs(e.x - p.x) <= 1 and abs(e.y - p.y) <= 1:
                if p.invincible == 0:
                    e.alive  = False
                    p.hp    -= 2
                    p.skid   = 15
                    p.invincible = 40
                    self.show_msg("CRASH! -2 HP!")
                    for _ in range(6):
                        self.particles.append([e.x, e.y, random.uniform(-2,2), random.uniform(-2,0), 8])
                    if p.hp <= 0:
                        self.game_over = True
                        if p.score > self.high_score:
                            self.high_score = p.score

        # Collision: player vs road objects
        for ro in self.road_objs:
            if abs(ro.x - p.x) <= 1 and abs(ro.y - p.y) <= 1:
                ro.alive = False
                if ro.symbol == COIN:
                    p.coins  += 1
                    self.show_msg(f"Coin! Total: {p.coins}")
                elif ro.symbol == BOOST_PAD:
                    p.boost_fuel = min(p.max_boost, p.boost_fuel + 40)
                    self.show_msg("Boost refill!")
                elif ro.symbol == OIL:
                    p.skid = 20
                    self.show_msg("Oil! Skidding!")
                elif ro.symbol == BARRIER:
                    if p.invincible == 0:
                        p.hp -= 1
                        p.invincible = 25
                        self.show_msg("Barrier! -1 HP")
                        if p.hp <= 0:
                            self.game_over = True

        # Update particles
        new_parts = []
        for pt in self.particles:
            pt[0] += pt[2]
            pt[1] += pt[3]
            pt[3] += 0.5
            pt[4] -= 1
            if pt[4] > 0:
                new_parts.append(pt)
        self.particles = new_parts

        # Msg timer
        if self.msg_timer > 0:
            self.msg_timer -= 1

    def render(self):
        p    = self.player
        grid = [list(row) for row in self.road.rows]

        # Weather rain effect
        if self.weather == "rain":
            for _ in range(8):
                rx = random.randint(1, WIDTH - 2)
                ry = random.randint(0, HEIGHT - 1)
                if grid[ry][rx] == " ":
                    grid[ry][rx] = "'"

        # Draw road objects
        for ro in self.road_objs:
            if 0 <= ro.y < HEIGHT and 0 <= ro.x < WIDTH:
                grid[ro.y][ro.x] = ro.symbol

        # Draw particles
        for pt in self.particles:
            px, py = int(pt[0]), int(pt[1])
            if 0 <= py < HEIGHT and 0 <= px < WIDTH:
                grid[py][px] = "*"

        # Draw enemies
        for e in self.enemies:
            if 0 <= e.y < HEIGHT and 0 <= e.x < WIDTH:
                grid[e.y][e.x] = e.symbol
                # Car body
                if e.y + 1 < HEIGHT and e.x > 0 and e.x < WIDTH-1:
                    grid[e.y][e.x-1] = "["
                    grid[e.y][e.x+1] = "]"

        # Draw player (blink when invincible)
        if p.invincible == 0 or p.invincible % 4 < 2:
            if 0 <= p.y < HEIGHT and 0 <= p.x < WIDTH:
                grid[p.y][p.x]     = PLAYER_CAR
                if p.x > 0:
                    grid[p.y][p.x - 1] = "/"
                if p.x < WIDTH - 1:
                    grid[p.y][p.x + 1] = "\\"
                if p.y + 1 < HEIGHT:
                    grid[p.y + 1][p.x] = "U"

        # Fog effect: hide top rows
        if self.weather == "fog":
            for y in range(min(8, HEIGHT)):
                for x in range(WIDTH):
                    if grid[y][x] not in (ROAD_LINE, GRASS):
                        grid[y][x] = "~" if random.random() < 0.3 else " "

        # Build lines
        lines = []

        # HUD top
        hp_bar    = "[" + "♥" * p.hp + "-" * (p.max_hp - p.hp) + "]"
        boost_bar = "[" + "=" * int(p.boost_fuel / 10) + "." * (10 - int(p.boost_fuel / 10)) + "]"
        boost_lbl = "BOOST" if p.boost else "     "
        weather_lbl = {"clear":"☀ CLEAR","rain":"☂ RAIN ","fog":"≋ FOG  "}.get(self.weather,"      ")
        lines.append(f" HP:{hp_bar} BOOST:{boost_bar}{boost_lbl} {weather_lbl}")

        for row in grid:
            lines.append("".join(row))

        # Bottom HUD
        spd_val  = int(self.get_speed() * 60)
        dist_val = int(p.distance)
        lvl_str  = f"LV:{self.level}"
        scr_str  = f"SCORE:{p.score:06d}"
        coi_str  = f"COINS:{p.coins}"
        spd_str  = f"SPD:{spd_val}km/h"
        lines.append(f" {lvl_str}  {scr_str}  {coi_str}  {spd_str}  DIST:{dist_val}m")

        # Controls
        lines.append(" A/D=Steer  SPACE=Boost  P=Pause  Q=Quit")

        # Message
        if self.msg_timer > 0:
            lines.append(f" >> {self.message} <<")
        else:
            lines.append("")

        return "\n".join(lines)

    def render_game_over(self):
        lines = []
        p     = self.player
        lines.append("=" * WIDTH)
        lines.append("  GAME OVER - CRASH!".center(WIDTH))
        lines.append("=" * WIDTH)
        lines.append("")
        lines.append(f"  Final Score  : {p.score}")
        lines.append(f"  High Score   : {self.high_score}")
        lines.append(f"  Distance     : {int(p.distance)} m")
        lines.append(f"  Level Reached: {self.level}")
        lines.append(f"  Coins        : {p.coins}")
        lines.append("")
        lines.append("  Press R to Race Again")
        lines.append("  Press Q to Quit")
        lines.append("")
        lines.append("=" * WIDTH)
        return "\n".join(lines)

    def render_paused(self):
        lines = []
        lines.append("=" * WIDTH)
        lines.append("  PAUSED".center(WIDTH))
        lines.append("=" * WIDTH)
        lines.append("")
        lines.append(f"  Score   : {self.player.score}")
        lines.append(f"  Level   : {self.level}")
        lines.append(f"  Distance: {int(self.player.distance)} m")
        lines.append("")
        lines.append("  P = Resume")
        lines.append("  Q = Quit")
        lines.append("=" * WIDTH)
        return "\n".join(lines)

# ============================================================
#   INTRO SCREEN
# ============================================================

def show_intro():
    clear_screen()
    print("=" * 50)
    print(r"""
  _______ _    _ _____  ____   ____
 |__   __| |  | |  __ \|  _ \ / __ \
    | |  | |  | | |__) | |_) | |  | |
    | |  | |  | |  _  /|  _ <| |  | |
    | |  | |__| | | \ \| |_) | |__| |
    |_|   \____/|_|  \_\____/ \____/
         RACER  -  Terminal Edition
    """)
    print("=" * 50)
    print()
    print("  CONTROLS:")
    print("   A        = Steer Left")
    print("   D        = Steer Right")
    print("   SPACE    = TURBO BOOST!")
    print("   P        = Pause")
    print("   Q        = Quit / Restart")
    print("=" * 50)
    print("  ROAD OBJECTS:")
    print("   o  = Coin (+50 points)")
    print("   =  = Boost Pad (refills boost)")
    print("   @  = Oil Spill (you skid!)")
    print("   X  = Barrier (avoid it!)")
    print()
    print("  ENEMIES:")
    print("   V/U/T = Enemy Cars (avoid crash!)")
    print()
    print("  WEATHER: Rain = slippery, Fog = low visibility!")
    print()
    print("  Survive as long as possible!")
    print("  Speed increases every level!")
    print()
    print("=" * 50)
    print("  Press ENTER to Start Racing...")
    input()

# ============================================================
#   MAIN
# ============================================================

def main():
    try:
        hide_cursor()
        show_intro()

        play_again = True
        while play_again:
            game     = Game()
            last_t   = time.time()
            fps      = 12

            while True:
                now = time.time()
                if now - last_t >= 1.0 / fps:
                    last_t = now
                    key    = get_key()

                    if game.game_over:
                        if key == 'q':
                            play_again = False
                            break
                        elif key == 'r':
                            break

                    elif game.paused:
                        if key == 'p':
                            game.paused = False
                        elif key == 'q':
                            play_again = False
                            break

                    else:
                        if key == 'a':
                            game.player.move_left()
                        elif key == 'd':
                            game.player.move_right()
                        elif key == ' ':
                            game.player.use_boost()
                        elif key == 'p':
                            game.paused = True
                        elif key == 'q':
                            play_again = False
                            break

                        game.update()

                    clear_screen()
                    if game.game_over:
                        print(game.render_game_over())
                    elif game.paused:
                        print(game.render_paused())
                    else:
                        print(game.render())

    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        clear_screen()
        print("=" * 40)
        print("  Thanks for playing Turbo Racer!")
        print("=" * 40)

if __name__ == "__main__":
    main()
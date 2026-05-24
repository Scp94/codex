import json
import math
import random
import sys
from pathlib import Path

import pygame


# 游戏窗口和网格设置
CELL_SIZE = 24
GRID_WIDTH = 25
GRID_HEIGHT = 20
WINDOW_WIDTH = CELL_SIZE * GRID_WIDTH
WINDOW_HEIGHT = CELL_SIZE * GRID_HEIGHT + 48
FPS = 60
MOVE_INTERVAL_MS = 90
BOARD_TOP = 48
LEADERBOARD_FILE = Path(__file__).with_name("leaderboard.json")
LEADERBOARD_LIMIT = 10
STATE_START = "start"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"

# 常用颜色
WHITE = (245, 245, 245)
BLACK = (20, 20, 20)
GREEN = (52, 168, 83)
DARK_GREEN = (32, 120, 57)
RED = (234, 67, 53)
GRAY = (70, 70, 70)
YELLOW = (251, 188, 5)
BLUE = (66, 133, 244)
BOARD_BG = (17, 24, 20)
GRID_LINE = (27, 42, 34)
LIGHT_GREEN = (91, 220, 117)
FOOD_GLOW = (255, 112, 94)
SHADOW = (6, 10, 8)


def load_font(size, bold=False):
    """加载支持中文的字体，找不到时使用 Pygame 默认字体。"""
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in font_paths:
        if not Path(path).exists():
            continue
        try:
            font = pygame.font.Font(path, size)
            font.set_bold(bold)
            return font
        except pygame.error:
            continue

    font_names = [
        "PingFang SC",
        "STHeiti Medium",
        "STHeiti",
        "Heiti SC",
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Noto Sans CJK SC",
        "Noto Sans CJK",
        "WenQuanYi Micro Hei",
        "Arial Unicode MS",
    ]
    for name in font_names:
        font_path = pygame.font.match_font(name)
        if font_path:
            try:
                font = pygame.font.Font(font_path, size)
                font.set_bold(bold)
                return font
            except pygame.error:
                continue

    for name in font_names:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except pygame.error:
            continue

    return pygame.font.Font(None, size)


def random_food(snake):
    """生成一个不和蛇身体重叠的食物位置。"""
    empty_cells = [
        (x, y)
        for x in range(GRID_WIDTH)
        for y in range(GRID_HEIGHT)
        if (x, y) not in snake
    ]
    return random.choice(empty_cells)


def load_leaderboard():
    """读取排行榜，文件不存在或内容异常时返回空榜。"""
    if not LEADERBOARD_FILE.exists():
        return []

    try:
        scores = json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    valid_scores = [score for score in scores if isinstance(score, int) and score >= 0]
    return sorted(valid_scores, reverse=True)[:LEADERBOARD_LIMIT]


def save_leaderboard(scores):
    """保存排行榜，只保留前 10 名。"""
    top_scores = sorted(scores, reverse=True)[:LEADERBOARD_LIMIT]
    LEADERBOARD_FILE.write_text(
        json.dumps(top_scores, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_score(score, leaderboard):
    """记录本局分数并返回新的排行榜。"""
    leaderboard = [*leaderboard, score]
    save_leaderboard(leaderboard)
    return load_leaderboard()


def reset_game():
    """重置游戏状态。"""
    start_x = GRID_WIDTH // 2
    start_y = GRID_HEIGHT // 2
    snake = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
    direction = (1, 0)
    next_direction = direction
    food = random_food(snake)
    score = 0
    game_over = False
    return snake, direction, next_direction, food, score, game_over


def lerp(start, end, progress):
    """在两个数值之间平滑插值。"""
    return start + (end - start) * progress


def ease_out_cubic(progress):
    """让移动开始更利落，停靠时更柔和。"""
    return 1 - (1 - progress) ** 3


def cell_center(cell):
    """返回格子中心点的屏幕坐标。"""
    return (
        cell[0] * CELL_SIZE + CELL_SIZE / 2,
        cell[1] * CELL_SIZE + BOARD_TOP + CELL_SIZE / 2,
    )


def interpolated_snake(previous_snake, snake, progress):
    """根据上一步和当前蛇身，计算用于绘制的浮点格子坐标。"""
    smooth_progress = ease_out_cubic(progress)
    points = []
    for index, current in enumerate(snake):
        previous = previous_snake[index] if index < len(previous_snake) else current
        x = lerp(previous[0], current[0], smooth_progress)
        y = lerp(previous[1], current[1], smooth_progress)
        points.append((x, y))
    return points


def spawn_eat_effects(food_cell, direction):
    """吃到食物时产生一圈轻量粒子。"""
    center_x, center_y = cell_center(food_cell)
    particles = []
    for index in range(10):
        angle = math.tau * index / 10
        speed = random.uniform(22, 46)
        particles.append(
            {
                "x": center_x,
                "y": center_y,
                "vx": math.cos(angle) * speed - direction[0] * 12,
                "vy": math.sin(angle) * speed - direction[1] * 12,
                "age": 0,
                "life": random.randint(260, 420),
                "radius": random.uniform(2.5, 4.5),
            }
        )
    return particles


def update_particles(particles, elapsed_ms):
    """推进粒子动画并移除已消散的粒子。"""
    alive_particles = []
    for particle in particles:
        particle["age"] += elapsed_ms
        if particle["age"] >= particle["life"]:
            continue
        delta = elapsed_ms / 1000
        particle["x"] += particle["vx"] * delta
        particle["y"] += particle["vy"] * delta
        particle["vy"] += 38 * delta
        alive_particles.append(particle)
    return alive_particles


def draw_text(surface, font, text, color, center):
    """按中心点绘制文字。"""
    image = font.render(text, True, color)
    rect = image.get_rect(center=center)
    surface.blit(image, rect)


def draw_leaderboard(surface, font, leaderboard, x, y):
    """绘制排行榜。"""
    title = font.render("排行榜 TOP 10", True, YELLOW)
    surface.blit(title, (x, y))

    if not leaderboard:
        empty_text = font.render("暂无分数", True, WHITE)
        surface.blit(empty_text, (x, y + 34))
        return

    for index, board_score in enumerate(leaderboard, start=1):
        rank_text = font.render(f"{index:>2}. {board_score}", True, WHITE)
        surface.blit(rank_text, (x, y + 32 + (index - 1) * 22))


def draw_grid(screen):
    """绘制棋盘底色和细网格。"""
    board_rect = pygame.Rect(0, BOARD_TOP, WINDOW_WIDTH, GRID_HEIGHT * CELL_SIZE)
    pygame.draw.rect(screen, BOARD_BG, board_rect)
    for x in range(0, WINDOW_WIDTH + 1, CELL_SIZE):
        pygame.draw.line(screen, GRID_LINE, (x, BOARD_TOP), (x, WINDOW_HEIGHT), 1)
    for y in range(BOARD_TOP, WINDOW_HEIGHT + 1, CELL_SIZE):
        pygame.draw.line(screen, GRID_LINE, (0, y), (WINDOW_WIDTH, y), 1)


def draw_food(screen, food, now_ms):
    """绘制带呼吸效果的食物。"""
    center_x, center_y = cell_center(food)
    pulse = (math.sin(now_ms / 180) + 1) / 2
    glow_radius = 15 + pulse * 5
    glow = pygame.Surface((CELL_SIZE * 3, CELL_SIZE * 3), pygame.SRCALPHA)
    pygame.draw.circle(
        glow,
        (*FOOD_GLOW, int(44 + pulse * 36)),
        (CELL_SIZE * 3 // 2, CELL_SIZE * 3 // 2),
        int(glow_radius),
    )
    screen.blit(glow, (int(center_x - CELL_SIZE * 1.5), int(center_y - CELL_SIZE * 1.5)))

    radius = 7 + pulse * 2
    pygame.draw.circle(screen, RED, (int(center_x), int(center_y)), int(radius))
    pygame.draw.circle(
        screen,
        (255, 176, 159),
        (int(center_x - 3), int(center_y - 3)),
        int(max(2, radius / 3)),
    )


def draw_snake(screen, snake_points, direction, state, now_ms):
    """绘制平滑移动的蛇身。"""
    if not snake_points:
        return

    for index in range(len(snake_points) - 1, -1, -1):
        x, y = snake_points[index]
        rect = pygame.Rect(
            int(x * CELL_SIZE),
            int(y * CELL_SIZE + BOARD_TOP),
            CELL_SIZE,
            CELL_SIZE,
        ).inflate(-3, -3)
        color = DARK_GREEN if index == 0 else GREEN
        if state == STATE_GAME_OVER:
            flash = (math.sin(now_ms / 80) + 1) / 2
            color = (
                int(lerp(color[0], RED[0], flash * 0.55)),
                int(lerp(color[1], RED[1], flash * 0.55)),
                int(lerp(color[2], RED[2], flash * 0.55)),
            )

        shadow_rect = rect.move(0, 2)
        pygame.draw.rect(screen, SHADOW, shadow_rect, border_radius=7)
        pygame.draw.rect(screen, color, rect, border_radius=7)
        pygame.draw.rect(screen, LIGHT_GREEN, rect.inflate(-9, -9), border_radius=5)

        if index == 0:
            draw_snake_head(screen, rect, direction)


def draw_snake_head(screen, rect, direction):
    """给蛇头加眼睛和朝向感。"""
    dx, dy = direction
    if dx == 0 and dy == 0:
        dx = 1
    perpendicular = (-dy, dx)
    face_offset = 5
    eye_gap = 4
    eye_radius = 2.2
    pupil_radius = 1.1
    center_x, center_y = rect.center

    for side in (-1, 1):
        eye_x = center_x + dx * face_offset + perpendicular[0] * eye_gap * side
        eye_y = center_y + dy * face_offset + perpendicular[1] * eye_gap * side
        pygame.draw.circle(screen, WHITE, (int(eye_x), int(eye_y)), int(eye_radius))
        pygame.draw.circle(
            screen,
            BLACK,
            (int(eye_x + dx * 0.8), int(eye_y + dy * 0.8)),
            int(pupil_radius),
        )


def draw_particles(screen, particles):
    """绘制吃食物时的短暂粒子。"""
    for particle in particles:
        life_progress = particle["age"] / particle["life"]
        alpha = int(220 * (1 - life_progress))
        radius = max(1, particle["radius"] * (1 - life_progress * 0.45))
        size = int(radius * 2 + 4)
        particle_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(
            particle_surface,
            (*YELLOW, alpha),
            (size // 2, size // 2),
            int(radius),
        )
        screen.blit(
            particle_surface,
            (int(particle["x"] - size / 2), int(particle["y"] - size / 2)),
        )


def draw_game(
    screen,
    font,
    big_font,
    snake,
    previous_snake,
    food,
    score,
    state,
    leaderboard,
    direction,
    move_progress,
    particles,
    now_ms,
):
    """绘制完整游戏画面。"""
    screen.fill(BLACK)
    draw_grid(screen)

    # 绘制顶部计分栏
    pygame.draw.rect(screen, GRAY, (0, 0, WINDOW_WIDTH, 48))
    score_text = font.render(f"得分：{score}", True, WHITE)
    screen.blit(score_text, (16, 10))

    hint_text = font.render("空格/P 暂停  Esc 退出", True, WHITE)
    hint_rect = hint_text.get_rect(midright=(WINDOW_WIDTH - 16, 24))
    screen.blit(hint_text, hint_rect)

    draw_food(screen, food, now_ms)
    snake_points = interpolated_snake(previous_snake, snake, move_progress)
    draw_snake(screen, snake_points, direction, state, now_ms)
    draw_particles(screen, particles)

    if state in (STATE_START, STATE_PAUSED, STATE_GAME_OVER):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        screen.blit(overlay, (0, 0))

    if state == STATE_START:
        draw_text(screen, big_font, "贪吃蛇", YELLOW, (WINDOW_WIDTH // 2, 118))
        draw_text(screen, font, "按空格开始游戏", WHITE, (WINDOW_WIDTH // 2, 180))
        draw_text(screen, font, "方向键/WASD 控制移动", WHITE, (WINDOW_WIDTH // 2, 218))
        draw_leaderboard(screen, font, leaderboard, WINDOW_WIDTH // 2 - 72, 260)
    elif state == STATE_PAUSED:
        draw_text(screen, big_font, "游戏暂停", BLUE, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 34))
        draw_text(screen, font, "按空格或 P 继续", WHITE, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 18))
    elif state == STATE_GAME_OVER:
        draw_text(screen, big_font, "游戏结束", YELLOW, (WINDOW_WIDTH // 2, 118))
        draw_text(screen, font, f"本局得分：{score}", WHITE, (WINDOW_WIDTH // 2, 176))
        draw_text(screen, font, "按空格重新开始，按 Esc 退出", WHITE, (WINDOW_WIDTH // 2, 218))
        draw_leaderboard(screen, font, leaderboard, WINDOW_WIDTH // 2 - 72, 260)

    pygame.display.flip()


def main():
    """游戏入口。"""
    pygame.init()
    pygame.display.set_caption("贪吃蛇")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    font = load_font(24)
    big_font = load_font(48, bold=True)

    snake, direction, next_direction, food, score, game_over = reset_game()
    previous_snake = snake[:]
    leaderboard = load_leaderboard()
    state = STATE_START
    score_recorded = False
    last_move_ms = pygame.time.get_ticks()
    last_frame_ms = last_move_ms
    particles = []

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if state == STATE_START and event.key == pygame.K_SPACE:
                    snake, direction, next_direction, food, score, game_over = reset_game()
                    previous_snake = snake[:]
                    state = STATE_PLAYING
                    score_recorded = False
                    particles = []
                    last_move_ms = pygame.time.get_ticks()
                    continue

                if state == STATE_GAME_OVER and event.key == pygame.K_SPACE:
                    snake, direction, next_direction, food, score, game_over = reset_game()
                    previous_snake = snake[:]
                    state = STATE_PLAYING
                    score_recorded = False
                    particles = []
                    last_move_ms = pygame.time.get_ticks()
                    continue

                if state in (STATE_PLAYING, STATE_PAUSED) and event.key in (pygame.K_SPACE, pygame.K_p):
                    state = STATE_PAUSED if state == STATE_PLAYING else STATE_PLAYING
                    continue

                # 方向控制：禁止直接反向，避免蛇头撞到自己的第二节身体
                if state == STATE_PLAYING:
                    if event.key in (pygame.K_UP, pygame.K_w) and direction != (0, 1):
                        next_direction = (0, -1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s) and direction != (0, -1):
                        next_direction = (0, 1)
                    elif event.key in (pygame.K_LEFT, pygame.K_a) and direction != (1, 0):
                        next_direction = (-1, 0)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d) and direction != (-1, 0):
                        next_direction = (1, 0)

        now_ms = pygame.time.get_ticks()
        elapsed_ms = now_ms - last_frame_ms
        last_frame_ms = now_ms
        particles = update_particles(particles, elapsed_ms)

        if state == STATE_PLAYING and now_ms - last_move_ms >= MOVE_INTERVAL_MS:
            previous_snake = snake[:]
            direction = next_direction
            head_x, head_y = snake[0]
            new_head = (head_x + direction[0], head_y + direction[1])

            # 碰到边界或自己身体就结束游戏
            hit_wall = (
                new_head[0] < 0
                or new_head[0] >= GRID_WIDTH
                or new_head[1] < 0
                or new_head[1] >= GRID_HEIGHT
            )
            hit_self = new_head in snake

            if hit_wall or hit_self:
                game_over = True
                state = STATE_GAME_OVER
                if not score_recorded:
                    leaderboard = record_score(score, leaderboard)
                    score_recorded = True
            else:
                snake.insert(0, new_head)

                # 吃到食物时加分并生成新食物，否则移动时去掉尾巴
                if new_head == food:
                    score += 1
                    particles.extend(spawn_eat_effects(food, direction))
                    food = random_food(snake)
                else:
                    snake.pop()

            last_move_ms = now_ms

        if state == STATE_PLAYING:
            move_progress = min(1, (now_ms - last_move_ms) / MOVE_INTERVAL_MS)
        else:
            move_progress = 1

        draw_game(
            screen,
            font,
            big_font,
            snake,
            previous_snake,
            food,
            score,
            state,
            leaderboard,
            direction,
            move_progress,
            particles,
            now_ms,
        )
        clock.tick(FPS)


if __name__ == "__main__":
    main()

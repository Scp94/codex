import json
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
FPS = 12
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


def load_font(size):
    """加载支持中文的字体，找不到时使用 Pygame 默认字体。"""
    font_names = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]
    for name in font_names:
        font_path = pygame.font.match_font(name)
        if font_path:
            return pygame.font.Font(font_path, size)
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


def draw_game(screen, font, big_font, snake, food, score, state, leaderboard):
    """绘制完整游戏画面。"""
    screen.fill(BLACK)

    # 绘制顶部计分栏
    pygame.draw.rect(screen, GRAY, (0, 0, WINDOW_WIDTH, 48))
    score_text = font.render(f"得分：{score}", True, WHITE)
    screen.blit(score_text, (16, 10))

    hint_text = font.render("空格/P 暂停  Esc 退出", True, WHITE)
    hint_rect = hint_text.get_rect(midright=(WINDOW_WIDTH - 16, 24))
    screen.blit(hint_text, hint_rect)

    # 绘制食物
    food_rect = pygame.Rect(
        food[0] * CELL_SIZE,
        food[1] * CELL_SIZE + 48,
        CELL_SIZE,
        CELL_SIZE,
    )
    pygame.draw.ellipse(screen, RED, food_rect.inflate(-4, -4))

    # 绘制蛇，蛇头颜色略深
    for index, (x, y) in enumerate(snake):
        rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE + 48, CELL_SIZE, CELL_SIZE)
        color = DARK_GREEN if index == 0 else GREEN
        pygame.draw.rect(screen, color, rect.inflate(-2, -2), border_radius=5)

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
    big_font = load_font(48)

    snake, direction, next_direction, food, score, game_over = reset_game()
    leaderboard = load_leaderboard()
    state = STATE_START
    score_recorded = False

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
                    state = STATE_PLAYING
                    score_recorded = False
                    continue

                if state == STATE_GAME_OVER and event.key == pygame.K_SPACE:
                    snake, direction, next_direction, food, score, game_over = reset_game()
                    state = STATE_PLAYING
                    score_recorded = False
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

        if state == STATE_PLAYING:
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
                    food = random_food(snake)
                else:
                    snake.pop()

        draw_game(screen, font, big_font, snake, food, score, state, leaderboard)
        clock.tick(FPS)


if __name__ == "__main__":
    main()

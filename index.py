import random
import sys

import pygame


# 游戏窗口和网格设置
CELL_SIZE = 24
GRID_WIDTH = 25
GRID_HEIGHT = 20
WINDOW_WIDTH = CELL_SIZE * GRID_WIDTH
WINDOW_HEIGHT = CELL_SIZE * GRID_HEIGHT + 48
FPS = 12

# 常用颜色
WHITE = (245, 245, 245)
BLACK = (20, 20, 20)
GREEN = (52, 168, 83)
DARK_GREEN = (32, 120, 57)
RED = (234, 67, 53)
GRAY = (70, 70, 70)
YELLOW = (251, 188, 5)


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


def draw_game(screen, font, big_font, snake, food, score, game_over):
    """绘制完整游戏画面。"""
    screen.fill(BLACK)

    # 绘制顶部计分栏
    pygame.draw.rect(screen, GRAY, (0, 0, WINDOW_WIDTH, 48))
    score_text = font.render(f"得分：{score}", True, WHITE)
    screen.blit(score_text, (16, 10))

    hint_text = font.render("方向键/WASD 移动  Esc 退出", True, WHITE)
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

    # 游戏结束提示
    if game_over:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        screen.blit(overlay, (0, 0))
        draw_text(screen, big_font, "游戏结束", YELLOW, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 32))
        draw_text(screen, font, "按空格重新开始，按 Esc 退出", WHITE, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 18))

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

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if game_over and event.key == pygame.K_SPACE:
                    snake, direction, next_direction, food, score, game_over = reset_game()
                    continue

                # 方向控制：禁止直接反向，避免蛇头撞到自己的第二节身体
                if not game_over:
                    if event.key in (pygame.K_UP, pygame.K_w) and direction != (0, 1):
                        next_direction = (0, -1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s) and direction != (0, -1):
                        next_direction = (0, 1)
                    elif event.key in (pygame.K_LEFT, pygame.K_a) and direction != (1, 0):
                        next_direction = (-1, 0)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d) and direction != (-1, 0):
                        next_direction = (1, 0)

        if not game_over:
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
            else:
                snake.insert(0, new_head)

                # 吃到食物时加分并生成新食物，否则移动时去掉尾巴
                if new_head == food:
                    score += 1
                    food = random_food(snake)
                else:
                    snake.pop()

        draw_game(screen, font, big_font, snake, food, score, game_over)
        clock.tick(FPS)


if __name__ == "__main__":
    main()

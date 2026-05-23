#!/usr/bin/env python3
"""俄罗斯方块 (Tetris) - Pygame 窗口版"""

import sys
import random
import pygame

# ── 常量 ──────────────────────────────────────────────
COLS = 10
ROWS = 20
CELL_SIZE = 32
BOARD_X = 40
BOARD_Y = 60
PANEL_X = BOARD_X + COLS * CELL_SIZE + 30
PANEL_Y = BOARD_Y

WINDOW_WIDTH = PANEL_X + 180
WINDOW_HEIGHT = BOARD_Y + ROWS * CELL_SIZE + 40

FPS = 60

# 颜色
BG_COLOR = (15, 18, 32)
BOARD_BG = (22, 33, 62)
GRID_LINE = (30, 45, 80)
BORDER_COLOR = (60, 80, 140)
PANEL_TEXT = (200, 200, 220)
TITLE_COLOR = (255, 80, 80)
WHITE = (240, 240, 240)
BLACK = (10, 10, 20)
OVERLAY = (0, 0, 0, 180)

PIECE_COLORS = {
    'I': (0, 229, 229),
    'O': (229, 229, 0),
    'T': (155, 0, 229),
    'S': (0, 229, 0),
    'Z': (229, 0, 0),
    'J': (0, 0, 229),
    'L': (229, 145, 0),
}
GHOST_COLOR = (60, 60, 100)

SCORE_TABLE = {1: 100, 2: 300, 3: 500, 4: 800}
LEVEL_SPEEDS = [800, 720, 630, 550, 470, 380, 300, 220, 150, 100,
                80, 70, 60, 50, 40, 30, 20, 15, 10, 8, 5]

# 方块形状
SHAPES = {
    'I': [[(0,1),(1,1),(2,1),(3,1)], [(2,0),(2,1),(2,2),(2,3)],
          [(0,2),(1,2),(2,2),(3,2)], [(1,0),(1,1),(1,2),(1,3)]],
    'O': [[(0,0),(0,1),(1,0),(1,1)]] * 4,
    'T': [[(0,1),(1,0),(1,1),(1,2)], [(0,1),(1,1),(1,2),(2,1)],
          [(1,0),(1,1),(1,2),(2,1)], [(0,1),(1,0),(1,1),(2,1)]],
    'S': [[(0,1),(0,2),(1,0),(1,1)], [(0,0),(1,0),(1,1),(2,1)],
          [(1,1),(1,2),(2,0),(2,1)], [(0,0),(1,0),(1,1),(2,1)]],
    'Z': [[(0,0),(0,1),(1,1),(1,2)], [(0,1),(1,0),(1,1),(2,0)],
          [(1,0),(1,1),(2,1),(2,2)], [(0,2),(1,1),(1,2),(2,1)]],
    'J': [[(0,0),(1,0),(1,1),(1,2)], [(0,1),(0,2),(1,1),(2,1)],
          [(1,0),(1,1),(1,2),(2,2)], [(0,1),(1,1),(2,0),(2,1)]],
    'L': [[(0,2),(1,0),(1,1),(1,2)], [(0,1),(1,1),(2,1),(2,2)],
          [(1,0),(1,1),(1,2),(2,0)], [(0,0),(0,1),(1,1),(2,1)]],
}
PIECE_KEYS = list(SHAPES.keys())

# SRS 踢墙数据 (Wall Kick)
# 格式: KICKS[旋转前][旋转后] = [(dc, dr), ...]
# I 方块有独立踢墙表
# SRS 踢墙数据 (dc, dr): dr>0=向下 (已从 SRS dy 取反)
KICKS_I = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)],
    (1, 0): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)],
    (2, 1): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)],
    (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)],
    (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)],
}

# 其他方块通用踢墙表 (JLSTZ)
KICKS = {
    (0, 1): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (1, 0): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (1, 2): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (2, 1): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (2, 3): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (3, 2): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (3, 0): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (0, 3): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
}


# 游戏状态
STATE_START = "start"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_OVER = "game_over"


def load_font(size, bold=False):
    """加载中文字体，优先使用系统自带中文字体"""
    # 按优先级尝试：直接路径 > match_font > SysFont
    font_paths = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for path in font_paths:
        try:
            font = pygame.font.Font(path, size)
            font.set_bold(bold)
            return font
        except Exception:
            continue

    font_names = [
        "STHeiti Medium", "STHeiti", "PingFang SC",
        "Heiti SC", "Microsoft YaHei", "SimHei",
        "Noto Sans CJK SC", "Arial Unicode MS",
    ]
    for name in font_names:
        path = pygame.font.match_font(name)
        if path:
            font = pygame.font.Font(path, size)
            font.set_bold(bold)
            return font

    for name in font_names:
        try:
            font = pygame.font.SysFont(name, size, bold=bold)
            return font
        except Exception:
            continue

    return pygame.font.Font(None, size)


class Tetris:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.score = 0
        self.lines = 0
        self.level = 0
        self.game_over = False
        self.bag = []
        self._fill_bag()
        self.cur = self._spawn()
        self.nxt = self._spawn()
        self.lock_delay_active = False
        self.lock_delay_start = 0
        self.lock_move_count = 0

    def _fill_bag(self):
        self.bag = PIECE_KEYS[:]
        random.shuffle(self.bag)

    def _next_name(self):
        if not self.bag:
            self._fill_bag()
        return self.bag.pop()

    def _spawn(self):
        name = self._next_name()
        shape = SHAPES[name][0]
        cs = [c for _, c in shape]
        col = (COLS - max(cs) - min(cs)) // 2
        return {'name': name, 'rot': 0, 'r': -1, 'c': col}

    def _cells(self, name, rot, r, c):
        return [(r + dr, c + dc) for dr, dc in SHAPES[name][rot]]

    def _valid(self, name, rot, r, c):
        for rr, cc in self._cells(name, rot, r, c):
            if not (0 <= cc < COLS):
                return False
            if rr >= ROWS:
                return False
            if rr >= 0 and self.board[rr][cc] is not None:
                return False
        return True

    def _lock(self):
        p = self.cur
        for rr, cc in self._cells(p['name'], p['rot'], p['r'], p['c']):
            if rr >= 0:
                self.board[rr][cc] = p['name']
        self._clear_lines()
        self.cur = self.nxt
        self.nxt = self._spawn()
        self.lock_delay_active = False
        if not self._valid(self.cur['name'], self.cur['rot'], self.cur['r'], self.cur['c']):
            self.game_over = True

    def _clear_lines(self):
        full = [r for r in range(ROWS) if all(self.board[r][c] is not None for c in range(COLS))]
        for r in full:
            del self.board[r]
            self.board.insert(0, [None] * COLS)
        n = len(full)
        if n:
            self.lines += n
            self.score += SCORE_TABLE.get(n, 0) * (self.level + 1)
            self.level = min(self.lines // 10, len(LEVEL_SPEEDS) - 1)

    def ghost_r(self):
        p = self.cur
        r = p['r']
        while self._valid(p['name'], p['rot'], r + 1, p['c']):
            r += 1
        return r

    def move(self, dr, dc, now_ms=0):
        if self._valid(self.cur['name'], self.cur['rot'],
                       self.cur['r'] + dr, self.cur['c'] + dc):
            self.cur['r'] += dr
            self.cur['c'] += dc
            self.on_piece_move(now_ms)
            return True
        return False

    def rotate(self, now_ms=0):
        old_rot = self.cur['rot']
        new_rot = (old_rot + 1) % 4
        name = self.cur['name']
        # 选择踢墙表：I 方块用独立表
        kick_table = KICKS_I if name == 'I' else KICKS
        kicks = kick_table.get((old_rot, new_rot), [(0, 0)])
        for dc, dr in kicks:
            nr, nc = self.cur['r'] + dr, self.cur['c'] + dc
            if self._valid(name, new_rot, nr, nc):
                self.cur['rot'] = new_rot
                self.cur['r'] = nr
                self.cur['c'] = nc
                # 旋转后重力下落：若锁定延迟中则落到底
                if self.lock_delay_active:
                    while self._valid(self.cur['name'], self.cur['rot'],
                                      self.cur['r'] + 1, self.cur['c']):
                        self.cur['r'] += 1
                self.on_piece_move(now_ms)
                return True
        return False

    def drop(self):
        self.cur['r'] = self.ghost_r()
        self._lock()

    def tick(self):
        if self._valid(self.cur['name'], self.cur['rot'],
                       self.cur['r'] + 1, self.cur['c']):
            self.cur['r'] += 1
            self.lock_delay_active = False
            return True
        else:
            return False

    def try_lock(self, now_ms):
        """检查是否应该锁定：若未启动延迟则启动，若超时则锁定"""
        if not self.lock_delay_active:
            self.lock_delay_active = True
            self.lock_delay_start = now_ms
            self.lock_move_count = 0
            return False
        # 延迟 500ms，移动/旋转最多重置 15 次
        if now_ms - self.lock_delay_start >= 500:
            self._lock()
            return True
        return False

    def on_piece_move(self, now_ms):
        """移动或旋转时调用，重置锁定延迟（有上限）"""
        if self.lock_delay_active and self.lock_move_count < 15:
            self.lock_delay_start = now_ms
            self.lock_move_count += 1


def draw_block(surface, x, y, color, alpha=255):
    """绘制一个带立体效果的方块"""
    rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
    # 主体
    s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), (0, 0, CELL_SIZE, CELL_SIZE), border_radius=3)
    # 高光（左上）
    highlight = tuple(min(c + 60, 255) for c in color)
    pygame.draw.rect(s, (*highlight, alpha), (2, 2, CELL_SIZE - 4, 4), border_radius=2)
    pygame.draw.rect(s, (*highlight, alpha), (2, 2, 4, CELL_SIZE - 4), border_radius=2)
    # 阴影（右下）
    shadow = tuple(max(c - 60, 0) for c in color)
    pygame.draw.rect(s, (*shadow, alpha), (2, CELL_SIZE - 6, CELL_SIZE - 4, 4), border_radius=2)
    pygame.draw.rect(s, (*shadow, alpha), (CELL_SIZE - 6, 2, 4, CELL_SIZE - 4), border_radius=2)
    surface.blit(s, (x, y))


def draw_board(screen, game):
    # 棋盘背景
    board_rect = pygame.Rect(BOARD_X - 2, BOARD_Y - 2,
                              COLS * CELL_SIZE + 4, ROWS * CELL_SIZE + 4)
    pygame.draw.rect(screen, BORDER_COLOR, board_rect, border_radius=4)
    inner = pygame.Rect(BOARD_X, BOARD_Y, COLS * CELL_SIZE, ROWS * CELL_SIZE)
    pygame.draw.rect(screen, BOARD_BG, inner)

    # 网格线
    for r in range(ROWS + 1):
        y = BOARD_Y + r * CELL_SIZE
        pygame.draw.line(screen, GRID_LINE, (BOARD_X, y),
                         (BOARD_X + COLS * CELL_SIZE, y))
    for c in range(COLS + 1):
        x = BOARD_X + c * CELL_SIZE
        pygame.draw.line(screen, GRID_LINE, (x, BOARD_Y),
                         (x, BOARD_Y + ROWS * CELL_SIZE))

    # 已锁定的方块
    for r in range(ROWS):
        for c in range(COLS):
            name = game.board[r][c]
            if name:
                draw_block(screen, BOARD_X + c * CELL_SIZE,
                           BOARD_Y + r * CELL_SIZE, PIECE_COLORS[name])

    if game.game_over:
        return

    # 幽灵方块
    p = game.cur
    ghost_r = game.ghost_r()
    if ghost_r != p['r']:
        for rr, cc in game._cells(p['name'], p['rot'], ghost_r, p['c']):
            if rr >= 0:
                draw_block(screen, BOARD_X + cc * CELL_SIZE,
                           BOARD_Y + rr * CELL_SIZE, GHOST_COLOR, alpha=100)

    # 当前活动方块
    for rr, cc in game._cells(p['name'], p['rot'], p['r'], p['c']):
        if rr >= 0:
            draw_block(screen, BOARD_X + cc * CELL_SIZE,
                       BOARD_Y + rr * CELL_SIZE, PIECE_COLORS[p['name']])


def draw_panel(screen, font, game):
    x = PANEL_X
    y = PANEL_Y

    texts = [
        (f"分数", 28, TITLE_COLOR),
        (f"{game.score}", 46, WHITE),
        ("", 20, WHITE),
        (f"行数", 28, TITLE_COLOR),
        (f"{game.lines}", 46, WHITE),
        ("", 20, WHITE),
        (f"等级", 28, TITLE_COLOR),
        (f"{game.level}", 46, WHITE),
    ]
    for txt, size, color in texts:
        if not txt:
            y += 10
            continue
        f = load_font(size, bold=(size > 30))
        img = f.render(txt, True, color)
        screen.blit(img, (x, y))
        y += size + 6

    # 下一块预览
    y += 15
    f = load_font(24)
    img = f.render("下一个", True, TITLE_COLOR)
    screen.blit(img, (x, y))
    y += 34

    preview_size = 4 * 28
    preview_x = x + 10
    preview_y = y
    pygame.draw.rect(screen, BOARD_BG,
                     (preview_x - 2, preview_y - 2, preview_size + 4, preview_size + 4),
                     border_radius=4)

    shape = SHAPES[game.nxt['name']][0]
    rs = [r for r, _ in shape]
    cs = [c for _, c in shape]
    min_r, max_r = min(rs), max(rs)
    min_c, max_c = min(cs), max(cs)
    cells_r = max_r - min_r + 1
    cells_c = max_c - min_c + 1
    off_r = (4 - cells_r) // 2 - min_r
    off_c = (4 - cells_c) // 2 - min_c

    for dr, dc in shape:
        pr, pc = dr + off_r, dc + off_c
        draw_block(screen, preview_x + pc * 28, preview_y + pr * 28,
                   PIECE_COLORS[game.nxt['name']], alpha=200)


def draw_overlay(screen, font, big_font, state, game=None):
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((10, 10, 25, 190))
    screen.blit(overlay, (0, 0))

    cx = WINDOW_WIDTH // 2
    if state == STATE_START:
        draw_text_center(screen, big_font, "俄罗斯方块", TITLE_COLOR, (cx, 140))
        draw_text_center(screen, font, "按 空格 或 Enter 开始", WHITE, (cx, 220))
        draw_text_center(screen, font, "← → 移动  ↑ 旋转  ↓ 软降", PANEL_TEXT, (cx, 270))
        draw_text_center(screen, font, "空格 硬降  P 暂停  Esc 退出", PANEL_TEXT, (cx, 310))
    elif state == STATE_PAUSED:
        draw_text_center(screen, big_font, "暂停", (100, 180, 255), (cx, 200))
        draw_text_center(screen, font, "按 P 或 空格 继续", WHITE, (cx, 270))
    elif state == STATE_OVER:
        draw_text_center(screen, big_font, "游戏结束", TITLE_COLOR, (cx, 130))
        f = load_font(30)
        img = f.render(f"得分: {game.score if game else 0}", True, WHITE)
        screen.blit(img, img.get_rect(center=(cx, 200)))
        draw_text_center(screen, font, "按 空格 或 R 重新开始", WHITE, (cx, 260))
        draw_text_center(screen, font, "按 Esc 退出", PANEL_TEXT, (cx, 300))


def draw_text_center(surface, font, text, color, center):
    img = font.render(text, True, color)
    surface.blit(img, img.get_rect(center=center))


def main():
    pygame.init()
    pygame.display.set_caption("俄罗斯方块 - Tetris")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    font = load_font(22)
    big_font = load_font(52)

    game = Tetris()
    state = STATE_START

    last_tick = pygame.time.get_ticks()
    # DAS (Delayed Auto Shift) 左右移动
    das_delay = 170
    das_repeat = 50
    das_timer = {'left': 0, 'right': 0, 'down': 0}
    das_active = {'left': False, 'right': False, 'down': False}

    running = True
    while running:
        dt = clock.tick(FPS)
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if state == STATE_START:
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        game.reset()
                        state = STATE_PLAYING
                        last_tick = now
                    continue

                if state == STATE_OVER:
                    if event.key in (pygame.K_SPACE, pygame.K_r):
                        game.reset()
                        state = STATE_PLAYING
                        last_tick = now
                    continue

                if event.key in (pygame.K_p, pygame.K_SPACE):
                    if state == STATE_PLAYING:
                        if event.key == pygame.K_p:
                            state = STATE_PAUSED
                        elif event.key == pygame.K_SPACE:
                            game.drop()
                            last_tick = now
                    elif state == STATE_PAUSED:
                        state = STATE_PLAYING
                        last_tick = now

                if state != STATE_PLAYING:
                    continue

                if event.key == pygame.K_LEFT:
                    game.move(0, -1, now)
                    das_active['left'] = True
                    das_timer['left'] = now + das_delay
                elif event.key == pygame.K_RIGHT:
                    game.move(0, 1, now)
                    das_active['right'] = True
                    das_timer['right'] = now + das_delay
                elif event.key == pygame.K_DOWN:
                    if game.move(1, 0, now):
                        last_tick = now
                    das_active['down'] = True
                    das_timer['down'] = now + das_delay
                elif event.key == pygame.K_UP:
                    game.rotate(now)

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    das_active['left'] = False
                elif event.key == pygame.K_RIGHT:
                    das_active['right'] = False
                elif event.key == pygame.K_DOWN:
                    das_active['down'] = False

        # DAS 自动重复移动
        if state == STATE_PLAYING:
            for key in ('left', 'right', 'down'):
                if das_active[key] and now >= das_timer[key]:
                    if key == 'left':
                        game.move(0, -1, now)
                    elif key == 'right':
                        game.move(0, 1, now)
                    elif key == 'down':
                        if game.move(1, 0, now):
                            last_tick = now
                    das_timer[key] = now + das_repeat

        # 定时下落
        if state == STATE_PLAYING:
            speed = LEVEL_SPEEDS[min(game.level, len(LEVEL_SPEEDS) - 1)]
            if now - last_tick >= speed:
                moved = game.tick()
                if not moved:
                    game.try_lock(now)
                last_tick = now
                if game.game_over:
                    state = STATE_OVER
            elif game.lock_delay_active:
                # 即使不到下落时间，也要检查锁定延迟是否到期
                game.try_lock(now)
                if game.game_over:
                    state = STATE_OVER

        # 渲染
        screen.fill(BG_COLOR)
        draw_board(screen, game)
        draw_panel(screen, font, game)

        # 控制提示
        hint_font = load_font(20)
        hint = hint_font.render("← → ↑ ↓ 移动/旋转  Space 硬降  P 暂停  Esc 退出", True, PANEL_TEXT)
        screen.blit(hint, (BOARD_X, WINDOW_HEIGHT - 30))

        if state != STATE_PLAYING:
            draw_overlay(screen, font, big_font, state, game)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()

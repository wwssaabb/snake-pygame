"""贪吃蛇 · pygame 版

状态机：菜单 / 排行榜 / 游戏（含暂停）/ 昵称录入 / 结算
运行：run.vbs（无控制台）或 run.bat / .venv\\Scripts\\python.exe main.py
"""

from __future__ import annotations

import math
import os
import sys
import traceback
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")   # pythonw 下不往 stdout 打印


def _fail(message: str) -> None:
    """没有控制台时把错误写日志并弹系统框，避免"点了没反应"。"""
    try:
        (_ROOT / "error.log").write_text(message, encoding="utf-8")
    except OSError:
        pass
    if sys.stderr is not None:
        sys.stderr.write(message)
    else:
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message[-1200:], "贪吃蛇 - 启动失败", 0x10)
        except Exception:  # noqa: BLE001
            pass


def _ensure_pygame() -> None:
    """任意 Python 3.12 都能直接跑；不在 3.12 上给出明确指引。"""
    try:
        import pygame  # noqa: F401

        return
    except ModuleNotFoundError:
        pass
    site = _ROOT / ".venv" / "Lib" / "site-packages"
    if site.is_dir():
        sys.path.insert(0, str(site))
        try:
            import pygame  # noqa: F401

            return
        except ImportError as exc:
            _fail(
                f"无法加载 pygame：{exc}\n\n"
                f"当前 Python {sys.version.split()[0]}，pygame 是按 Python 3.12 安装的。\n"
                "请用 run.vbs 或 .venv\\Scripts\\python.exe 运行；\n"
                "或给当前解释器安装：python -m pip install pygame"
            )
            raise SystemExit(1) from exc
    _fail("未找到 pygame。请先安装：python -m pip install pygame")
    raise SystemExit(1)


_ensure_pygame()


def _install_excepthook() -> None:
    def hook(tp, val, tb) -> None:  # noqa: ANN001
        text = "".join(traceback.format_exception(tp, val, tb))
        try:
            (_ROOT / "error.log").write_text(text, encoding="utf-8")
        except OSError:
            pass
        if sys.stderr is not None:
            sys.stderr.write(text)
        else:
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(0, text[-1200:], "贪吃蛇 - 运行出错", 0x10)
            except Exception:  # noqa: BLE001
                pass

    sys.excepthook = hook


_install_excepthook()

import pygame  # noqa: E402

from game import Direction, Game  # noqa: E402
from leaderboard import Leaderboard  # noqa: E402
from settings import (  # noqa: E402
    ACCENT,
    BOARD_BG,
    BOARD_RECT,
    CARD,
    CELL,
    COLS,
    DANGER,
    FPS,
    FOOTER_RECT,
    FRAME,
    GHOST,
    GOLD,
    GRAD_BOTTOM,
    GRAD_TOP,
    HEIGHT,
    HIGHLIGHT,
    HUD_RECT,
    INNER_EDGE,
    LINE,
    MARGIN,
    Mode,
    PANEL_EDGE,
    ROWS,
    SHADOW,
    SNAKE_HEAD,
    SNAKE_TAIL,
    SUB,
    TEXT,
    WIDTH,
    FOOD,
    FOOD_GLOW,
    load_font,
)
from ui import (  # noqa: E402
    Button,
    badge,
    divider,
    draw_cell,
    draw_grid_dots,
    draw_text,
    gradient_surface,
    lerp_color,
    make_glow,
    medal,
    pill,
    pulse,
    round_panel,
    shadow_text,
    dim,
)

MENU, BOARD, PLAY, ENTRY, OVER = "menu", "board", "play", "entry", "over"

KEYMAP = {
    pygame.K_UP: Direction.UP,
    pygame.K_w: Direction.UP,
    pygame.K_DOWN: Direction.DOWN,
    pygame.K_s: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT,
    pygame.K_a: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT,
    pygame.K_d: Direction.RIGHT,
}

# 排行榜列（相对面板左边，全部左对齐；每列带最大宽度以防溢出）
COL_RANK = 24
COL_NAME = 96
COL_MODE = 240
COL_SCORE = 356
COL_TIME = 430
ROW_STEP = 34
HEADER_H = 46

NAME_W = 132
MODE_W = 104
SCORE_W = 62


def ring_path(cols: int, rows: int) -> list[tuple[int, int]]:
    """绕矩形一圈的路径，用作菜单背景里游动的装饰蛇。"""
    cells: list[tuple[int, int]] = [(x, 0) for x in range(cols)]
    cells += [(cols - 1, y) for y in range(1, rows)]
    cells += [(x, rows - 1) for x in range(cols - 2, -1, -1)]
    cells += [(0, y) for y in range(rows - 2, 0, -1)]
    return cells


def short_time(date: str) -> str:
    """把 'YYYY-MM-DD HH:MM' 收成 'MM-DD HH:MM'，并兼容异常数据。"""
    raw = (date or "").strip()
    if len(raw) >= 16 and raw[4] == "-" and raw[7] == "-":
        return raw[5:16]
    return raw


class App:
    def __init__(self, board_path: str | Path | None = None) -> None:
        pygame.init()
        pygame.display.set_caption("贪吃蛇  Snake")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.now = 0

        self.bg = gradient_surface(WIDTH, HEIGHT, GRAD_TOP, GRAD_BOTTOM)
        self.food_glow = make_glow(12, FOOD_GLOW)
        # 背景漂浮光晕
        self.bg_glows = [
            (make_glow(80, (58, 158, 148), layers=10), 130, 110, 0.00060),
            (make_glow(95, (112, 92, 205), layers=10), 500, 380, 0.00043),
        ]
        # 装饰蛇只沿棋盘边框游动，棋盘下方是独立的底部提示区（不会遮挡）
        self.deco_ring = ring_path(COLS, ROWS)

        base = Path(__file__).resolve().parent
        self.leaderboard = Leaderboard(Path(board_path) if board_path else base / "leaderboard.json")

        self.mode = Mode.CLASSIC
        self.state = MENU
        self.menu_index = 0
        self.paused = False
        self.game: Game | None = None
        self.name_buf = "PLAYER"
        self.new_index: int | None = None
        self.best_before = 0
        self.new_record = False

        self.particles: list[dict] = []
        self.floaters: list[dict] = []

        self.f_title = load_font(62, bold=True)
        self.f_sub = load_font(20)
        self.f_menu = load_font(26, bold=True)
        self.f_hud = load_font(26, bold=True)
        self.f_hud_s = load_font(18, bold=True)
        self.f_badge = load_font(17, bold=True)
        self.f_tiny = load_font(15)
        self.f_panel = load_font(38, bold=True)
        self.f_body = load_font(23)
        self.f_small = load_font(19)
        self.f_rank = load_font(14, bold=True)

        self.menu_buttons = [
            Button("开始游戏", tag="start"),
            Button(f"模式 · {self.mode.label}", tag="mode"),
            Button("排行榜", tag="board"),
            Button("退出", tag="quit"),
        ]
        for i, button in enumerate(self.menu_buttons):
            button.rect.center = (WIDTH // 2, 268 + i * 60)

    # ================================================== 输入
    def handle(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.KEYDOWN:
            self._on_key(event)
        elif event.type == pygame.MOUSEMOTION:
            self._hover(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._click(event.pos)

    def _hover(self, pos: tuple[int, int]) -> None:
        if self.state == MENU:
            for button in self.menu_buttons:
                button.hovered = button.hit(pos)

    def _click(self, pos: tuple[int, int]) -> None:
        if self.state == MENU:
            for index, button in enumerate(self.menu_buttons):
                if button.hit(pos):
                    self.menu_index = index
                    self._activate(button.tag)
                    return
        elif self.state == BOARD:
            self.state = MENU
        elif self.state == OVER:
            self._restart()

    def _activate(self, tag: str) -> None:
        if tag == "start":
            self._restart()
        elif tag == "mode":
            self.mode = Mode.WRAP if self.mode is Mode.CLASSIC else Mode.CLASSIC
            self.menu_buttons[1].label = f"模式 · {self.mode.label}"
        elif tag == "board":
            self.new_index = None
            self.state = BOARD
        elif tag == "quit":
            self.running = False

    def _on_key(self, event: pygame.event.Event) -> None:
        key = event.key

        if self.state == MENU:
            if key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % len(self.menu_buttons)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % len(self.menu_buttons)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._activate(self.menu_buttons[self.menu_index].tag)
            elif key == pygame.K_l:
                self.new_index = None
                self.state = BOARD
            elif key == pygame.K_ESCAPE:
                self.running = False
            return

        if self.state == BOARD:
            if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_l):
                self.state = MENU
            return

        if self.state == ENTRY:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._submit_name()
            elif key == pygame.K_ESCAPE:
                self.state = OVER                      # 跳过记录
            elif key == pygame.K_BACKSPACE:
                self.name_buf = self.name_buf[:-1]
            else:
                char = getattr(event, "unicode", "")
                if char and char.isprintable() and len(self.name_buf) < 8 and not char.isspace():
                    self.name_buf += char
            return

        if self.state == OVER:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r):
                self._restart()
            elif key == pygame.K_l:
                self.new_index = None
                self.state = BOARD
            elif key == pygame.K_ESCAPE:
                self.state = MENU
            return

        # ---- PLAY ----
        if self.paused:
            if key in (pygame.K_p, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self.paused = False
            elif key == pygame.K_q:
                self.state = MENU
            elif key == pygame.K_r:
                self._restart()
            return

        if key in KEYMAP:
            if self.game:
                self.game.turn(KEYMAP[key])
        elif key in (pygame.K_p, pygame.K_ESCAPE):
            self.paused = True
        elif key == pygame.K_r:
            self._restart()

    # ================================================== 状态切换
    def _restart(self) -> None:
        self.best_before = self.leaderboard.best       # 本局开始前的历史最高
        self.new_record = False
        self.game = Game(self.mode, COLS, ROWS)
        self.particles.clear()
        self.floaters.clear()
        self.new_index = None
        self.paused = False
        self.state = PLAY

    def _submit_name(self) -> None:
        assert self.game is not None
        self.new_index = self.leaderboard.add(self.name_buf, self.game.score, self.mode)
        self.state = BOARD

    def _on_end(self) -> None:
        assert self.game is not None
        # 新纪录 = 破了本局开始前的历史最高（与"能进前十"无关）
        self.new_record = self.game.score > 0 and self.game.score > self.best_before
        if self.leaderboard.qualifies(self.game.score):
            self.name_buf = "PLAYER"
            self.state = ENTRY
        else:
            self.state = OVER

    # ================================================== 更新
    def update(self, dt: float) -> None:
        if self.state == PLAY and self.game is not None and not self.paused:
            for event in self.game.update(dt):
                kind = event[0]
                if kind == "eat":
                    self._burst(event[1])
                    self.floaters.append({
                        "x": BOARD_RECT.left + event[1][0] * CELL + CELL // 2,
                        "y": BOARD_RECT.top + event[1][1] * CELL,
                        "life": 900.0,
                        "text": "+1",
                    })
                elif kind in ("dead", "win"):
                    self._on_end()

        for particle in self.particles:
            particle["life"] -= dt
            particle["x"] += particle["vx"] * dt / 16.0
            particle["y"] += particle["vy"] * dt / 16.0
            particle["vy"] += 0.045 * dt / 16.0
        self.particles = [p for p in self.particles if p["life"] > 0]

        for floater in self.floaters:
            floater["life"] -= dt
            floater["y"] -= 0.03 * dt
        self.floaters = [f for f in self.floaters if f["life"] > 0]

    def _burst(self, cell: tuple[int, int]) -> None:
        cx = BOARD_RECT.left + cell[0] * CELL + CELL // 2
        cy = BOARD_RECT.top + cell[1] * CELL + CELL // 2
        for index in range(14):
            angle = index / 14 * math.tau
            speed = 1.6 + (index % 3) * 0.5
            self.particles.append({
                "x": cx, "y": cy,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": 520.0,
                "color": lerp_color(FOOD, GOLD, (index % 4) / 4),
            })

    # ================================================== 绘制
    def draw(self) -> None:
        self._draw_background()
        if self.state == MENU:
            self._draw_menu()
        elif self.state == BOARD:
            self._draw_board_screen()
        elif self.state == ENTRY:
            self._draw_play()
            self._draw_entry()
        elif self.state == OVER:
            self._draw_play()
            self._draw_over()
        else:
            self._draw_play()
        self._draw_effects()
        pygame.display.flip()

    def _draw_background(self) -> None:
        self.screen.blit(self.bg, (0, 0))
        for surface, cx, cy, speed in self.bg_glows:
            x = cx + math.sin(self.now * speed) * 55
            y = cy + math.cos(self.now * speed * 0.87) * 42
            scaled = pygame.transform.scale_by(surface, 1.0 + 0.10 * math.sin(self.now * speed * 3))
            scaled.set_alpha(60)
            self.screen.blit(scaled, scaled.get_rect(center=(x, y)))

    def _draw_footer(self, text: str, accent: bool = False) -> None:
        """底部独立提示区：与棋盘分离，任何蛇/装饰都不会压到它。"""
        rect = FOOTER_RECT
        pill(self.screen, rect, (22, 27, 47), LINE)
        color = ACCENT if accent else SUB
        draw_text(self.screen, self.f_tiny, text, color, rect.center, center=True)

    # ---------- 菜单 ----------
    def _draw_menu(self) -> None:
        screen = self.screen
        self._draw_deco_snake()

        glow_scale = pulse(self.now, 0.003, 0.18)
        glow = pygame.transform.scale_by(self.food_glow, glow_scale * 3.2)
        glow.set_alpha(140)
        screen.blit(glow, glow.get_rect(center=(WIDTH // 2, 92)))

        shadow_text(screen, self.f_title, "贪吃蛇", TEXT, (WIDTH // 2, 92))
        draw_text(screen, self.f_sub, "S N A K E   ·   P Y G A M E", ACCENT,
                  (WIDTH // 2, 140), center=True)
        pygame.draw.rect(screen, ACCENT, pygame.Rect(WIDTH // 2 - 60, 160, 120, 3), border_radius=2)

        # 徽章行：模式 + 历史最佳（按实际宽度并排，避免长模式名互相挤压）
        best = self.leaderboard.best
        mode_text = f"{self.mode.label} · {self.mode.hint}"
        best_text = f"历史最佳 {best}"
        mode_w = self.f_badge.size(mode_text)[0] + 30
        best_w = self.f_badge.size(best_text)[0] + 30
        gap = 16
        total = mode_w + gap + best_w
        left = WIDTH // 2 - total // 2
        badge(screen, self.f_badge, mode_text,
              (left + mode_w // 2, 194))
        badge(screen, self.f_badge, best_text,
              (left + mode_w + gap + best_w // 2, 194),
              fg=GOLD, bg=(38, 33, 24), edge=(98, 80, 40))

        for index, button in enumerate(self.menu_buttons):
            button.selected = index == self.menu_index
            if index == 1:
                button.label = f"模式 · {self.mode.label}"
            button.draw(screen, self.f_menu)

        self._draw_footer("↑ ↓ 选择      Enter 确认      L 排行榜      鼠标可点击")

    def _draw_deco_snake(self) -> None:
        """沿棋盘边框游动的装饰蛇。"""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        head_index = int(self.now * 0.012) % len(self.deco_ring)
        length = 18
        for i in range(length):
            x, y = self.deco_ring[(head_index - i) % len(self.deco_ring)]
            alpha = int(78 * (1 - i / length))
            color = lerp_color(SNAKE_HEAD, SNAKE_TAIL, i / length)
            rect = pygame.Rect(BOARD_RECT.left + x * CELL, BOARD_RECT.top + y * CELL, CELL, CELL)
            pygame.draw.rect(overlay, (*color, alpha), rect.inflate(-7, -7), border_radius=10)
        self.screen.blit(overlay, (0, 0))

    # ---------- 排行榜 ----------
    def _draw_board_screen(self) -> None:
        screen = self.screen
        entries = self.leaderboard.entries
        count = len(entries)

        draw_text(screen, self.f_panel, "排行榜 TOP 10", GOLD, (WIDTH // 2, 46), center=True)
        draw_text(screen, self.f_tiny, "按分数从高到低 · 同分按提交时间靠前", SUB,
                  (WIDTH // 2, 74), center=True)

        panel_top = 94
        rows_h = max(count, 1) * ROW_STEP
        panel_h = HEADER_H + rows_h + 22
        panel = pygame.Rect(MARGIN, panel_top, WIDTH - MARGIN * 2, panel_h)
        round_panel(screen, panel, radius=18)

        # 表头：随面板顶部圆角
        header = pygame.Rect(panel.left, panel.top, panel.width, HEADER_H)
        pygame.draw.rect(screen, CARD, header, border_radius=18)
        pygame.draw.rect(screen, CARD, (header.left, header.bottom - 18, header.width, 18))
        header_y = panel.top + HEADER_H // 2
        for x, label, width in (
            (COL_RANK, "排名", 52),
            (COL_NAME, "昵称", NAME_W),
            (COL_MODE, "模式", MODE_W),
            (COL_SCORE, "分数", SCORE_W),
            (COL_TIME, "时间", None),
        ):
            draw_cell(screen, self.f_tiny, label, SUB, panel.left + x, header_y, max_width=width)
        divider(screen, panel.left + 14, panel.right - 14, header.bottom, PANEL_EDGE)

        if not entries:
            draw_text(screen, self.f_body, "暂无记录 · 先玩一局吧", SUB,
                      (panel.centerx, panel.top + HEADER_H + rows_h // 2), center=True)
        else:
            row_y0 = panel.top + HEADER_H + ROW_STEP // 2 + 4
            # 第一遍：行底（隔行 + 本局高亮），避免遮住文字
            for index in range(count):
                y = row_y0 + index * ROW_STEP
                stripe = pygame.Rect(panel.left + 10, y - ROW_STEP // 2 + 2,
                                     panel.width - 20, ROW_STEP - 4)
                if index == self.new_index:
                    flash = 0.5 + 0.5 * math.sin(self.now * 0.008)
                    pygame.draw.rect(screen, lerp_color(CARD, HIGHLIGHT, flash),
                                     stripe, border_radius=9)
                elif index % 2 == 0:
                    pygame.draw.rect(screen, (31, 36, 58), stripe, border_radius=9)

            # 第二遍：文字（全部左对齐 + 垂直居中，列宽截断防溢出）
            time_w = panel.right - (panel.left + COL_TIME) - 16
            for index, entry in enumerate(entries):
                y = row_y0 + index * ROW_STEP
                highlight = index == self.new_index
                medal(screen, self.f_rank, panel.left + COL_RANK + 11, y, index + 1)
                draw_cell(screen, self.f_small, entry["name"], TEXT,
                          panel.left + COL_NAME, y, max_width=NAME_W)
                draw_cell(screen, self.f_tiny, self.leaderboard.label_of(entry["mode"]),
                          ACCENT, panel.left + COL_MODE, y, max_width=MODE_W)
                draw_cell(screen, self.f_hud_s, str(entry["score"]),
                          GOLD if highlight else TEXT, panel.left + COL_SCORE, y,
                          max_width=SCORE_W)
                draw_cell(screen, self.f_tiny, short_time(entry["date"]), SUB,
                          panel.left + COL_TIME, y, max_width=time_w)

        hint_y = min(panel.bottom + 26, HEIGHT - 26)
        draw_text(screen, self.f_tiny, "Esc / Enter / 鼠标点击 返回菜单", GHOST,
                  (WIDTH // 2, hint_y), center=True)

    # ---------- 游戏 ----------
    def _draw_play(self) -> None:
        screen = self.screen
        game = self.game
        if game is None:
            return

        # HUD：四个信息格 + 分隔线
        round_panel(screen, HUD_RECT, radius=14)
        best = max(self.leaderboard.best, game.score)
        cells = [
            ("分数", str(game.score), self.f_hud, TEXT, 42),
            ("模式", game.mode.label, self.f_hud_s, ACCENT, 182),
            ("速度", str(game.speed_level), self.f_hud_s, TEXT, 322),
            ("最佳", str(best), self.f_hud_s, GOLD, 462),
        ]
        for label, value, value_font, color, x in cells:
            draw_cell(screen, self.f_tiny, label, SUB, x, HUD_RECT.top + 18, max_width=120)
            draw_cell(screen, value_font, value, color, x, HUD_RECT.top + 41, max_width=130)
        for dx in (164, 304, 444):
            pygame.draw.line(screen, LINE, (dx, HUD_RECT.top + 12), (dx, HUD_RECT.bottom - 12))

        # 棋盘：外框 + 内板
        outer = BOARD_RECT.inflate(6, 6)
        pygame.draw.rect(screen, SHADOW, outer.move(0, 4), border_radius=19)
        pygame.draw.rect(screen, FRAME, outer, border_radius=19)
        pygame.draw.rect(screen, INNER_EDGE, outer, width=1, border_radius=19)
        pygame.draw.rect(screen, BOARD_BG, BOARD_RECT, border_radius=16)
        draw_grid_dots(screen, BOARD_RECT, CELL)

        # 食物：辉光 + 旋转点缀 + 核心
        if game.food is not None:
            fx, fy = game.food
            cx = BOARD_RECT.left + fx * CELL + CELL // 2
            cy = BOARD_RECT.top + fy * CELL + CELL // 2
            glow = pygame.transform.scale_by(self.food_glow, pulse(self.now, 0.006, 0.18))
            glow.set_alpha(190)
            screen.blit(glow, glow.get_rect(center=(cx, cy)))
            for k in range(6):
                angle = self.now * 0.004 + k * math.tau / 6
                pygame.draw.circle(screen, (255, 176, 186),
                                   (round(cx + math.cos(angle) * 15),
                                    round(cy + math.sin(angle) * 15)), 2)
            pygame.draw.circle(screen, FOOD, (cx, cy), 9)
            pygame.draw.circle(screen, (255, 196, 204), (cx - 3, cy - 3), 3)

        # 蛇：轮廓 + 渐变填充 + 头部高光
        segments = game.snake.segments(game.progress)
        rects = [
            pygame.Rect(BOARD_RECT.left + fx * CELL, BOARD_RECT.top + fy * CELL, CELL, CELL)
            for fx, fy in segments
        ]
        # 外发光（只对头部到前几节）
        if rects:
            halo = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for rect in rects[:3]:
                pygame.draw.rect(halo, (*SNAKE_HEAD, 26), rect.inflate(10, 10), border_radius=16)
            screen.blit(halo, (0, 0))
        for rect in rects:
            pygame.draw.rect(screen, (8, 10, 18), rect.inflate(2, 2), border_radius=14)
        count = len(rects)
        for index, rect in enumerate(rects):
            color = lerp_color(SNAKE_HEAD, SNAKE_TAIL, index / max(1, count - 1))
            pygame.draw.rect(screen, color, rect.inflate(-1, -1), border_radius=12)
            pygame.draw.rect(screen, lerp_color(color, (255, 255, 255), 0.30),
                             pygame.Rect(rect.left + 5, rect.top + 4, rect.width - 10, 4),
                             border_radius=2)

        if rects:
            head = rects[0]
            cx, cy = head.center
            dx, dy = game.snake.direction.dx, game.snake.direction.dy
            px, py = -dy, dx
            for sign in (1, -1):
                ex = cx + dx * 4 + px * 5 * sign
                ey = cy + dy * 4 + py * 5 * sign
                pygame.draw.circle(screen, (255, 255, 255), (ex, ey), 3)
                pygame.draw.circle(screen, (18, 22, 40), (round(ex + dx), round(ey + dy)), 1)

        self._draw_footer("方向键 / WASD 移动      P 暂停      R 重开      Esc 菜单")

        if self.paused:
            dim(screen, 150)
            panel = pygame.Rect(0, 0, 360, 190)
            panel.center = (BOARD_RECT.centerx, BOARD_RECT.centery)
            round_panel(screen, panel, radius=18)
            draw_text(screen, self.f_panel, "已暂停", TEXT, (panel.centerx, panel.top + 52), center=True)
            draw_text(screen, self.f_body, "P / Enter 继续", ACCENT,
                      (panel.centerx, panel.top + 104), center=True)
            draw_text(screen, self.f_tiny, "R 重开    Q 回主菜单    Esc 继续", SUB,
                      (panel.centerx, panel.top + 144), center=True)

    # ---------- 昵称录入 ----------
    def _draw_entry(self) -> None:
        screen = self.screen
        dim(screen, 170)
        assert self.game is not None

        panel = pygame.Rect(0, 0, 480, 330)
        panel.center = (WIDTH // 2, HEIGHT // 2)
        round_panel(screen, panel, radius=20)

        title = "新纪录！" if self.new_record else "上榜！"
        title_color = GOLD if self.new_record else ACCENT
        draw_text(screen, self.f_panel, title, title_color, (panel.centerx, panel.top + 52), center=True)

        draw_text(screen, self.f_body, f"本局得分 {self.game.score} · {self.mode.label}",
                  TEXT, (panel.centerx, panel.top + 104), center=True)

        ahead = sum(1 for e in self.leaderboard.entries if e["score"] > self.game.score) + 1
        if self.new_record:
            note = "刷新了历史最高分"
            note_color = GOLD
        else:
            note = f"榜上第 {ahead} 名 · 历史最高 {max(self.leaderboard.best, self.game.score)}"
            note_color = SUB
        draw_text(screen, self.f_tiny, note, note_color,
                  (panel.centerx, panel.top + 136), center=True)

        divider(screen, panel.left + 46, panel.right - 46, panel.top + 160)

        box = pygame.Rect(0, 0, 330, 54)
        box.center = (panel.centerx, panel.top + 200)
        pygame.draw.rect(screen, (20, 24, 44), box, border_radius=12)
        pygame.draw.rect(screen, ACCENT, box, width=2, border_radius=12)
        caret = "|" if int(self.now / 400) % 2 == 0 else " "
        draw_text(screen, self.f_body, self.name_buf + caret, TEXT,
                  (box.centerx, box.centery), center=True)

        draw_text(screen, self.f_tiny, "输入昵称（英文 / 数字，最多 8 位）", SUB,
                  (panel.centerx, box.bottom + 26), center=True)
        draw_text(screen, self.f_tiny, "回车记录      Esc 跳过", GHOST,
                  (panel.centerx, box.bottom + 52), center=True)

    # ---------- 结算 ----------
    def _draw_over(self) -> None:
        screen = self.screen
        dim(screen, 172)
        assert self.game is not None

        entries = self.leaderboard.entries[:5]
        list_h = 36 + max(1, len(entries)) * 30          # 小标题 + 行
        panel_h = 232 + list_h + 46                     # 内容 + 底部提示
        panel = pygame.Rect(0, 0, 480, panel_h)
        panel.center = (WIDTH // 2, HEIGHT // 2)
        round_panel(screen, panel, radius=20)

        title = "通关！" if self.game.won else "游戏结束"
        color = GOLD if self.game.won else DANGER
        draw_text(screen, self.f_panel, title, color, (panel.centerx, panel.top + 44), center=True)

        draw_text(screen, self.f_hud, f"得分 {self.game.score}",
                  GOLD if self.new_record else TEXT,
                  (panel.centerx, panel.top + 92), center=True)

        divider(screen, panel.left + 40, panel.right - 40, panel.top + 118)

        draw_text(screen, self.f_small, f"模式  {self.mode.label}",
                  SUB, (panel.centerx, panel.top + 142), center=True)
        draw_text(screen, self.f_small, f"历史最佳  {max(self.leaderboard.best, self.game.score)}",
                  GOLD if self.new_record else SUB,
                  (panel.centerx, panel.top + 170), center=True)

        if self.new_record:
            badge(screen, self.f_tiny, "★ 新的最高分 ★",
                  (panel.centerx, panel.top + 202), fg=GOLD,
                  bg=(40, 34, 22), edge=(104, 84, 40))

        # 结算页内嵌小排行榜（左对齐，列宽固定，空间单独预留）
        inner = pygame.Rect(panel.left + 28, panel.top + 224, panel.width - 56, list_h + 8)
        pygame.draw.rect(screen, (24, 29, 49), inner, border_radius=12)
        pygame.draw.rect(screen, LINE, inner, width=1, border_radius=12)
        draw_text(screen, self.f_tiny, "本机 TOP 5", SUB, (inner.left + 14, inner.top + 10))

        if entries:
            for index, entry in enumerate(entries):
                y = inner.top + 38 + index * 30
                draw_cell(screen, self.f_tiny, f"{index + 1}.", SUB, inner.left + 14, y)
                draw_cell(screen, self.f_small, entry["name"], TEXT,
                          inner.left + 44, y, max_width=160)
                draw_cell(screen, self.f_tiny, self.leaderboard.label_of(entry["mode"]),
                          ACCENT, inner.left + 218, y, max_width=96)
                draw_cell(screen, self.f_hud_s, str(entry["score"]), GOLD,
                          inner.right - 62, y, max_width=48)
        else:
            draw_text(screen, self.f_tiny, "还没有记录", SUB,
                      (inner.centerx, inner.top + 46), center=True)

        draw_text(screen, self.f_tiny, "R / Enter 再来一局    L 排行榜    Esc 主菜单",
                  GHOST, (panel.centerx, panel.bottom - 24), center=True)

    # ---------- 特效 ----------
    def _draw_effects(self) -> None:
        for particle in self.particles:
            alpha = max(0, min(255, int(255 * particle["life"] / 520)))
            radius = max(1, int(4 * particle["life"] / 520))
            surface = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*particle["color"], alpha), (radius + 1, radius + 1), radius)
            self.screen.blit(surface, (particle["x"] - radius - 1, particle["y"] - radius - 1))

        for floater in self.floaters:
            alpha = max(0, min(255, int(255 * floater["life"] / 900)))
            image = self.f_hud.render(floater["text"], True, GOLD)
            image.set_alpha(alpha)
            self.screen.blit(image, image.get_rect(center=(floater["x"], floater["y"])))

    # ================================================== 主循环
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS)
            self.now = pygame.time.get_ticks()
            for event in pygame.event.get():
                self.handle(event)
            self.update(dt)
            self.draw()
        pygame.quit()


def main() -> int:
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

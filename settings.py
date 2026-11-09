"""全局配置：尺寸、配色、字体、模式定义。"""

from __future__ import annotations

import enum
import os

import pygame

# ---------------- 网格与窗口 ----------------
CELL = 26
COLS = 22
ROWS = 18
BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL

MARGIN = 24
HUD_H = 62
GAP = 10
FOOTER_H = 34

WIDTH = BOARD_W + MARGIN * 2
HEIGHT = MARGIN * 2 + HUD_H + GAP + BOARD_H + GAP + FOOTER_H

HUD_RECT = pygame.Rect(MARGIN, MARGIN, BOARD_W, HUD_H)
BOARD_RECT = pygame.Rect(MARGIN, MARGIN + HUD_H + GAP, BOARD_W, BOARD_H)
FOOTER_RECT = pygame.Rect(MARGIN, BOARD_RECT.bottom + GAP, BOARD_W, FOOTER_H)

FPS = 60

# ---------------- 节奏 ----------------
BASE_STEP_MS = 150
MIN_STEP_MS = 70
STEP_DECREASE = 4          # 每吃一个食物提速多少毫秒

# ---------------- 配色（深色高级感）----------------
BG_TOP = (14, 17, 32)
BG_BOTTOM = (27, 31, 58)

# 背景渐变上下色（兼容旧引用）
GRAD_TOP = BG_TOP
GRAD_BOTTOM = BG_BOTTOM

PANEL = (29, 34, 60)
PANEL_EDGE = (68, 78, 124)
CARD = (35, 40, 70)
ROW_ALT = (31, 36, 60)
BOARD_BG = (10, 13, 24)
FRAME = (31, 37, 68)
INNER_EDGE = (47, 55, 94)
GRID_DOT = (32, 38, 64)
LINE = (48, 56, 96)

SNAKE_HEAD = (126, 240, 196)
SNAKE_TAIL = (86, 110, 222)

FOOD = (255, 105, 124)
FOOD_GLOW = (255, 150, 164)

TEXT = (235, 238, 248)
SUB = (152, 162, 196)
ACCENT = (94, 234, 212)
GOLD = (255, 206, 110)
DANGER = (255, 96, 112)
GHOST = (72, 82, 128)
SUCCESS = (120, 230, 180)

SHADOW = (8, 10, 20)
HIGHLIGHT = (74, 64, 32)


# ---------------- 模式 ----------------
class Mode(enum.Enum):
    """游戏模式：标准模式撞墙即死，穿越边界从另一侧钻出。"""

    CLASSIC = "classic"
    WRAP = "wrap"

    @property
    def label(self) -> str:
        return "标准模式" if self is Mode.CLASSIC else "穿越边界"

    @property
    def hint(self) -> str:
        return "撞墙即结束" if self is Mode.CLASSIC else "穿出边界从对面回来"


# ---------------- 中文字体 ----------------
_CJK_CANDIDATES = (
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\DengXian.ttf",
    r"C:\Windows\Fonts\msjhbd.ttc",
    r"C:\Windows\Fonts\NotoSansCJK-Regular.ttc",
)
_font_cache: dict[tuple[int, bool], pygame.font.Font] = {}


def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """优先用系统中文字体，取不到才退回 pygame 默认字体（不支持中文）。"""
    key = (size, bold)
    cached = _font_cache.get(key)
    if cached is not None:
        return cached

    path = None
    wanted = "msyhbd.ttc" if bold else "msyh.ttc"
    for candidate in _CJK_CANDIDATES:
        if os.path.isfile(candidate) and os.path.basename(candidate) == wanted:
            path = candidate
            break
    if path is None:
        for candidate in _CJK_CANDIDATES:
            if os.path.isfile(candidate):
                path = candidate
                break

    font = pygame.font.Font(path, size) if path else pygame.font.Font(None, size)
    if path is None:
        font.set_bold(bold)
    _font_cache[key] = font
    return font

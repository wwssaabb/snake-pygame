"""绘制工具：渐变背景、光晕、圆角面板、按钮、徽章、文字排版。"""

from __future__ import annotations

import math

import pygame

from settings import (
    ACCENT,
    LINE,
    PANEL,
    PANEL_EDGE,
    SHADOW,
    SUB,
    TEXT,
)


def lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


def gradient_surface(width: int, height: int, top, bottom) -> pygame.Surface:
    """垂直线性渐变，只在启动时生成一次。"""
    surface = pygame.Surface((width, height))
    for y in range(height):
        pygame.draw.line(surface, lerp_color(top, bottom, y / max(1, height - 1)), (0, y), (width, y))
    return surface


def make_glow(radius: int, color, layers: int = 7) -> pygame.Surface:
    """预渲染的径向辉光。"""
    size = (radius + layers * 3) * 2
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    for i in range(layers, 0, -1):
        alpha = int(8 + 24 * (1 - i / layers))
        pygame.draw.circle(surface, (*color, alpha), (center, center), radius + i * 3)
    return surface


def round_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    radius: int = 14,
    fill=PANEL,
    edge=PANEL_EDGE,
    shadow: bool = True,
    glow_line: bool = True,
) -> None:
    """带投影与顶部高光的圆角面板。"""
    if shadow:
        pygame.draw.rect(surface, SHADOW, rect.move(0, 4), border_radius=radius)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, edge, rect, width=1, border_radius=radius)
    if glow_line and rect.width > 40:
        top = lerp_color(fill, (255, 255, 255), 0.14)
        pygame.draw.line(surface, top, (rect.left + 14, rect.top + 1), (rect.right - 14, rect.top + 1))


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color,
    pos: tuple[int, int],
    center: bool = False,
    alpha: int | None = None,
) -> pygame.Rect:
    image = font.render(text, True, color)
    if alpha is not None:
        image = image.copy()
        image.set_alpha(alpha)
    rect = image.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(image, rect)
    return rect


def fit_text(font: pygame.font.Font, text: str, max_width: int | None) -> str:
    """超宽时截断并补省略号，避免文字越过列边界。"""
    if max_width is None or max_width <= 0 or font.size(text)[0] <= max_width:
        return text
    ellipsis = "…"
    if font.size(ellipsis)[0] > max_width:
        return ""
    trimmed = text
    while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
        trimmed = trimmed[:-1]
    return trimmed + ellipsis


def draw_cell(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color,
    x: int,
    y_center: int,
    max_width: int | None = None,
) -> pygame.Rect:
    """表格单元格：**左对齐 + 垂直居中**，保证各列同一基线。"""
    text = fit_text(font, text, max_width)
    image = font.render(text, True, color)
    rect = image.get_rect()
    rect.left = x
    rect.centery = y_center
    surface.blit(image, rect)
    return rect


def pill(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill,
    edge=None,
    radius: int | None = None,
) -> None:
    radius = radius if radius is not None else rect.height // 2
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if edge is not None:
        pygame.draw.rect(surface, edge, rect, width=1, border_radius=radius)


def badge(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    center: tuple[int, int],
    fg=ACCENT,
    bg=(24, 30, 52),
    edge=(52, 96, 108),
) -> pygame.Rect:
    """圆角徽章：文字 + 描边。"""
    image = font.render(text, True, fg)
    rect = image.get_rect(center=center)
    box = rect.inflate(30, 16)
    pill(surface, box, bg, edge)
    surface.blit(image, rect)
    return box


def medal(surface: pygame.Surface, font: pygame.font.Font, cx: int, cy: int, rank: int, radius: int = 12) -> None:
    """排名徽章：前三金银铜，其余深色。"""
    palette = {
        1: ((255, 206, 110), (46, 34, 6)),
        2: ((203, 213, 225), (38, 44, 56)),
        3: ((217, 158, 110), (52, 32, 18)),
    }
    fill, text_color = palette.get(rank, ((46, 52, 84), SUB))
    pygame.draw.circle(surface, fill, (cx, cy), radius)
    image = font.render(str(rank), True, text_color)
    surface.blit(image, image.get_rect(center=(cx, cy)))


class Button:
    """菜单按钮：鼠标悬停与键盘选中两种高亮，带投影与左侧强调条。"""

    def __init__(self, label: str, width: int = 360, height: int = 50, tag: str = "") -> None:
        self.label = label
        self.tag = tag or label
        self.rect = pygame.Rect(0, 0, width, height)
        self.hovered = False
        self.selected = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> pygame.Rect:
        rect = self.rect
        active = self.hovered or self.selected

        # 投影
        pygame.draw.rect(surface, SHADOW, rect.move(0, 5), border_radius=16)
        # 底色：选中更亮，并有轻微渐变层次
        fill = (52, 62, 104) if active else (30, 35, 60)
        pygame.draw.rect(surface, fill, rect, border_radius=16)
        pygame.draw.rect(
            surface, lerp_color(fill, (255, 255, 255), 0.10),
            pygame.Rect(rect.left + 2, rect.top + 2, rect.width - 4, rect.height // 2 - 2),
            border_radius=14,
        )
        pygame.draw.rect(
            surface,
            ACCENT if active else PANEL_EDGE,
            rect,
            width=2 if active else 1,
            border_radius=16,
        )
        if active:
            pygame.draw.rect(surface, ACCENT, (rect.left + 9, rect.top + 12, 4, rect.height - 24), border_radius=2)
            pygame.draw.polygon(
                surface, ACCENT,
                [(rect.right - 26, rect.centery - 6),
                 (rect.right - 20, rect.centery),
                 (rect.right - 26, rect.centery + 6)],
            )
        draw_text(surface, font, self.label, TEXT if active else SUB, rect.center, center=True)
        return rect

    def hit(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


def draw_grid_dots(surface: pygame.Surface, rect: pygame.Rect, cell: int) -> None:
    for x in range(rect.left, rect.right, cell):
        for y in range(rect.top, rect.bottom, cell):
            pygame.draw.circle(surface, (30, 36, 62), (x + cell // 2, y + cell // 2), 1)


def dim(surface: pygame.Surface, alpha: int = 150) -> None:
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((6, 8, 18, max(0, min(255, alpha))))
    surface.blit(overlay, (0, 0))


def shadow_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color,
    center: tuple[int, int],
    offset: tuple[int, int] = (0, 3),
    shadow_color=SHADOW,
) -> pygame.Rect:
    """带投影的标题文字。"""
    image = font.render(text, True, shadow_color)
    surface.blit(image, image.get_rect(center=(center[0] + offset[0], center[1] + offset[1])))
    return draw_text(surface, font, text, color, center, center=True)


def hint_pill(surface: pygame.Surface, font: pygame.font.Font, text: str, center: tuple[int, int]) -> pygame.Rect:
    """底部操作提示：放进胶囊底，避免被背景装饰干扰。"""
    image = font.render(text, True, SUB)
    rect = image.get_rect(center=center)
    bg = rect.inflate(36, 18)
    pill(surface, bg, (24, 29, 50), LINE)
    surface.blit(image, rect)
    return bg


def divider(surface: pygame.Surface, x1: int, x2: int, y: int, color=LINE) -> None:
    pygame.draw.line(surface, color, (x1, y), (x2, y))


def pulse(now_ms: float, speed: float = 0.004, amount: float = 0.12) -> float:
    return 1.0 + amount * math.sin(now_ms * speed)

"""游戏逻辑：蛇的移动、碰撞、两种模式、食物与计分。

渲染与事件循环在 main.py；本模块不依赖 pygame，可单独做单元测试。
"""

from __future__ import annotations

import enum
import random
from typing import Iterable

from settings import BASE_STEP_MS, MIN_STEP_MS, STEP_DECREASE, Mode


class Direction(enum.Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @property
    def opposite(self) -> "Direction":
        return _OPPOSITE[self]


_OPPOSITE = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}


class Snake:
    """蛇身用坐标列表表示，索引 0 是头；prev_body 供渲染插值。"""

    def __init__(self, cols: int, rows: int) -> None:
        self.cols = cols
        self.rows = rows
        y = rows // 2
        head_x = cols // 4
        length = 4
        self.body: list[tuple[int, int]] = [(head_x - i, y) for i in range(length)]
        self.prev_body: list[tuple[int, int]] = list(self.body)
        self.direction = Direction.RIGHT
        self._queue: list[Direction] = []

    @property
    def head(self) -> tuple[int, int]:
        return self.body[0]

    def turn(self, d: Direction) -> None:
        """只排队，不立即生效；禁止同帧掉头与刷键。"""
        if len(self._queue) >= 2:
            return
        last = self._queue[-1] if self._queue else self.direction
        if d is last or d is last.opposite:
            return
        self._queue.append(d)

    def commit(self) -> None:
        if self._queue:
            self.direction = self._queue.pop(0)

    def next_head(self, wrap: bool) -> tuple[int, int]:
        x, y = self.body[0]
        nx, ny = x + self.direction.dx, y + self.direction.dy
        if wrap:
            nx %= self.cols
            ny %= self.rows
        return nx, ny

    def move(self, new_head: tuple[int, int], grow: bool) -> None:
        self.prev_body = list(self.body)
        self.body.insert(0, new_head)
        if not grow:
            self.body.pop()

    def segments(self, progress: float) -> list[tuple[float, float]]:
        """返回每节的浮点渲染坐标（含跨界吸附，避免横穿整个屏幕）。"""
        out: list[tuple[float, float]] = []
        for index, (cx, cy) in enumerate(self.body):
            if index < len(self.prev_body):
                px, py = self.prev_body[index]
            else:
                px, py = self.prev_body[-1]
            if abs(px - cx) > 1 or abs(py - cy) > 1:   # 穿越边界：直接吸附
                px, py = cx, cy
            out.append((px + (cx - px) * progress, py + (cy - py) * progress))
        return out


class Game:
    """一局游戏的状态机。update() 返回本轮产生的事件供 UI 消费。"""

    def __init__(self, mode: Mode, cols: int, rows: int) -> None:
        self.mode = mode
        self.cols = cols
        self.rows = rows
        self.snake = Snake(cols, rows)
        self.food = self._spawn_food()
        self.score = 0
        self.over = False
        self.won = False
        self.acc = 0.0
        self.step_ms = float(BASE_STEP_MS)
        self.progress = 0.0

    # ---------------- 主循环 ----------------
    def update(self, dt_ms: float) -> list[tuple]:
        if self.over:
            self.progress = 1.0
            return []
        self.acc += dt_ms
        events: list[tuple] = []
        while self.acc >= self.step_ms:
            self.acc -= self.step_ms
            events += self._tick()
            if self.over:
                self.acc = 0.0
                break
        self.progress = min(1.0, self.acc / self.step_ms) if not self.over else 1.0
        return events

    def turn(self, d: Direction) -> None:
        if not self.over:
            self.snake.turn(d)

    # ---------------- 单步 ----------------
    def _tick(self) -> list[tuple]:
        self.snake.commit()
        wrap = self.mode is Mode.WRAP
        nxt = self.snake.next_head(wrap=wrap)

        # 撞自己：不吃食物时尾巴这帧会移走，所以排除尾节（追尾合法）
        will_grow = nxt == self.food
        body: Iterable[tuple[int, int]] = self.snake.body if will_grow else self.snake.body[:-1]
        if nxt in body:
            self.over = True
            return [("dead", "self")]

        # 撞墙（仅标准模式）
        if not wrap and not (0 <= nxt[0] < self.cols and 0 <= nxt[1] < self.rows):
            self.over = True
            return [("dead", "wall")]

        self.snake.move(nxt, will_grow)

        if not will_grow:
            return []

        self.score += 1
        self.step_ms = max(float(MIN_STEP_MS), self.step_ms - STEP_DECREASE)
        events = [("eat", self.food)]
        self.food = self._spawn_food()
        if self.food is None:            # 全占满 = 通关
            self.over = True
            self.won = True
            events.append(("win",))
        return events

    def _spawn_food(self) -> tuple[int, int] | None:
        occupied = set(self.snake.body)
        empty = [
            (x, y)
            for x in range(self.cols)
            for y in range(self.rows)
            if (x, y) not in occupied
        ]
        return random.choice(empty) if empty else None

    # ---------------- 辅助 ----------------
    @property
    def speed_level(self) -> int:
        from settings import BASE_STEP_MS as _base

        return max(1, round((_base - self.step_ms) / STEP_DECREASE) + 1)

"""无界面冒烟测试：SDL dummy 驱动下跑通全部状态与两种模式。

用法：python smoke_test.py
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import pygame  # noqa: E402

import main as M  # noqa: E402
from game import Direction, Game  # noqa: E402
from settings import COLS, Mode, ROWS  # noqa: E402


def fresh_board(tmpdir: pathlib.Path, entries: list[dict] | None = None) -> pathlib.Path:
    """每个用例独立的排行榜文件，避免受真实存档影响。"""
    tmpdir.mkdir(parents=True, exist_ok=True)
    path = tmpdir / "leaderboard.json"
    path.write_text(json.dumps({"entries": entries or []}), encoding="utf-8")
    return path


def key(k: int, unicode: str = "") -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode)


def tick_once(game: Game) -> None:
    game.update(game.step_ms)          # 恰好推进一帧


# ---------------- 纯逻辑：模式 ----------------
def test_wrap_mode() -> None:
    game = Game(Mode.WRAP, COLS, ROWS)
    game.snake.direction = Direction.LEFT
    game.snake.body = [(1, 5), (2, 5), (3, 5)]
    game.snake.prev_body = list(game.snake.body)
    game.food = (COLS - 2, ROWS - 2)

    tick_once(game)
    assert game.snake.body[0] == (0, 5), game.snake.body
    tick_once(game)                                   # 越过左边界 → 从右边回来
    assert game.snake.body[0] == (COLS - 1, 5), game.snake.body
    assert not game.over, "穿越模式不该因出界结束"


def test_classic_wall() -> None:
    game = Game(Mode.CLASSIC, COLS, ROWS)
    game.snake.direction = Direction.UP
    game.snake.body = [(5, 1), (5, 2), (5, 3), (5, 4)]
    game.snake.prev_body = list(game.snake.body)
    game.food = (COLS - 2, ROWS - 2)

    tick_once(game)
    assert game.snake.body[0] == (5, 0)
    tick_once(game)
    assert game.over and not game.won, "标准模式撞墙应结束"


def test_self_collision() -> None:
    game = Game(Mode.CLASSIC, COLS, ROWS)
    game.snake.body = [(5, 5), (5, 6), (6, 6), (6, 5)]
    game.snake.prev_body = list(game.snake.body)
    game.snake.direction = Direction.DOWN              # 向下会撞到 (5,6)
    game.food = (COLS - 2, ROWS - 2)
    tick_once(game)
    assert game.over, "撞到自己应结束"


def test_grow_and_food() -> None:
    game = Game(Mode.CLASSIC, COLS, ROWS)
    head = game.snake.head
    game.food = (head[0] + 1, head[1])               # 正前方就是食物
    before = len(game.snake.body)
    events = game.update(game.step_ms)
    assert "eat" in [e[0] for e in events], events
    assert len(game.snake.body) == before + 1, "吃到应长一节"
    assert game.score == 1
    assert game.food not in game.snake.body, "食物不能生成在蛇身上"


# ---------------- 界面状态机 ----------------
def test_app_states(board: pathlib.Path) -> None:
    app = M.App(board)
    assert app.state == M.MENU

    # 菜单导航
    app.handle(key(pygame.K_DOWN))
    assert app.menu_index == 1
    app.handle(key(pygame.K_UP))
    assert app.menu_index == 0

    # 模式切换
    app.menu_index = 1
    app.handle(key(pygame.K_RETURN))
    assert app.mode is Mode.WRAP and "穿越边界" in app.menu_buttons[1].label
    app.handle(key(pygame.K_RETURN))
    assert app.mode is Mode.CLASSIC and "标准模式" in app.menu_buttons[1].label

    # 进入排行榜（空）→ 返回
    app.menu_index = 2
    app.handle(key(pygame.K_RETURN))
    assert app.state == M.BOARD
    app.draw()
    app.handle(key(pygame.K_ESCAPE))
    assert app.state == M.MENU

    # 开始游戏
    app.menu_index = 0
    app.handle(key(pygame.K_RETURN))
    assert app.state == M.PLAY and app.game is not None

    # 转向 + 跑若干帧（含渲染）
    app.handle(key(pygame.K_UP))
    for _ in range(30):
        app.update(16)
        app.draw()
    assert app.game.snake.direction is Direction.UP

    # 暂停 / 继续
    app.handle(key(pygame.K_p))
    assert app.paused
    app.draw()
    app.handle(key(pygame.K_p))
    assert not app.paused

    # 制造新纪录 → 昵称录入 → 记录 → 排行榜
    app.game.score = 7
    app.game.over = True
    app._on_end()
    assert app.state == M.ENTRY, app.state
    app.draw()
    app.handle(key(pygame.K_BACKSPACE))
    app.name_buf = ""
    for char in "ACE":
        app.handle(key(ord(char), char))
    assert app.name_buf == "ACE"
    app.handle(key(pygame.K_RETURN))
    assert app.state == M.BOARD
    assert app.new_index == 0
    assert app.leaderboard.entries[0]["name"] == "ACE"
    assert app.leaderboard.entries[0]["score"] == 7
    app.draw()

    # 0 分不入榜 → 直接结算
    app.handle(key(pygame.K_ESCAPE))
    assert app.state == M.MENU
    app.menu_index = 0
    app.handle(key(pygame.K_RETURN))
    app.game.score = 0
    app.game.over = True
    app._on_end()
    assert app.state == M.OVER, app.state
    app.draw()
    app.handle(key(pygame.K_r))
    assert app.state == M.PLAY and app.game.score == 0

    # 鼠标点击菜单按钮
    app.state = M.MENU
    app.draw()
    button = app.menu_buttons[1]
    app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button.rect.center))
    assert app.mode is Mode.WRAP, "点击模式按钮应切换模式"

    pygame.quit()


def test_new_record_rule(board_dir: pathlib.Path) -> None:
    """新纪录只认「破历史最高」，不是「能进前十」。"""
    board = fresh_board(board_dir / "record", [
        {"name": f"P{i}", "score": 40 - i, "mode": "classic", "date": "2026-11-09 03:41"}
        for i in range(10)
    ])
    app = M.App(board)

    # 40 分：能进榜（榜上已有 40），但没破历史最高 → 不是新纪录
    app.menu_index = 0
    app.handle(key(pygame.K_RETURN))
    app.game.score = 40
    app.game.over = True
    app._on_end()
    assert app.new_record is False, "并列最高分不算新纪录"
    assert app.state == M.ENTRY, app.state

    # 41 分：破了历史最高 → 新纪录
    app.state = M.MENU
    app.menu_index = 0
    app.handle(key(pygame.K_RETURN))
    app.game.score = 41
    app.game.over = True
    app._on_end()
    assert app.new_record is True, "超过历史最高应为新纪录"

    # 低分且进不了榜 → 直接结算，也不误报新纪录
    app.state = M.MENU
    app.menu_index = 0
    app.handle(key(pygame.K_RETURN))
    app.game.score = 1
    app.game.over = True
    app._on_end()
    assert app.new_record is False
    assert app.state == M.OVER, app.state
    pygame.quit()


def main() -> int:
    test_wrap_mode()
    test_classic_wall()
    test_self_collision()
    test_grow_and_food()
    tmp = pathlib.Path(__file__).resolve().parent / ".test-tmp"
    test_app_states(fresh_board(tmp / "states"))
    test_new_record_rule(tmp / "record")
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

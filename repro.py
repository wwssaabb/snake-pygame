"""复现：菜单点击排行榜是否崩溃。"""

from __future__ import annotations

import os
import pathlib
import sys
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

import main as M  # noqa: E402


def pump(app: M.App, frames: int = 30) -> None:
    for _ in range(frames):
        app.update(16)
        app.draw()


def click(app: M.App, pos) -> None:
    app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def key(app: M.App, k: int, u: str = "") -> None:
    app.handle(pygame.event.Event(pygame.KEYDOWN, key=k, unicode=u))


def stage(name: str, fn) -> None:
    try:
        fn()
        print(f"OK   {name}")
    except Exception:  # noqa: BLE001
        print(f"FAIL {name}")
        traceback.print_exc()


app = M.App()

stage("点击排行榜按钮", lambda: (click(app, app.menu_buttons[2].rect.center),
                                 print("   state =", app.state)))
stage("排行榜画面渲染 30 帧", lambda: pump(app))
stage("点任意处返回菜单", lambda: (click(app, (5, 5)), print("   state =", app.state)))
stage("菜单渲染 30 帧", lambda: pump(app))
stage("再次点排行榜", lambda: (click(app, app.menu_buttons[2].rect.center),
                               pump(app), print("   state =", app.state)))
stage("键盘 L 打开排行榜", lambda: (key(app, pygame.K_ESCAPE), pump(app),
                                    key(app, pygame.K_l), pump(app),
                                    print("   state =", app.state)))
stage("空排行榜(删除数据)后打开", lambda: (
    setattr(app.leaderboard, "entries", []),
    key(app, pygame.K_ESCAPE), pump(app),
    key(app, pygame.K_l), pump(app),
    print("   state =", app.state)))
stage("返回菜单并渲染", lambda: (key(app, pygame.K_ESCAPE), pump(app)))
stage("开始游戏后回菜单再点排行榜", lambda: (
    setattr(app, "menu_index", 0), key(app, pygame.K_RETURN), pump(app),
    key(app, pygame.K_ESCAPE), pump(app),          # 暂停
    key(app, pygame.K_q), pump(app),               # 回主菜单
    print("   state =", app.state),
    click(app, app.menu_buttons[2].rect.center), pump(app),
    print("   state =", app.state)))

pygame.quit()
print("repro done")

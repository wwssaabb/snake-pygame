"""渲染各状态截图用于视觉检查（SDL dummy 驱动）。"""

from __future__ import annotations

import json
import os
import pathlib
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

import main as M  # noqa: E402


def key(k: int, unicode: str = "") -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode)


OUT = ROOT / "screenshots"
OUT.mkdir(exist_ok=True)
TMP = ROOT / ".shot-tmp"
TMP.mkdir(exist_ok=True)
BOARD = TMP / "leaderboard.json"
BOARD.write_text(json.dumps({"entries": []}), encoding="utf-8")


def shot(app: M.App, name: str) -> None:
    app.draw()
    pygame.image.save(app.screen, str(OUT / name))
    print("saved", name)


app = M.App(BOARD)
shot(app, "1-menu.png")

# 模式切换后的菜单
app.menu_index = 1
app.handle(key(pygame.K_RETURN))
app.menu_index = 0
shot(app, "2-menu-wrap.png")
app.menu_index = 1
app.handle(key(pygame.K_RETURN))          # 切回标准模式

# 游戏中
app.menu_index = 0
app.handle(key(pygame.K_RETURN))          # 开始
for _ in range(26):
    app.update(16)
app.game.score = 12
shot(app, "3-play.png")

# 暂停
app.handle(key(pygame.K_p))
shot(app, "4-pause.png")
app.handle(key(pygame.K_p))

# 排行榜（造几条数据，仅用于截图）
app.leaderboard.entries = [
    {"name": "ACE", "score": 42, "mode": "classic", "date": "2026-11-08 21:30"},
    {"name": "NOVA", "score": 36, "mode": "wrap", "date": "2026-11-08 22:14"},
    {"name": "PLAYER", "score": 28, "mode": "classic", "date": "2026-11-09 00:02"},
    {"name": "LIX", "score": 21, "mode": "wrap", "date": "2026-11-09 00:47"},
    {"name": "MOMO", "score": 17, "mode": "classic", "date": "2026-11-09 01:12"},
    {"name": "Q", "score": 9, "mode": "wrap", "date": "2026-11-09 02:33"},
]
app.new_index = 1
app.state = M.BOARD
shot(app, "5-leaderboard.png")

# 昵称录入
app.state = M.PLAY
app.game.score = 33
app.game.over = True
app.new_index = None
app._on_end()
app.name_buf = "ACE"
shot(app, "6-entry.png")

# 结算
app.state = M.OVER
app.game.score = 3
shot(app, "7-over.png")

pygame.quit()
print("done")

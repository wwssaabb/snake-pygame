"""历史高分排行榜：本地 JSON 持久化，只保留前十。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from settings import Mode

MAX_ENTRIES = 10


class Leaderboard:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.entries: list[dict] = []
        self.load()

    # ---------------- 持久化 ----------------
    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            items = raw.get("entries", []) if isinstance(raw, dict) else []
        except (OSError, ValueError):
            items = []
        self.entries = []
        for item in items:
            try:
                self.entries.append({
                    "name": str(item["name"])[:12],
                    "score": int(item["score"]),
                    "mode": item.get("mode", Mode.CLASSIC.value),
                    "date": str(item.get("date", "")),
                })
            except (KeyError, TypeError, ValueError):
                continue
        self.entries.sort(key=lambda e: -e["score"])
        self.entries = self.entries[:MAX_ENTRIES]

    def save(self) -> None:
        try:
            self.path.write_text(
                json.dumps({"entries": self.entries}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass                       # 只读环境下降级为本局内存排行

    # ---------------- 查询 ----------------
    @property
    def best(self) -> int:
        return max((e["score"] for e in self.entries), default=0)

    def qualifies(self, score: int) -> bool:
        """分数能否进前十（0 分不记录）。"""
        if score <= 0:
            return False
        return len(self.entries) < MAX_ENTRIES or score > self.entries[-1]["score"]

    def add(self, name: str, score: int, mode: Mode) -> int | None:
        """插入一条记录并保存，返回它所在下标；未上榜返回 None。"""
        if not self.qualifies(score):
            return None
        entry = {
            "name": (name.strip() or "玩家")[:12],
            "score": int(score),
            "mode": mode.value,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        # 分数降序；同分按时间靠前的在前
        index = len(self.entries)
        while index > 0 and self.entries[index - 1]["score"] < entry["score"]:
            index -= 1
        self.entries.insert(index, entry)
        del self.entries[MAX_ENTRIES:]
        self.save()
        return index

    def label_of(self, mode_value: str) -> str:
        try:
            return Mode(mode_value).label
        except ValueError:
            return "标准模式"

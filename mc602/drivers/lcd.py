"""
mc602.drivers.lcd — Lcd 驱动 (单例, 160x80 屏幕, 5 行字符)

用法:
    lcd = robot.lcd
    lcd.show_line(1, "hello")      # 第 1 行
    lcd.show_line(3, f"V={v:.1f}") # 任意行
    lcd.clear_line(2)              # 清第 2 行
    lcd.clear()                    # 全清
    lcd.auto()                     # 恢复心跳自动刷新
"""

from __future__ import annotations

from ..services.lcd import LCDService


class Lcd:
    """屏幕显示 (单例, 行 1~5, 每行 20 字符)。"""

    def __init__(self, bot):
        self._service = bot.lcd if bot is not None else None

    def show_line(self, line: int, text: str) -> None:
        """在指定行显示文本。首次调用后心跳刷新停止。"""
        self._service.show_line(line, text)

    def clear_line(self, line: int) -> None:
        """清指定行。"""
        self._service.clear_line(line)

    def clear(self) -> None:
        """清屏。"""
        self._service.clear()

    def auto(self) -> None:
        """恢复心跳自动刷新。"""
        self._service.auto()

    def __repr__(self) -> str:
        return "<Lcd 160x80 5行>"

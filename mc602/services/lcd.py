"""
mc602.services.lcd — LCD 服务底层 RPC 客户端 (SVC 0x60)

屏幕 160x80, 5 行字符显示 (1~5, show(0) 在屏外)。

上位机写屏后固件自动停用心跳刷新, 直到调用 auto() 恢复。
"""

from __future__ import annotations

from ..comm.packet import Op

LCD_LINE_MAX = 5
LCD_LINE_LEN = 20


class LCDService:
    """LCD 服务 (0x60) — 屏幕显示（底层 RPC 客户端）"""

    SVC = 0x60

    CALL_SHOW_LINE = 0x80   # [u8 line][str text]
    CALL_CLEAR = 0x81
    CALL_CLEAR_LINE = 0x82  # [u8 line]
    CALL_AUTO = 0x83        # 恢复心跳刷新

    def __init__(self, bot):
        self._bot = bot

    def show_line(self, line: int, text: str) -> None:
        """在指定行显示文本 (1~5, 每行最多 20 字符)。
        首次调用后心跳的屏幕刷新自动停止。"""
        if not (1 <= line <= LCD_LINE_MAX):
            raise ValueError(f"LCD 行号必须在 1~{LCD_LINE_MAX}, 收到 {line}")
        data = bytes([line]) + text.encode("utf-8", errors="replace")[:LCD_LINE_LEN]
        self._bot._request(
            Op.CALL, self.SVC, 0, self.CALL_SHOW_LINE,
            value=data, timeout=1.0, retry=2, retry_delay=0.1,
        )

    def clear(self) -> None:
        """清屏。心跳刷新停止。"""
        self._bot._request(Op.CALL, self.SVC, 0, self.CALL_CLEAR)

    def clear_line(self, line: int) -> None:
        """清指定行。"""
        if not (1 <= line <= LCD_LINE_MAX):
            raise ValueError(f"LCD 行号必须在 1~{LCD_LINE_MAX}, 收到 {line}")
        self._bot._request(
            Op.CALL, self.SVC, 0, self.CALL_CLEAR_LINE,
            value=bytes([line]), timeout=1.0, retry=2, retry_delay=0.1,
        )

    def auto(self) -> None:
        """恢复心跳自动刷新 (电压/心跳/堆内存)。"""
        self._bot._request(Op.CALL, self.SVC, 0, self.CALL_AUTO)

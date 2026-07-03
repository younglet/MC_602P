"""
mc602.services.btpad — BTPad RPC (SVC 0x03)

底层协议: 与 firmware/devices/services.c::btremote_handler 一一对应.
高层 OOP 封装在 mc602/drivers/btpad.py (BTPad).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..comm.packet import Op


@dataclass
class BTPadState:
    """蓝牙手柄状态快照 (原始值)"""
    stick1: int   # 左摇杆 Y (u16 原始)
    stick2: int   # 左摇杆 X
    stick3: int   # 右摇杆 Y
    stick4: int   # 右摇杆 X
    keys:   int   # 按键 bitmap (u16)
    connected: bool

    @classmethod
    def dead(cls) -> "BTPadState":
        return cls(0, 0, 0, 0, 0, False)


class BTPadService:
    """BTREMOTE 服务 (0x03) — 底层 RPC"""

    SVC = 0x03
    PROP_ALL  = 0x01
    PROP_NAME = 0x02

    def __init__(self, bot):
        self._bot = bot

    def get_state(self) -> BTPadState:
        r = self._bot._request(
            Op.GET, self.SVC, 0, self.PROP_ALL,
            timeout=0.5, retry=1, retry_delay=0.05,
        )
        if len(r.value) < 11:
            return BTPadState.dead()
        return BTPadState(
            stick1 = int.from_bytes(r.value[0:2],  "little"),
            stick2 = int.from_bytes(r.value[2:4],  "little"),
            stick3 = int.from_bytes(r.value[4:6],  "little"),
            stick4 = int.from_bytes(r.value[6:8],  "little"),
            keys    = int.from_bytes(r.value[8:10], "little"),
            connected = r.value[10] != 0,
        )

    def get_name(self) -> str:
        r = self._bot._request(
            Op.GET, self.SVC, 0, self.PROP_NAME,
            timeout=0.5, retry=0,
        )
        slen = r.value[0]
        return r.value[1:1 + slen].decode("ascii", errors="replace")

    @property
    def is_connected(self) -> bool:
        return self.get_state().connected

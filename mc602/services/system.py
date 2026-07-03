"""
mc602.services.system — System Service 底层 RPC 客户端

与下位机 device/devices/services.c::system_handler 一一对应。
"""

from __future__ import annotations

from ..comm.packet import Op


class SystemService:
    """SYSTEM 服务 (0xFE) — 控制器自身信息（底层 RPC 客户端）"""

    SVC = 0xFE

    # GET properties
    PROP_VOLTAGE     = 0x01   # u16 mV
    PROP_VERSION     = 0x02   # str
    PROP_UPTIME      = 0x03   # u32 s
    PROP_WATCHDOG_MS = 0x04   # u16 (rw)

    # CALL commands
    CALL_REBOOT     = 0x80
    CALL_BOOTLOADER = 0x81

    def __init__(self, bot):
        self._bot = bot

    @property
    def voltage_mv(self) -> int:
        r = self._bot._request(Op.GET, self.SVC, 0, self.PROP_VOLTAGE)
        return int.from_bytes(r.value, "little", signed=False)

    @property
    def voltage(self) -> float:
        return self.voltage_mv / 1000.0

    @property
    def version(self) -> str:
        r = self._bot._request(Op.GET, self.SVC, 0, self.PROP_VERSION)
        slen = r.value[0]
        return r.value[1:1 + slen].decode("ascii", errors="replace")

    @property
    def uptime(self) -> int:
        r = self._bot._request(Op.GET, self.SVC, 0, self.PROP_UPTIME)
        return int.from_bytes(r.value, "little", signed=False)

    @property
    def watchdog_ms(self) -> int:
        r = self._bot._request(Op.GET, self.SVC, 0, self.PROP_WATCHDOG_MS)
        return int.from_bytes(r.value, "little", signed=False)

    @watchdog_ms.setter
    def watchdog_ms(self, ms: int) -> None:
        ms = max(0, min(0xFFFF, int(ms)))
        self._bot._request(Op.SET, self.SVC, 0, self.PROP_WATCHDOG_MS,
                           value=ms.to_bytes(2, "little"))

    def reboot(self) -> None:
        self._bot._request(Op.CALL, self.SVC, 0, self.CALL_REBOOT)

    def bootloader(self) -> None:
        self._bot._request(Op.CALL, self.SVC, 0, self.CALL_BOOTLOADER)

"""
mc602.devices.system — System (singleton) 面向对象封装

用法:
    system = robot.system
    print(system.voltage, system.version, system.uptime)
    system.reboot()
"""

from __future__ import annotations

from ..services.system import SystemService


class System:
    """系统设备（单例）"""

    def __init__(self, bot):
        self._bot = bot
        self._service: SystemService = bot.system

    @property
    def voltage_mv(self) -> int:
        return self._service.voltage_mv

    @property
    def voltage(self) -> float:
        return self._service.voltage

    @property
    def version(self) -> str:
        return self._service.version

    @property
    def uptime(self) -> int:
        return self._service.uptime

    @property
    def watchdog_ms(self) -> int:
        return self._service.watchdog_ms

    @watchdog_ms.setter
    def watchdog_ms(self, ms: int) -> None:
        self._service.watchdog_ms = ms

    def reboot(self) -> None:
        self._service.reboot()

    def bootloader(self) -> None:
        self._service.bootloader()

    def __repr__(self) -> str:
        return f"<System {self.version} V={self.voltage:.2f}>"

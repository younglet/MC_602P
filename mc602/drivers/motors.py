"""
mc602.drivers.motors — Multi-motor driver

    m = Motors(bot, ports=(3, 1, 4, 2))   # int ports
    m = Motors(bot, ports=("M3", "M1", "M4", "M2"))  # str ports
    m.set_speeds(50, -50, -50, 50)
    e1, e2, e3, e4 = m.get_encoders()
"""

from __future__ import annotations
from ..services.motors import MotorsService


class Motors:
    """Generic multi-motor driver.

    Args:
        bot:   MC602 instance
        ports: port numbers or names, e.g. (1,2,3,4) or (M1,M2,M3,M4)
    """

    def __init__(self, bot, ports: tuple = (1, 2, 3, 4)):
        self._ports = tuple(ports)
        self._n = len(ports)
        self._svc = MotorsService(bot, ports)

    @property
    def ports(self) -> tuple:
        return self._ports

    def set_speeds(self, *speeds: int) -> None:
        """Set motor speeds (-100~+100). Order matches ports."""
        return self._svc.set_speeds(*speeds)

    def get_encoders(self) -> tuple:
        """Read encoders. Order matches ports."""
        return self._svc.get_encoders()

    def stop(self) -> None:
        """Stop all motors."""
        return self._svc.stop()

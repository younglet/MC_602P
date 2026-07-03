"""
mc602.drivers.motor_chassis — Generic multi-motor chassis

Wraps MotorChassisService with port mapping.
Supports any number of motors; port order is user-configurable.

    chassis = MotorChassis(bot, ports=(3,1,4,2))
    chassis.set_speeds(50, -50, -50, 50)
    e1, e2, e3, e4 = chassis.get_encoders()
"""

from __future__ import annotations
from ..services.motor_chassis import MotorChassisService


class MotorChassis:
    """Generic multi-motor chassis driver.

    Args:
        bot:   MC602 instance
        ports: motor port numbers in desired order
               e.g. (3,1,4,2) swaps front motors
    """

    def __init__(self, bot, ports: tuple = (1, 2, 3, 4)):
        self._ports = tuple(ports)
        self._n = len(ports)
        self._svc = MotorChassisService(bot, ports)

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

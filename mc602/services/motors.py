"""
mc602.services.motors — Multi-motor RPC.

When N=4, uses MecanumGroup (SVC 0x02, 1 frame).
Otherwise degrades to per-motor calls (SVC 0x01).
"""

from __future__ import annotations
from ..comm.packet import Op


def _port_int(port) -> int:
    """Convert port spec to int. Accepts int, "M1"-"M6", or "M" + int."""
    if isinstance(port, int):
        return port
    if isinstance(port, str):
        s = port.strip().upper()
        if s.startswith("M"):
            return int(s[1:])
        return int(s)
    raise TypeError(f"port must be int or str, got {type(port).__name__}")


class MotorsService:
    """Multi-motor RPC.

    Args:
        bot:   MC602 instance
        ports: motor port numbers or names, e.g. (1,2,3,4) or (M1,M2,M3,M4)
    """

    SVC_GROUP = 0x02

    def __init__(self, bot, ports: tuple):
        self._bot = bot
        self._ports = tuple(_port_int(p) for p in ports)
        self._n = len(self._ports)
        self._fast = (self._n == 4)  # SVC 0x02 supports 4 motors exactly

    def set_speeds(self, *speeds: int) -> None:
        """Set speeds for all motors (-100~+100). Order matches ports."""
        if len(speeds) != self._n:
            raise ValueError(f"expected {self._n} speeds, got {len(speeds)}")
        if self._fast:
            s = list(speeds)
            self._bot._request(
                Op.SET, self.SVC_GROUP, 0, 0x01,
                value=bytes([s[i] & 0xFF for i in range(4)]),
                timeout=1.0, retry=2, retry_delay=0.1,
            )
        else:
            for port, spd in zip(self._ports, speeds):
                self._bot.motor.set_speed(port, spd)

    def get_encoders(self) -> tuple:
        """Read encoders for all motors. Order matches ports."""
        if self._fast:
            r = self._bot._request(
                Op.GET, self.SVC_GROUP, 0, 0x02,
                timeout=0.5, retry=0,
            )
            return (
                int.from_bytes(r.value[0:4],  "little", signed=True),
                int.from_bytes(r.value[4:8],  "little", signed=True),
                int.from_bytes(r.value[8:12], "little", signed=True),
                int.from_bytes(r.value[12:16], "little", signed=True),
            )
        else:
            return tuple(
                self._bot.motor.get_encoder(p) for p in self._ports
            )

    def stop(self) -> None:
        """Stop all motors."""
        if self._fast:
            self._bot._request(
                Op.CALL, self.SVC_GROUP, 0, 0x80,
                timeout=1.0, retry=2, retry_delay=0.1,
            )
        else:
            for port in self._ports:
                try:
                    self._bot.motor.stop(port)
                except Exception:
                    pass

    stop_all = stop

    def get_statuses(self) -> tuple:
        """Read motor statuses (0=stopped, 1=running, 2=stalled)."""
        if self._fast:
            r = self._bot._request(
                Op.GET, self.SVC_GROUP, 0, 0x03,
                timeout=0.5, retry=0,
            )
            return tuple(r.value[i] for i in range(4))
        else:
            return tuple(
                self._bot.motor.get_status(p) for p in self._ports
            )

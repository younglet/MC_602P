"""
mc602.drivers.btpad — BTPad (OOP 封装)

高层 API, 在 BTPadService 之上加死区/校准/emoji 标签.
用法:
    bot.pad.calibrate()
    fwd, strafe, rot = bot.pad.get_deadzoned()
"""

from __future__ import annotations

from ..services.btpad import BTPadService, BTPadState


class BTPad:
    """蓝牙手柄 — OOP 封装.

    bot.pad.calibrate()           # 自动校准中心
    bot.pad.dz_threshold = 5      # 改死区
    fwd, strafe, rot = bot.pad.get_deadzoned()  # 归一化摇杆
    """

    KEY_MAP = {
        0:  "⬆️",
        1:  "⬅️",
        2:  "⬇️",
        3:  "➡️",
        4:  "🔼",
        5:  "▶️",
        6:  "🔽",
        7:  "◀️",
        8:  "🔵",
        9:  "🟦",
        10: "3️⃣",
        11: "4️⃣",
        14: "1️⃣",
        15: "2️⃣",
    }

    def __init__(self, bot):
        self._svc = BTPadService(bot)
        self.dz_center = (50, 50, 50, 50)
        self.dz_threshold = 5.0

    # ── 底层 RPC 透传 ────────────────────────────────────

    def get_state(self) -> BTPadState:
        return self._svc.get_state()

    def get_name(self) -> str:
        return self._svc.get_name()

    @property
    def is_connected(self) -> bool:
        return self._svc.is_connected

    # ── 高层 API ─────────────────────────────────────────

    def calibrate(self, n: int = 10) -> tuple:
        """自动校准摇杆中心. 请勿触碰摇杆."""
        import time
        samples = {0: [], 1: [], 2: [], 3: []}
        for _ in range(n):
            try:
                s = self.get_state()
            except Exception:
                time.sleep(0.05)
                continue
            for i, v in enumerate([s.stick1, s.stick2, s.stick3, s.stick4]):
                samples[i].append(v)
            time.sleep(0.05)
        centers = []
        for i in range(4):
            vals = sorted(samples[i])
            centers.append(vals[len(vals) // 2] if vals else 50)
        self.dz_center = tuple(centers)
        avg = sum(centers) / 4
        self.dz_threshold = avg * 0.05
        return (*self.dz_center, self.dz_threshold)

    @staticmethod
    def _deadzone(value: int, center: int, threshold: float) -> float:
        norm = value - center
        if abs(norm) <= threshold:
            return 0.0
        sign = 1.0 if norm > 0 else -1.0
        return (norm - threshold * sign) / (center if center > 0 else 50.0)

    def get_deadzoned(self) -> tuple:
        """返回 (fwd, strafe, rot) 各 -1.0~+1.0, 已做死区."""
        s = self.get_state()
        c = self.dz_center
        t = self.dz_threshold
        return (
            self._deadzone(s.stick1, c[0], t),
            self._deadzone(s.stick2, c[1], t),
            self._deadzone(s.stick4, c[3], t),
        )

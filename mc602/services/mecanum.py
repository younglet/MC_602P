"""
mc602.services.mecanum — Mecanum Group Service (0x02)

一次指令控制 M1~M4 四路麦克纳姆轮。
与下位机 firmware/devices/services.c::mecanum_group_handler 一一对应。

优势 (vs 逐路调用 bot.motor.set_speed 4 次):
    1 帧往返代替 4 帧 — 延迟降为 1/4, 串口占用降为 1/4
    四路在同一个固件 PID tick 生效 — 毫秒级同步
"""

from __future__ import annotations

from ..comm.packet import Op


class MecanumGroupService:
    """MECANUM_GROUP 服务 (0x02) — 4 路麦克纳姆轮组控"""

    SVC = 0x02

    # GET properties
    PROP_ENCODERS = 0x02   # 4×i32le
    PROP_STATUSES = 0x03   # 4×u8

    # SET properties
    PROP_SPEEDS   = 0x01   # 4×i8

    # CALL commands
    CALL_STOP_ALL = 0x80

    def __init__(self, bot):
        self._bot = bot

    # ── SET ──────────────────────────────────────────────────

    def set_speeds(self, m1: int, m2: int, m3: int, m4: int) -> None:
        """一次设定四路速度, 范围 -100 ~ +100.

        举例 (前进):  mec.set_speeds(80, 80, 80, 80)
        举例 (横移右): mec.set_speeds(-80, 80, 80, -80)
        举例 (旋转 CW): mec.set_speeds(-80, 80, -80, 80)
        举例 (停):      mec.set_speeds(0, 0, 0, 0)
        """
        for v in (m1, m2, m3, m4):
            if not (-100 <= v <= 100):
                raise ValueError(f"speed 必须在 -100~100, 收到 {[m1,m2,m3,m4]}")
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_SPEEDS,
            value=bytes([m1 & 0xFF, m2 & 0xFF, m3 & 0xFF, m4 & 0xFF]),
            timeout=1.0, retry=2, retry_delay=0.1,
        )

    # ── GET ──────────────────────────────────────────────────

    def get_encoders(self) -> tuple:
        """一次读取四路编码器, 返回 (enc1, enc2, enc3, enc4) 均为 int"""
        r = self._bot._request(
            Op.GET, self.SVC, 0, self.PROP_ENCODERS,
            timeout=0.5, retry=0,
        )
        return (
            int.from_bytes(r.value[0:4],   "little", signed=True),
            int.from_bytes(r.value[4:8],   "little", signed=True),
            int.from_bytes(r.value[8:12],  "little", signed=True),
            int.from_bytes(r.value[12:16], "little", signed=True),
        )

    def get_statuses(self) -> tuple:
        """一次读取四路状态, 返回 (st1, st2, st3, st4)
        0=停止 1=运行 2=堵转 3=PID到位 4=PID超时
        """
        r = self._bot._request(
            Op.GET, self.SVC, 0, self.PROP_STATUSES,
            timeout=0.5, retry=0,
        )
        return (r.value[0], r.value[1], r.value[2], r.value[3])

    # ── CALL ─────────────────────────────────────────────────

    def stop_all(self) -> None:
        """一次停四路"""
        self._bot._request(
            Op.CALL, self.SVC, 0, self.CALL_STOP_ALL,
            timeout=1.0, retry=2, retry_delay=0.1,
        )

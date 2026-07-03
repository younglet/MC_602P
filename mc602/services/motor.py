"""
mc602.services.motor — Motor Service 底层 RPC 客户端

与下位机 device/devices/services.c::motor_handler 一一对应。
提供细粒度的 GET/SET/CALL 调用；高层面向对象 API 在 devices/motor.py。
"""

from __future__ import annotations

import time
from typing import Dict

from ..comm.packet import Op, Payload, Status
from ..devices.constants import M1


class MotorService:
    """MOTOR 服务 (0x01) — 6 路电机 PID 闭环控制（底层 RPC 客户端）"""

    SVC = 0x01

    # GET/SET properties
    PROP_SPEED          = 0x01   # i8  rw  目标速度 (-100~100)
    PROP_ENCODER        = 0x02   # i32 r   编码器脉冲累计
    PROP_CURRENT        = 0x03   # u16 r   电流 mA (占位)
    PROP_STATUS         = 0x04   # u8  r   0=停止 1=运行 2=堵转 3=PID到位 4=PID超时
    PROP_PID_KP         = 0x05   # u16 rw  PID Kp ×1000
    PROP_PID_KI         = 0x06   # u16 rw  PID Ki ×1000
    PROP_PID_KD         = 0x07   # u16 rw  PID Kd ×1000
    PROP_CONTROL_MODE   = 0x08   # u8  rw  0=开环 1=PID速度 2=PID位置
    PROP_TARGET_POS     = 0x09   # i32 rw  位置模式目标 (编码器)
    PROP_MAX_SPEED      = 0x0A   # u8  rw  位置模式最大转速 (5~100, 默认80)
    PROP_MOVE_TIMEOUT   = 0x0B   # u16 rw  位置移动超时 (ms)
    PROP_STALL_TIMEOUT  = 0x0C   # u16 rw  堵转判定超时 (ms)

    # CALL commands
    CALL_STOP           = 0x80
    CALL_RESET_ENCODER  = 0x81
    CALL_MOVE_TO        = 0x82   # args: i32 position, u8 max_speed

    # 状态码
    STATUS_STOPPED  = 0
    STATUS_RUNNING  = 1
    STATUS_STALLED  = 2
    STATUS_AT_TARGET = 3
    STATUS_TIMED_OUT = 4

    def __init__(self, bot):
        self._bot = bot

    @staticmethod
    def _check_port(port: int) -> None:
        if not (1 <= port <= 6):
            raise ValueError(f"port 必须在 1~6, 收到 {port}")

    # ----- 速度模式 -----

    def set_speed(self, port: int, speed: int) -> None:
        """设置电机目标速度 (-100~100)。进入 PID 速度闭环模式。
        speed=0 立即停止电机并退出 PID。"""
        self._check_port(port)
        if not (-100 <= speed <= 100):
            raise ValueError(f"speed 必须在 -100~100, 收到 {speed}")
        self._bot._request(
            Op.SET, self.SVC, port, self.PROP_SPEED,
            value=bytes([speed & 0xFF]),
        )

    def get_speed(self, port: int) -> int:
        self._check_port(port)
        r = self._bot._request(Op.GET, self.SVC, port, self.PROP_SPEED)
        v = r.value[0]
        return v - 256 if v >= 128 else v

    # ----- 编码器 -----

    def get_encoder(self, port: int) -> int:
        self._check_port(port)
        r = self._bot._request(Op.GET, self.SVC, port, self.PROP_ENCODER)
        return int.from_bytes(r.value, "little", signed=True)

    def reset_encoder(self, port: int) -> None:
        self._check_port(port)
        self._bot._request(Op.CALL, self.SVC, port, self.CALL_RESET_ENCODER)

    # ----- 状态 -----

    def get_status(self, port: int) -> int:
        self._check_port(port)
        r = self._bot._request(Op.GET, self.SVC, port, self.PROP_STATUS)
        return r.value[0]

    def is_running(self, port: int) -> bool:
        return self.get_status(port) == self.STATUS_RUNNING

    # ----- PID 参数 -----

    def get_pid(self, port: int) -> Dict[str, float]:
        self._check_port(port)
        kp = self._read_u16(port, self.PROP_PID_KP) / 1000.0
        ki = self._read_u16(port, self.PROP_PID_KI) / 1000.0
        kd = self._read_u16(port, self.PROP_PID_KD) / 1000.0
        return {"kp": kp, "ki": ki, "kd": kd}

    def set_pid(self, port: int, kp: float = 0.200,
                ki: float = 0.001, kd: float = 0.004) -> None:
        self._check_port(port)
        self._write_u16(port, self.PROP_PID_KP, int(kp * 1000))
        self._write_u16(port, self.PROP_PID_KI, int(ki * 1000))
        self._write_u16(port, self.PROP_PID_KD, int(kd * 1000))

    # ----- 位置模式 -----

    def move_to(self, port: int, position: int,
                max_speed: int = 80, timeout_ms: int = 5000) -> int:
        """位置闭环: 让电机转到目标编码器位置。
        调用后请用 wait_at_target() 等完成。"""
        self._check_port(port)
        max_speed = max(5, min(100, max_speed))
        args = int(position).to_bytes(4, "little", signed=True) + bytes([max_speed])
        self._bot._request(Op.CALL, self.SVC, port, self.CALL_MOVE_TO, value=args)
        return self.STATUS_RUNNING

    def wait_at_target(self, port: int,
                       poll_interval: float = 0.05,
                       timeout: float = 10.0) -> int:
        """轮询状态直到电机到位 / 堵转 / 超时。返回最终状态码。"""
        self._check_port(port)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            s = self.get_status(port)
            if s in (self.STATUS_AT_TARGET, self.STATUS_STALLED, self.STATUS_TIMED_OUT):
                return s
            time.sleep(poll_interval)
        return self.STATUS_TIMED_OUT

    # ----- 命令 -----

    def stop(self, port: int = M1) -> None:
        self._check_port(port)
        self._bot._request(Op.CALL, self.SVC, port, self.CALL_STOP)

    def stop_all(self) -> None:
        """逐个停所有电机。inst=0 在协议层会被拒，所以退化到循环。"""
        for p in range(1, 7):
            try:
                self._bot._request(Op.CALL, self.SVC, p, self.CALL_STOP)
            except Exception:
                pass

    # ----- 内部 helper -----

    def _read_u16(self, port: int, prop: int) -> int:
        r = self._bot._request(Op.GET, self.SVC, port, prop)
        return int.from_bytes(r.value, "little", signed=False)

    def _write_u16(self, port: int, prop: int, value: int) -> None:
        v = max(0, min(0xFFFF, int(value)))
        self._bot._request(
            Op.SET, self.SVC, port, prop,
            value=v.to_bytes(2, "little")
        )

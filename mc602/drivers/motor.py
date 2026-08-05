"""
mc602.devices.motor — Motor (per-instance) 面向对象封装

设计原则（来自 6 层规范）:
    Motor 是 per-instance 设备对象，通过 bot.motor(port) 工厂创建。
    内部委托给 MotorService 做实际 RPC，不在 Motor 里加任何业务逻辑。

用法:
    motor = robot.motor(1)             # 创建 M1 实例
    motor.set_speed(50)                # 速度闭环
    motor.pid.kp = 0.25                # 调参（PID 子对象）
    enc = motor.encoder                # 读编码器
    motor.move_to(3000).wait()         # 位置闭环
    motor.stop()
"""

from __future__ import annotations

from typing import Dict

from ..services.motor import MotorService


class MotorPID:
    """Motor 的 PID 参数子对象（语法糖）"""

    def __init__(self, motor: "Motor"):
        self._motor = motor

    def _get(self) -> Dict[str, float]:
        return self._motor._service.get_pid(self._motor.port)

    def _set(self, kp: float, ki: float, kd: float) -> None:
        self._motor._service.set_pid(self._motor.port, kp, ki, kd)

    @property
    def kp(self) -> float:
        return self._get()["kp"]

    @kp.setter
    def kp(self, v: float) -> None:
        cur = self._get()
        self._set(v, cur["ki"], cur["kd"])

    @property
    def ki(self) -> float:
        return self._get()["ki"]

    @ki.setter
    def ki(self, v: float) -> None:
        cur = self._get()
        self._set(cur["kp"], v, cur["kd"])

    @property
    def kd(self) -> float:
        return self._get()["kd"]

    @kd.setter
    def kd(self, v: float) -> None:
        cur = self._get()
        self._set(cur["kp"], cur["ki"], v)


class Motor:
    """per-instance 电机对象 (M1~M6)"""

    def __init__(self, bot, port):
        from ..drivers.constants import resolve_port, MOTOR_NAMES
        port = resolve_port(port, MOTOR_NAMES, "电机端口")
        self._bot = bot
        self._service = bot.motor if bot is not None else None
        self.port = port

    # ----- 速度模式 -----

    def set_speed(self, speed: int) -> None:
        """设置电机目标速度 (-100~100)。进入 PID 速度闭环模式。"""
        self._service.set_speed(self.port, speed)

    def get_speed(self) -> int:
        return self._service.get_speed(self.port)

    # ----- 编码器 -----

    def reset_encoder(self) -> None:
        self._service.reset_encoder(self.port)

    @property
    def encoder(self) -> int:
        return self._service.get_encoder(self.port)

    # ----- 状态 -----

    def get_status(self) -> int:
        return self._service.get_status(self.port)

    @property
    def is_running(self) -> bool:
        return self._service.is_running(self.port)

    @property
    def status(self) -> int:
        return self.get_status()

    # ----- PID 参数 -----

    @property
    def pid(self) -> MotorPID:
        """PID 子对象: motor.pid.kp = 0.25"""
        return MotorPID(self)

    def get_pid(self) -> Dict[str, float]:
        return self._service.get_pid(self.port)

    def set_pid(self, kp: float = 0.200, ki: float = 0.001, kd: float = 0.004) -> None:
        self._service.set_pid(self.port, kp, ki, kd)

    # ----- 位置模式 -----

    def move_to(self, position: int, max_speed: int = 80) -> "MoveToFuture":
        """位置闭环: motor.move_to(3000).wait()"""
        self._service.move_to(self.port, position, max_speed=max_speed)
        return MoveToFuture(self)

    def wait_at_target(self, poll_interval: float = 0.05, timeout: float = 10.0) -> int:
        return self._service.wait_at_target(self.port, poll_interval, timeout)

    # ----- 命令 -----

    def stop(self) -> None:
        self._service.stop(self.port)

    def __repr__(self) -> str:
        return f"<Motor M{self.port} status={self.status}>"


class MoveToFuture:
    """move_to() 返回的 future, 链式 .wait() 等到位"""

    def __init__(self, motor: Motor):
        self._motor = motor

    def wait(self, poll_interval: float = 0.05, timeout: float = 10.0) -> int:
        return self._motor.wait_at_target(poll_interval, timeout)

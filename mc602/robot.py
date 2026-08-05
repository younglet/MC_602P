"""
mc602.robot — Robot 顶层门面 (6 层规范的入口)

设计: Robot = MC602 + per-instance 设备工厂
    robot = Robot.connect()
    with robot:
        robot.motor(1).set_speed(50)   # 面向对象 per-instance
        robot.motor(2).pid.kp = 0.25
        print(robot.system.voltage)
"""

from __future__ import annotations

from typing import Optional

from .comm.client import MC602, find_ch340_port
from .drivers.motor import Motor
from .drivers.system import System
from .drivers.stepper import Stepper
from .drivers.servo import Servo485, ServoPWM
from .drivers.io import DigitalOutput, AnalogInput, PWM
from .drivers.lcd import Lcd
from .comm.exceptions import SerialNotFoundError


class Robot:
    """
    顶层 Robot 对象 — 6 层规范的入口点。

    用法:
        with Robot.connect() as robot:
            robot.motor(1).set_speed(50)
            robot.motor(2).pid.kp = 0.25
            print(robot.system.voltage)
    """

    def __init__(self, bot: MC602):
        self._bot = bot

    # ---- 工厂: per-instance 设备 ----

    def motor(self, port: int) -> Motor:
        """返回指定端口的 Motor 实例 (M1~M6)"""
        return Motor(self._bot, port)

    def stepper(self, ch: int) -> Stepper:
        """返回指定通道的 Stepper 实例 (ST1~ST3, 485 总线步进电机)"""
        return Stepper(self._bot, ch)

    def servo485(self, servo_id: int) -> Servo485:
        """返回指定 ID 的 485 总线舵机实例 (S1~S18)"""
        return Servo485(self._bot, servo_id)

    def servo_pwm(self, port) -> ServoPWM:
        """返回指定端口的 PWM 舵机实例 (D1~D7, D1=P7; 传 1~7 或 'D1')"""
        return ServoPWM(self._bot, port)

    def digital_out(self, port) -> DigitalOutput:
        """数字输出实例 ("P1"~"P6" / "D1"~"D7")"""
        return DigitalOutput(self._bot, port)

    def analog(self, port) -> AnalogInput:
        """模拟输入实例 ("A1"~"A6" / "AI1"~"AI3", 共 9 路)"""
        return AnalogInput(self._bot, port)

    def pwm(self, port) -> PWM:
        """通用 PWM 实例 ("D1"~"D7")。⚠️ 与同口 DigitalOutput 互斥。"""
        return PWM(self._bot, port)

    @property
    def lcd(self) -> Lcd:
        """屏幕显示 (单例)。"""
        return Lcd(self._bot)

    @property
    def system(self) -> System:
        """返回 System 单例"""
        return System(self._bot)

    # ---- 透传: 底层 bot 访问 ----

    @property
    def bot(self) -> MC602:
        """底层 MC602 (用于需要直接 RPC 的场景)"""
        return self._bot

    def discover(self, timeout: float = 3.0):
        return self._bot.discover(timeout)

    # ---- 生命周期 ----

    @classmethod
    def connect(cls, port: Optional[str] = None, **kwargs) -> "Robot":
        """
        创建并打开一个 Robot。
        port=None 时自动找 CH340。
        """
        if port is None:
            port = find_ch340_port()
            if port is None:
                raise SerialNotFoundError(
                    "找不到 CH340 串口 (VID=0x1A86)。"
                    "请确认 MC602P 已通过 USB 连接, 且 CH340 驱动已安装。"
                )
        bot = MC602(port=port, **kwargs)
        bot.open()
        return cls(bot)

    def __enter__(self) -> "Robot":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._bot.close()

    def close(self) -> None:
        self._bot.close()

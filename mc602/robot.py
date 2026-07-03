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
from .devices.motor import Motor
from .devices.system import System
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

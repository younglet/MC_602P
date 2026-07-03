"""
mc602.devices — 面向对象设备层（per-instance）

每个硬件一个文件，定义 per-instance Device 类。
对外的面向对象 API：
    motor = robot.motor(1)
    motor.set_speed(50)
    motor.pid.kp = 0.25
"""

from .motor import Motor
from .system import System

__all__ = ["Motor", "System"]

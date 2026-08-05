"""
mc602 — MC602P 机器人控制器 Python SDK + 烧录工具

一站式发布包：拿到这一份就能控制 MC602P / 烧录固件

API 风格:
    1. 推荐 (per-instance OOP):
        from mc602 import Robot
        with Robot.connect() as robot:
            robot.motor(1).set_speed(50)
            robot.motor(1).pid.kp = 0.25

    2. 底层 RPC (service 风格):
        from mc602 import MC602, M1
        with MC602.connect() as bot:
            bot.motor.set_speed(M1, 50)
            print(bot.system.voltage)

    3. 协议层 (高级用户):
        from mc602 import Op, Status, Payload, crc8, cobs_encode

完整文档: README.md
"""

from .comm import (
    Command,
    FrameType,
    MC602,
    Op,
    Payload,
    Status,
    cobs_decode,
    cobs_encode,
    crc8,
    encode_frame,
    encode_response_frame,
    find_ch340_port,
    try_decode_frame,
)
from .comm.exceptions import (
    ConnectionError,
    FlashError,
    MC602Error,
    ProtocolError,
    SerialNotFoundError,
    TimeoutError,
    VerificationError,
    WhalesBotError,  # 历史别名（= MC602Error）
)
from .drivers import Motor, System
from .robot import Robot
from .services import MotorService, SystemService
from .services.motors import MotorsService
from .services.stepper import StepperService
from .services.servo import ServoBusService, ServoPWMService
from .services.mecanum import ChassisService
from .services.io import IOService
from .drivers.btpad import BTPad, BTPadState
from .drivers.motors import Motors
from .drivers.mecanum_chassis import MecanumChassis, Pose2D
from .drivers.stepper import Stepper
from .drivers.servo import Servo485, ServoPWM
from .drivers.io import DigitalOutput, AnalogInput, PWM

# 端口常量
from .drivers.constants import (
    # 电机
    M1, M2, M3, M4, M5, M6, MotorAll,
    # 步进电机
    ST1, ST2, ST3,
    # 端口 (P1~P6 = 1~6, D1~D7 = 7~13)
    P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13,
    D1, D2, D3, D4, D5, D6, D7,
    # 模拟输入 (A1~A6 在 P1~P6, AI1~AI3 在 D1~D3)
    A1, A2, A3, A4, A5, A6, AI1, AI2, AI3,
    # 舵机
    S1, S2, S3, S4, S5, S6, S7, S8, S9, S10,
    S11, S12, S13, S14, S15, S16, S17, S18,
    # 方向
    FORWARD, BACKWARD, TURN_LEFT, TURN_RIGHT,
    # 颜色
    COLOR_WHITE, COLOR_YELLOW, COLOR_PURPLE, COLOR_CYAN,
    COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_BLACK,
    # 蓝牙
    BTSTICK1, BTSTICK2, BTSTICK3, BTSTICK4, BTKEY,
    # CH340
    CH340_VID, CH340_PID, CH340_PID_ALT,
)

__version__ = "0.3.0"
__all__ = [
    # 高层 API
    "Robot", "Motor", "System",
    # 底层 API
    "MC602", "MotorService", "SystemService", "MotorsService",
    "BTPad", "BTPadState",
    "Motors", "MecanumChassis",
    "Stepper", "StepperService",
    "Servo485", "ServoPWM", "ServoBusService", "ServoPWMService",
    "ChassisService", "Pose2D",
    "IOService", "DigitalOutput", "AnalogInput", "PWM",
    # 异常
    "MC602Error", "WhalesBotError",
    "ConnectionError", "ProtocolError", "TimeoutError",
    "VerificationError", "FlashError", "SerialNotFoundError",
    # 协议
    "Op", "Status", "Payload",
    "FrameType", "Command",
    "crc8", "cobs_encode", "cobs_decode",
    "encode_frame", "encode_response_frame", "try_decode_frame",
    # 常量
    "M1", "M2", "M3", "M4", "M5", "M6", "MotorAll",
    "ST1", "ST2", "ST3",
    "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11", "P12", "P13",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7",
    "A1", "A2", "A3", "A4", "A5", "A6", "AI1", "AI2", "AI3",
    "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10",
    "S11", "S12", "S13", "S14", "S15", "S16", "S17", "S18",
    "FORWARD", "BACKWARD", "TURN_LEFT", "TURN_RIGHT",
    "COLOR_WHITE", "COLOR_YELLOW", "COLOR_PURPLE", "COLOR_CYAN",
    "COLOR_RED", "COLOR_GREEN", "COLOR_BLUE", "COLOR_BLACK",
    "BTSTICK1", "BTSTICK2", "BTSTICK3", "BTSTICK4", "BTKEY",
    "CH340_VID", "CH340_PID", "CH340_PID_ALT",
]

"""
硬件端口常量 (与 AT32Gcc/Inc/user/whalesbot.h 严格同步)
"""

# ===== 电机 =====
M1, M2, M3, M4, M5, M6 = 1, 2, 3, 4, 5, 6
MotorAll = 0

# ===== 数字/模拟端口 =====
P1, P2, P3, P4, P5, P6 = 1, 2, 3, 4, 5, 6
P7, P8, P9, P10, P11, P12, P13 = 7, 8, 9, 10, 11, 12, 13

# ===== 舵机 =====
S1, S2, S3, S4, S5, S6, S7, S8, S9, S10 = range(1, 11)
S11, S12, S13, S14, S15, S16, S17, S18 = range(11, 19)

# ===== 移动方向 =====
FORWARD = 1
BACKWARD = 2
TURN_LEFT = 3
TURN_RIGHT = 4

# ===== 颜色 (与 Scratch 兼容) =====
COLOR_WHITE = 1
COLOR_YELLOW = 2
COLOR_PURPLE = 3
COLOR_CYAN = 4
COLOR_RED = 5
COLOR_GREEN = 6
COLOR_BLUE = 7
COLOR_BLACK = 8

# ===== 蓝牙遥控通道 (与 BTXXX 枚举一致) =====
BTSTICK1 = "STICK1"
BTSTICK2 = "STICK2"
BTSTICK3 = "STICK3"
BTSTICK4 = "STICK4"
BTKEY = "KEY"

# ===== CH340 USB 标识 (用于自动发现串口) =====
CH340_VID = 0x1A86
CH340_PID = 0x7523
CH340_PID_ALT = 0x5523

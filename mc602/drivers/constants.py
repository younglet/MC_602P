"""
硬件端口常量 (与 AT32Gcc/Inc/user/whalesbot.h 严格同步)
"""

# ===== 电机 =====
M1, M2, M3, M4, M5, M6 = 1, 2, 3, 4, 5, 6
MotorAll = 0

# ===== 步进电机通道 (与 step_driver.h STP_MOT_CH1~3 一致) =====
ST1, ST2, ST3 = 1, 2, 3

# ===== 数字/模拟端口 (P1~P6 = 1~6, D1~D7 = 7~13) =====
P1, P2, P3, P4, P5, P6 = 1, 2, 3, 4, 5, 6
D1, D2, D3, D4, D5, D6, D7 = 7, 8, 9, 10, 11, 12, 13
# 旧别名: P7~P13 = D1~D7 (数字端口历史编号)
P7, P8, P9, P10, P11, P12, P13 = D1, D2, D3, D4, D5, D6, D7

# ===== 模拟输入 (A1~A6 在 P1~P6, AI1~AI3 在 D1~D3) =====
A1, A2, A3, A4, A5, A6 = 1, 2, 3, 4, 5, 6
AI1, AI2, AI3 = 7, 8, 9

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


# ====================================================================
# 统一端口解析: 常量 / 字符串 / 整数 全兼容
# ====================================================================

# 所有端口域的 名称 → 编号 映射
PORT_TABLE = {
    # 电机
    "M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5, "M6": 6,
    # 步进电机
    "ST1": 1, "ST2": 2, "ST3": 3,
    # 485 舵机
    "S1": 1, "S2": 2, "S3": 3, "S4": 4, "S5": 5, "S6": 6,
    "S7": 7, "S8": 8, "S9": 9, "S10": 10, "S11": 11, "S12": 12,
    "S13": 13, "S14": 14, "S15": 15, "S16": 16, "S17": 17, "S18": 18,
    # 数字口 (P1~P6 = 1~6, D1~D7 = 7~13)
    "P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5, "P6": 6,
    "D1": 7, "D2": 8, "D3": 9, "D4": 10, "D5": 11, "D6": 12, "D7": 13,
    # 模拟输入 (A1~A6 = P 口, AI1~AI3 = D1~D3)
    "A1": 1, "A2": 2, "A3": 3, "A4": 4, "A5": 5, "A6": 6,
    "AI1": 7, "AI2": 8, "AI3": 9,
}

# 各域的名称集 (用于校验)
MOTOR_NAMES   = {k for k in PORT_TABLE if k.startswith("M") and k[1:].isdigit()}
STEPPER_NAMES = {k for k in PORT_TABLE if k.startswith("ST")}
SERVO_NAMES   = {k for k in PORT_TABLE if k.startswith("S") and not k.startswith("ST")}
PWM_NAMES     = {k for k in PORT_TABLE if k.startswith("D")}
DIGITAL_NAMES = {k for k in PORT_TABLE if k.startswith("P")} | PWM_NAMES   # P1~P6 + D1~D7
ANALOG_NAMES  = {k for k in PORT_TABLE if k.startswith("A")}                # A1~A6 + AI1~AI3


def resolve_port(value, names: set, what: str) -> int:
    """统一端口解析: 整数/常量直通, 字符串查名称表。

    Args:
        value: 端口 (整数 或 'M1'/'D3'/'AI2' 等字符串)
        names: 允许的名称集合 (如 MOTOR_NAMES)
        what:  错误信息里的功能名 (如 "电机端口")
    """
    if isinstance(value, str):
        key = value.strip().upper()
        if key in names:
            return PORT_TABLE[key]
        if key.isdigit():   # 纯数字字符串 "3" → 3
            p = int(key)
            valid = {PORT_TABLE[n] for n in names}
            if p in valid:
                return p
        raise ValueError(f"{what}: 无效端口 {value}, 可用 {sorted(names)}")
    p = int(value)
    valid = {PORT_TABLE[n] for n in names}
    if p not in valid:
        raise ValueError(f"{what}: 无效端口 {value}, 可用 {sorted(names)}")
    return p

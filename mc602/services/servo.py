"""
mc602.services.servo — Servo 服务底层 RPC 客户端 (485 总线 + PWM 两个版本)

与下位机 firmware/devices/services.c 对应:
  - ServoBusService  (SVC 0x20) — 485 总线舵机 (经 step_driver 线程, 与步进共存)
  - ServoPWMService  (SVC 0x21) — PWM 舵机 (P7~P13, 7 路)

高层面向对象 API 在 drivers/servo.py (Servo485 / ServoPWM)。
"""

from __future__ import annotations

from ..comm.packet import Op

# 485 舵机 (ServoBus)
SERVO_ANGLE_MIN = -150      # SDK angle_to_servo_value 范围
SERVO_ANGLE_MAX = 150
SERVO_SPEED_MIN = 1
SERVO_SPEED_MAX = 100

# PWM 舵机 (ServoPWM)
PWM_ANGLE_MIN = 0
PWM_ANGLE_MAX = 180
PWM_SPEED_MIN = 10
PWM_SPEED_MAX = 100

SERVO_ID_MAX = 18          # S1~S18
PWM_PORT_MAX = 13          # D1~D7 = 物理端口 7~13

# D1~D7 → 物理端口 P7~P13 (SDK SetServo 参数)
PWM_PORT_TO_P = {7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12, 13: 13}


class ServoBusService:
    """SERVO BUS 服务 (0x20) — 485 总线舵机（底层 RPC 客户端）"""

    SVC = 0x20

    # GET properties
    PROP_ANGLE = 0x01   # i16 r  最近一次目标角度 (固件记录)

    # CALL commands
    CALL_SET_ANGLE = 0x80   # args: i16 angle(-150~150) + u8 speed(1~100)
    CALL_CHANGE_ID = 0x81   # args: u8 now_id + u8 new_id(1~3)
    CALL_READ_ANGLE = 0x82  # → i32  实际角度 (独占总线)
    CALL_PING = 0x83        # → u8   在线检测
    CALL_READ_VERSION = 0x84  # → u16 舵机固件版本
    CALL_SCAN = 0x87        # args: u8 max_id → u8×N 在线 ID 列表

    # 改 ID 目标范围
    NEW_ID_MIN = 1
    NEW_ID_MAX = 3

    def __init__(self, bot):
        self._bot = bot

    @staticmethod
    def _check_servo_id(servo_id: int) -> None:
        if not (1 <= servo_id <= SERVO_ID_MAX):
            raise ValueError(f"舵机 ID 必须在 1~{SERVO_ID_MAX} (S1~S18), "
                             f"收到 {servo_id}")

    def set_angle(self, servo_id: int, angle: int, speed: int = 40) -> None:
        """设置 485 舵机角度。servo_id: 1~18, angle: -150~150, speed: 1~100。
        经 step_driver 线程发送, 与步进电机共用总线, 阻塞 ≤10ms。"""
        self._check_servo_id(servo_id)
        angle = max(SERVO_ANGLE_MIN, min(SERVO_ANGLE_MAX, int(angle)))
        speed = max(SERVO_SPEED_MIN, min(SERVO_SPEED_MAX, int(speed)))
        args = int(angle).to_bytes(2, "little", signed=True) + bytes([speed])
        self._bot._request(
            Op.CALL, self.SVC, servo_id, self.CALL_SET_ANGLE,
            value=args, timeout=1.0, retry=2, retry_delay=0.1,
        )

    def get_angle(self, servo_id: int) -> int:
        """回读最近一次目标角度 (固件侧记录)。"""
        self._check_servo_id(servo_id)
        r = self._bot._request(Op.GET, self.SVC, servo_id, self.PROP_ANGLE)
        return int.from_bytes(r.value, "little", signed=True)

    def change_id(self, id_now: int, id_new: int) -> None:
        """修改舵机 ID。id_now: 当前 ID, id_new: 新 ID (仅限 1~3)。
        ⚠️ 仅支持总线上只有 1 个舵机时操作 (SDK 限制)。
        固件会暂让步进线程独占 485 总线完成修改。"""
        self._check_servo_id(id_now)
        if not (self.NEW_ID_MIN <= id_new <= self.NEW_ID_MAX):
            raise ValueError(f"新舵机 ID 仅限 {self.NEW_ID_MIN}~{self.NEW_ID_MAX}, "
                             f"收到 {id_new}")
        args = bytes([id_now, id_new])
        self._bot._request(
            Op.CALL, self.SVC, id_now, self.CALL_CHANGE_ID,
            value=args, timeout=2.0, retry=2, retry_delay=0.3,
        )

    def read_angle(self, servo_id: int) -> int:
        """读舵机实际角度 (驱动器反馈, 独占总线)。
        固件独占 485 总线期间步进线程暂停, 阻塞 ≤10ms。"""
        self._check_servo_id(servo_id)
        r = self._bot._request(
            Op.CALL, self.SVC, servo_id, self.CALL_READ_ANGLE,
            timeout=1.0, retry=1, retry_delay=0.2,
        )
        return int.from_bytes(r.value, "little", signed=True)

    def ping(self, servo_id: int) -> bool:
        """舵机在线检测。返回 True 表示在线。"""
        self._check_servo_id(servo_id)
        r = self._bot._request(
            Op.CALL, self.SVC, servo_id, self.CALL_PING,
            timeout=1.0, retry=1, retry_delay=0.2,
        )
        return r.value[0] != 0

    def read_version(self, servo_id: int) -> int:
        """读舵机内部固件版本号。"""
        self._check_servo_id(servo_id)
        r = self._bot._request(
            Op.CALL, self.SVC, servo_id, self.CALL_READ_VERSION,
            timeout=1.0, retry=1, retry_delay=0.2,
        )
        return int.from_bytes(r.value, "little", signed=False)

    def scan(self, max_id: int = 3) -> list:
        """扫描总线上在线的舵机 ID (默认 1~3, 上限 18)。
        固件逐个 PING, 独占总线, 阻塞 ~max_id×5ms。"""
        max_id = max(1, min(SERVO_ID_MAX, int(max_id)))
        r = self._bot._request(
            Op.CALL, self.SVC, 0, self.CALL_SCAN,
            value=bytes([max_id]), timeout=3.0, retry=1, retry_delay=0.3,
        )
        return list(r.value)


class ServoPWMService:
    """SERVO PWM 服务 (0x21) — PWM 舵机（底层 RPC 客户端）"""

    SVC = 0x21

    # GET properties
    PROP_ANGLE = 0x01   # i16 r  最近一次目标角度 (固件记录)
    PROP_DUTY = 0x02    # u16 rw 通用 PWM 占空比 (0~1000 = 0~100.0%)

    # CALL commands
    CALL_SET_ANGLE = 0x80   # args: u16 angle(0~180) + u8 speed(10~100)

    def __init__(self, bot):
        self._bot = bot

    @staticmethod
    def _check_port(port) -> int:
        """PWM 舵机端口: D1~D7 = 物理端口 7~13。
        接受整数 7~13 或 'D1'~'D7' 字符串, 返回固件 inst 1~7。"""
        if isinstance(port, str):
            s = port.strip().upper()
            if s.startswith("D"):
                port = int(s[1:]) + 6
            else:
                port = int(s.lstrip("P"))
        if not (7 <= port <= PWM_PORT_MAX):
            raise ValueError(f"PWM 舵机端口必须在 D1~D7 (7~13), "
                             f"收到 {port}")
        return port - 6

    def set_angle(self, port, angle: int, speed: int = 50) -> None:
        """设置 PWM 舵机角度。port: D1~D7, angle: 0~180, speed: 10~100。"""
        port = self._check_port(port)
        angle = max(PWM_ANGLE_MIN, min(PWM_ANGLE_MAX, int(angle)))
        speed = max(PWM_SPEED_MIN, min(PWM_SPEED_MAX, int(speed)))
        args = int(angle).to_bytes(2, "little") + bytes([speed])
        self._bot._request(
            Op.CALL, self.SVC, port, self.CALL_SET_ANGLE,
            value=args, timeout=1.0, retry=2, retry_delay=0.1,
        )

    def get_angle(self, port) -> int:
        """回读最近一次目标角度 (固件侧记录)。"""
        port = self._check_port(port)
        r = self._bot._request(Op.GET, self.SVC, port, self.PROP_ANGLE)
        return int.from_bytes(r.value, "little", signed=True)

    def set_duty(self, port, duty_percent: float) -> None:
        """通用 PWM 占空比输出 (0~100%, 40Hz)。
        ⚠️ 与 set_angle 共用同一引脚/定时器, 混用会互相覆盖。"""
        port = self._check_port(port)
        duty = max(0.0, min(100.0, float(duty_percent)))
        self._bot._request(
            Op.SET, self.SVC, port, self.PROP_DUTY,
            value=int(duty * 10).to_bytes(2, "little"),
            timeout=1.0, retry=2, retry_delay=0.1,
        )

    def get_duty(self, port) -> float:
        """回读最近一次占空比 (%)."""
        port = self._check_port(port)
        r = self._bot._request(Op.GET, self.SVC, port, self.PROP_DUTY)
        return int.from_bytes(r.value, "little") / 10.0

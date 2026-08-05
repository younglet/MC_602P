"""
mc602.drivers.servo — Servo (per-instance) 面向对象封装, 两个版本

  485 总线舵机: Servo485(bot, sid)     — S1~S18, 与步进共用总线
  PWM 舵机:     ServoPWM(bot, port)    — P7~P13 (port 传 1~7 或 'P7')

用法:
    s = robot.servo485(1)          # 485 舵机 S1
    s.set_angle(90)                # -150~150
    s.angle = -45                  # property 写法

    p = robot.servo_pwm(7)         # PWM 舵机 P7
    p.set_angle(90, speed=60)      # 0~180
"""

from __future__ import annotations

from ..services.servo import (
    ServoBusService,
    ServoPWMService,
    SERVO_ANGLE_MIN, SERVO_ANGLE_MAX,
    PWM_ANGLE_MIN, PWM_ANGLE_MAX,
    PWM_SPEED_MIN, PWM_SPEED_MAX,
    PWM_PORT_TO_P,
)


class Servo485:
    """per-instance 485 总线舵机对象 (S1~S18)"""

    def __init__(self, bot, servo_id):
        from ..drivers.constants import resolve_port, SERVO_NAMES
        servo_id = resolve_port(servo_id, SERVO_NAMES, "舵机 ID")
        self._bot = bot
        self._service = bot.servo_bus if bot is not None else None
        self.servo_id = servo_id

    def set_angle(self, angle: int, speed: int = 40) -> None:
        """设置角度 (-150~150), speed 1~100。阻塞 ≤10ms (总线发送)。"""
        self._service.set_angle(self.servo_id, angle, speed)

    @property
    def angle(self) -> int:
        """回读最近一次设置的角度 (固件侧记录, SDK 无同步读回)。"""
        return self._service.get_angle(self.servo_id)

    @angle.setter
    def angle(self, v: int) -> None:
        self.set_angle(v)

    def change_id(self, id_new: int) -> None:
        """修改本舵机 ID (id_new 仅限 1~3)。
        ⚠️ 总线上只能有 1 个舵机时操作。修改后本实例 servo_id 同步更新。"""
        self._service.change_id(self.servo_id, id_new)
        self.servo_id = id_new

    def read_angle(self) -> int:
        """读舵机实际角度 (驱动器反馈, 独占总线)。"""
        return self._service.read_angle(self.servo_id)

    def ping(self) -> bool:
        """在线检测。"""
        return self._service.ping(self.servo_id)

    def read_version(self) -> int:
        """读舵机内部固件版本。"""
        return self._service.read_version(self.servo_id)

    @classmethod
    def find_devices(cls, bot) -> list:
        """查找总线上在线的舵机 ID (固定扫描 1~3)。
        返回在线 ID 列表, 如 [1, 3]。用法: Servo485.find_devices(bot) 或
        robot.servo485 同系列实例均可调用。"""
        return bot.servo_bus.scan(3)

    def __repr__(self) -> str:
        return f"<Servo485 S{self.servo_id}>"


class ServoPWM:
    """per-instance PWM 舵机对象 (D1~D7 = 物理端口 7~13)"""

    def __init__(self, bot, port):
        if isinstance(port, str):
            s = port.strip().upper()
            if s.startswith("D"):
                port = int(s[1:]) + 6
            else:
                port = int(s.lstrip("P"))
        if not (7 <= port <= 13):
            raise ValueError(f"PWM 舵机端口必须在 D1~D7 (7~13), 收到 {port}")
        self._bot = bot
        self._service = bot.servo_pwm if bot is not None else None
        self.port = port          # 物理端口 7~13
        self.name = f"D{port - 6}"  # D1~D7

    def set_angle(self, angle: int, speed: int = 50) -> None:
        """设置角度 (0~180), speed 10~100。"""
        self._service.set_angle(self.port, angle, speed)

    @property
    def angle(self) -> int:
        """回读最近一次设置的角度 (固件侧记录)。"""
        return self._service.get_angle(self.port)

    @angle.setter
    def angle(self, v: int) -> None:
        self.set_angle(v)

    def set_duty(self, duty_percent: float) -> None:
        """通用 PWM 占空比输出 (0~100%, 40Hz)。⚠️ 与 set_angle 互斥。"""
        self._service.set_duty(self.port, duty_percent)

    @property
    def duty(self) -> float:
        """回读最近一次占空比 (%)."""
        return self._service.get_duty(self.port)

    @duty.setter
    def duty(self, v: float) -> None:
        self.set_duty(v)

    def __repr__(self) -> str:
        return f"<ServoPWM {self.name} (P{self.port})>"

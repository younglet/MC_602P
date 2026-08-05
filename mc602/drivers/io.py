"""
mc602.drivers.io — IO 驱动 (数字输出 / 模拟输入 / PWM)

端口命名统一为物理端口号 1~13:
    P1~P6 = 1~6   水晶头 (数字 DIG1~6 + 模拟 A1~A6 同口不同引脚)
    D1~D7 = 7~13  独立口 (数字 DIG7~13 / PWM 同引脚互斥, 模拟 AI1~AI3 在 D1~D3)

三个类:
    DigitalOutput(bot, "P2")   数字输出 (也支持 D1~D7)
    AnalogInput(bot, "A1")     模拟输入 (A1~A6 = P1~P6, AI1~AI3 = D1~D3)
    PWM(bot, "D3")             通用 PWM 占空比 (仅 D1~D7)

用法:
    pump = robot.digital_out("P2")
    pump.write(1)

    a = robot.analog("AI2")
    print(a.read(), a.voltage)

    pwm = robot.pwm("D3")
    pwm.set_duty(50.0)
"""

from __future__ import annotations

from ..services.io import IOService, MODE_INPUT, MODE_OUTPUT, ANALOG_LABELS
from ..services.servo import ServoPWMService
from ..drivers.constants import resolve_port, PWM_NAMES, DIGITAL_NAMES, ANALOG_NAMES


def _parse_port(port, table: set, what: str) -> int:
    return resolve_port(port, table, what)


def _port_label(names: set, port: int) -> str:
    """编号 → 名称 (如 2 → 'P2', 9 → 'D3')"""
    from ..drivers.constants import PORT_TABLE
    for k, v in PORT_TABLE.items():
        if k in names and v == port:
            return k
    return str(port)


class DigitalOutput:
    """数字输出 (P1~P6 / D1~D7)。⚠️ D 口与 PWM 共用引脚, 互斥。"""

    def __init__(self, bot, port):
        self._port = _parse_port(port, DIGITAL_NAMES, "数字输出端口")
        self._service = bot.io if bot is not None else None
        self.port = self._port
        self.name = _port_label(DIGITAL_NAMES, self._port)
    def write(self, value: int) -> None:
        """输出电平 0/1。"""
        self._service.write(self._port, value)

    @property
    def value(self) -> int:
        return self._service.read(self._port)

    @value.setter
    def value(self, v: int) -> None:
        self.write(v)

    def read(self) -> int:
        """读回电平。"""
        return self._service.read(self._port)

    def toggle(self) -> None:
        """输出反转。"""
        self._service.toggle(self._port)

    def set_input(self) -> None:
        """配置为输入 (上拉)。"""
        self._service.set_mode(self._port, MODE_INPUT)

    def set_output(self) -> None:
        """配置为输出 (推挽)。"""
        self._service.set_mode(self._port, MODE_OUTPUT)

    def __repr__(self) -> str:
        return f"<DigitalOutput {self.name} value={self.read()}>"


class AnalogInput:
    """模拟输入 (A1~A6 = P1~P6, AI1~AI3 = D1~D3, 共 9 路)。"""

    def __init__(self, bot, port):
        self._port = _parse_port(port, ANALOG_NAMES, "模拟输入端口")
        self._service = bot.io if bot is not None else None
        self.port = self._port
        self.name = ANALOG_LABELS[self._port]   # A1~A6 / AI1~AI3

    def read(self) -> int:
        """读原始 ADC 值 (0~4095, 12 位)。"""
        return self._service.read_analog(self._port)

    @property
    def value(self) -> int:
        return self.read()

    def read_voltage(self) -> float:
        """换算电压 (V, 3.3V 参考)。"""
        return self.read() / 4095 * 3.3

    @property
    def voltage(self) -> float:
        return self.read_voltage()

    def __repr__(self) -> str:
        return f"<AnalogInput {self.name} value={self.read()}>"


class PWM:
    """通用 PWM 占空比输出 (D1~D7, 40Hz)。⚠️ 与 DigitalOutput 互斥。"""

    def __init__(self, bot, port):
        self._port = _parse_port(port, PWM_NAMES, "PWM 端口")
        self._service = bot.servo_pwm if bot is not None else None
        self.port = self._port
        self.name = f"D{self._port - 6}"

    def set_duty(self, duty_percent: float) -> None:
        """设置占空比 0~100%。"""
        self._service.set_duty(self._port, duty_percent)

    @property
    def duty(self) -> float:
        """回读占空比 (%)."""
        return self._service.get_duty(self._port)

    @duty.setter
    def duty(self, v: float) -> None:
        self.set_duty(v)

    def __repr__(self) -> str:
        return f"<PWM {self.name} duty={self.duty}%>"

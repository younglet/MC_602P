"""
mc602.services.io — IO 服务底层 RPC 客户端 (SVC 0x50)

数字 IO: P1~P6 (DIG1~6) + D1~D7 (DIG7~13, ⚠️与 PWM 舵机共用引脚)
模拟输入: A1~A6 (P1~P6) + AI1~AI3 (D1~D3) 共 9 路
"""

from __future__ import annotations

from ..comm.packet import Op

IO_PORT_MAX = 13   # P1~P6 + D1~D7
ANALOG_MAX = 9     # A1~A6 + AI1~AI3

MODE_INPUT = 0
MODE_OUTPUT = 1

# 模拟输入命名: inst 1~6 = A1~A6, 7~9 = AI1~AI3
ANALOG_LABELS = {1: "A1", 2: "A2", 3: "A3", 4: "A4", 5: "A5", 6: "A6",
                 7: "AI1", 8: "AI2", 9: "AI3"}

# 数字口命名: 1~6 = P1~P6, 7~13 = D1~D7
DIGITAL_NAMES = {**{i: f"P{i}" for i in range(1, 7)},
                 **{i: f"D{i - 6}" for i in range(7, 14)}}


class IOService:
    """IO 服务 (0x50) — P1~P6 数字输入输出（底层 RPC 客户端）"""

    SVC = 0x50

    PROP_VALUE = 0x01   # u8 rw  读: 输入电平; 写: 输出电平
    PROP_MODE = 0x02    # u8 rw  0=输入(上拉) 1=输出(推挽)
    PROP_ANALOG = 0x03  # u16 r  模拟输入 (A1~A6)
    CALL_TOGGLE = 0x80

    def __init__(self, bot):
        self._bot = bot

    @staticmethod
    def _check_port(port) -> int:
        """数字口: 1~6 = P1~P6, 7~13 = D1~D7。
        接受整数或 'P5'/'D3' 字符串。"""
        if isinstance(port, str):
            s = port.strip().upper()
            if s.startswith("D"):
                port = int(s.lstrip("D")) + 6
            else:
                port = int(s.lstrip("P"))
        if not (1 <= port <= IO_PORT_MAX):
            raise ValueError(f"IO 端口必须在 1~{IO_PORT_MAX} "
                             f"(P1~P6/D1~D7), 收到 {port}")
        return port

    def read(self, port) -> int:
        """读端口电平 (0/1)。输出模式时读回输出状态。"""
        port = self._check_port(port)
        r = self._bot._request(
            Op.GET, self.SVC, port, self.PROP_VALUE,
            timeout=0.5, retry=1, retry_delay=0.1,
        )
        return r.value[0]

    def write(self, port, value: int) -> None:
        """输出电平 (0/1)。自动切输出模式。"""
        port = self._check_port(port)
        self._bot._request(
            Op.SET, self.SVC, port, self.PROP_VALUE,
            value=bytes([1 if value else 0]),
            timeout=1.0, retry=2, retry_delay=0.1,
        )

    def set_mode(self, port, mode: int) -> None:
        """0=输入(上拉) 1=输出(推挽)。"""
        port = self._check_port(port)
        self._bot._request(
            Op.SET, self.SVC, port, self.PROP_MODE,
            value=bytes([1 if mode else 0]),
            timeout=1.0, retry=2, retry_delay=0.1,
        )

    def get_mode(self, port) -> int:
        port = self._check_port(port)
        r = self._bot._request(Op.GET, self.SVC, port, self.PROP_MODE)
        return r.value[0]

    def read_analog(self, port) -> int:
        """读模拟输入 (10 位 ADC)。
        port 1~6 = A1~A6 (P1~P6), 7~9 = AI1~AI3 (D1~D3)。"""
        port = self._check_port(port)
        if port > ANALOG_MAX:
            raise ValueError(f"模拟输入只有 {ANALOG_MAX} 路 "
                             f"(A1~A6/AI1~AI3), D{port - 6} 口无模拟")
        r = self._bot._request(
            Op.GET, self.SVC, port, self.PROP_ANALOG,
            timeout=0.5, retry=1, retry_delay=0.1,
        )
        return int.from_bytes(r.value, "little", signed=False)

    def toggle(self, port) -> None:
        """输出反转。"""
        port = self._check_port(port)
        self._bot._request(
            Op.CALL, self.SVC, port, self.CALL_TOGGLE,
            timeout=1.0, retry=2, retry_delay=0.1,
        )

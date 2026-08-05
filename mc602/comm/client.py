"""
client.py — MC602 主类（RPC 客户端，串口传输层）

职责:
    1. 自动发现 CH340 串口 (VID=0x1A86 PID=0x7523 或 0x5523)
    2. 串口连接 (1 Mbps, 与下位机 USART1 匹配)
    3. 协议层收发: 请求/响应匹配 (按 seq)
    4. 提供面向用户的子 API:
         bot.system.voltage / version / uptime
         bot.motor.set_speed(M1, 50)
         bot.motor.get_encoder(M1)
         bot.motor.stop(M1)
         bot.motor.move_to(M1, 3000, max_speed=80)

高层面向对象 API (per-instance):
    mc602.Robot 包装 MC602 并提供 robot.motor(1) 工厂。
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

import serial  # type: ignore
import serial.tools.list_ports as list_ports  # type: ignore

from ..drivers.constants import M1
from .exceptions import (
    ConnectionError,
    SerialNotFoundError,
)
from ..services.motor import MotorService
from ..services.system import SystemService
from ..services.stepper import StepperService
from ..services.servo import ServoBusService, ServoPWMService
from ..services.mecanum import ChassisService
from ..services.io import IOService
from ..services.lcd import LCDService
from ..drivers.btpad import BTPad
from .packet import (
    Op,
    Payload,
    Status,
    encode_frame,
    try_decode_frame,
)


# CH340 USB -> Serial 标识 (下位机通过 CH340 引出虚拟串口)
CH340_VID          = 0x1A86
CH340_PID_PRIMARY  = 0x7523   # pydownload.py 使用 PID=29987=0x7523
CH340_PID_ALT      = 0x5523


# 默认串口参数 (与固件 USART1 一致)
DEFAULT_BAUDRATE   = 1_000_000
DEFAULT_TIMEOUT    = 0.5
DEFAULT_RW_TIMEOUT = 3.0


# =========================================================================
# 自动串口发现
# =========================================================================

def find_ch340_port() -> Optional[str]:
    """在系统上找首个匹配 CH340 VID/PID 的串口, 返回设备名 (如 'COM7')"""
    for p in list_ports.comports():
        if p.vid == CH340_VID and p.pid in (CH340_PID_PRIMARY, CH340_PID_ALT):
            return p.device
    return None


# =========================================================================
# MC602
# =========================================================================

class MC602:
    """
    与 MC602P 控制器通讯的高层对象（RPC 客户端）。

    用法:
        with MC602.connect() as bot:
            bot.motor.set_speed(M1, 50)
            time.sleep(3)
            bot.motor.stop(M1)
    """

    def __init__(self, port: str, baudrate: int = DEFAULT_BAUDRATE,
                 timeout: float = DEFAULT_TIMEOUT,
                 reader_poll_ms: float = 10.0):
        self._port_name = port
        self._baudrate  = baudrate
        self._timeout   = timeout
        self._reader_poll_ms = reader_poll_ms
        self._ser: Optional[serial.Serial] = None

        self._rx_buf = bytearray()
        self._rx_lock = threading.Lock()

        self._next_seq = 1
        self._seq_lock = threading.Lock()
        self._pending: Dict[int, Optional[Payload]] = {}
        self._pending_event = threading.Event()
        self._reader_thread: Optional[threading.Thread] = None
        self._reader_stop = threading.Event()

        # 子 API
        self.system  = SystemService(self)
        self.motor   = MotorService(self)
        self.stepper = StepperService(self)
        self.servo_bus = ServoBusService(self)
        self.servo_pwm = ServoPWMService(self)
        self.chassis = ChassisService(self)
        self.io = IOService(self)
        self.lcd = LCDService(self)
        self.pad = BTPad(self)

    def __enter__(self) -> "MC602":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @classmethod
    def connect(cls, port: Optional[str] = None,
                baudrate: int = DEFAULT_BAUDRATE,
                timeout: float = DEFAULT_TIMEOUT) -> "MC602":
        if port is None:
            port = find_ch340_port()
            if port is None:
                raise SerialNotFoundError(
                    "找不到 CH340 串口 (VID=0x1A86)。"
                    "请确认 MC602P 已通过 USB 连接, 且 CH340 驱动已安装。"
                )
        bot = cls(port=port, baudrate=baudrate, timeout=timeout)
        bot.open()
        return bot

    def open(self) -> None:
        if self._ser is not None:
            return
        try:
            self._ser = serial.Serial(
                port=self._port_name,
                baudrate=self._baudrate,
                timeout=self._timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            # 关键: 打开后立即禁用 DTR/RTS — CH340 的 DTR 接复位电路,
            # pyserial 默认拉高 DTR → 固件复位 → 重启需 ~10s → 首个请求超时
            try:
                self._ser.dtr = False
                self._ser.rts = False
            except Exception:
                pass
        except (serial.SerialException, OSError) as e:
            raise ConnectionError(f"打开串口失败: {self._port_name}: {e}") from e

        self._reader_stop.clear()
        self._reader_thread = threading.Thread(
            target=self._reader_loop, name="MC602Reader", daemon=True
        )
        self._reader_thread.start()

        # 链路预热握手: 板子 USB/复位特性导致"连接后第一个请求偶发超时",
        # open 后立即发一次 GET version 稳定链路 (失败重试, 不阻断)。
        for _ in range(3):
            try:
                self._request(Op.GET, 0xFE, 0, 0x02, timeout=1.0, retry=1)
                break
            except Exception:
                time.sleep(0.3)

    def close(self) -> None:
        if self._ser is None:
            return
        self._reader_stop.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.5)
        try:
            self._ser.close()
        except Exception:
            pass
        self._ser = None

    # -----------------------------------------------------------------
    # 收发核心
    # -----------------------------------------------------------------

    def _allocate_seq(self) -> int:
        with self._seq_lock:
            seq = self._next_seq
            self._next_seq = (self._next_seq + 1) & 0x7F
            if self._next_seq == 0:
                self._next_seq = 1
            return seq

    def _send_frame(self, payload: Payload) -> int:
        if self._ser is None:
            raise ConnectionError("串口未打开")
        data = encode_frame(payload)
        try:
            self._ser.write(data)
            self._ser.flush()
        except (serial.SerialException, OSError) as e:
            raise ConnectionError(f"串口写入失败: {e}") from e
        return payload.seq

    def _read_more(self) -> None:
        if self._ser is None:
            return
        try:
            n = self._ser.in_waiting
            if n == 0:
                chunk = self._ser.read(1)
                n = len(chunk)
                if n:
                    self._rx_buf.extend(chunk)
            else:
                chunk = self._ser.read(min(n, 256))
                self._rx_buf.extend(chunk)
        except (serial.SerialException, OSError) as e:
            raise ConnectionError(f"串口读取失败: {e}") from e

        if n == 0:
            time.sleep(self._reader_poll_ms / 1000.0)

    def _reader_loop(self) -> None:
        while not self._reader_stop.is_set():
            try:
                self._read_more()
            except ConnectionError:
                break

            with self._rx_lock:
                if not self._rx_buf:
                    continue
                payload = try_decode_frame(self._rx_buf)
                if payload is None:
                    if len(self._rx_buf) > 1024:
                        self._rx_buf.pop(0)
                    continue
                frame_end = bytes(self._rx_buf).index(0x00) + 2
                if frame_end > len(self._rx_buf):
                    continue
                del self._rx_buf[:frame_end]

            if payload.seq == 0:
                continue
            with self._seq_lock:
                if payload.seq in self._pending:
                    self._pending[payload.seq] = payload
                    self._pending_event.set()

    def _request(self, op: Op, svc: int, inst: int, prop: int,
                 value: bytes = b"",
                 timeout: float = 2.0,
                 retry: int = 1,
                 retry_delay: float = 0.1) -> Payload:
        """发送一帧请求, 等待响应, 可选自动重试.

        retry: 超时后额外重试次数 (默认 1 — 心跳刷屏的 SPI 窗口会丢帧,
        重发即成功).
        retry_delay: 重试前等待秒数, 给固件 UART handler 喘息窗口.
        """
        last_err = None
        for attempt in range(retry + 1):
            seq = self._allocate_seq()
            payload = Payload(seq=seq, op=op, svc=svc, inst=inst, prop=prop, value=value)
            # 必须先在 _pending 里占一个坑, 再发包 — 否则 MCU 快速响应时
            # reader 线程可能比 _await_response 更早拿到响应帧, 然后发现
            # seq 还没注册就直接丢弃 (race condition, 概率性丢响应)。
            with self._seq_lock:
                self._pending[seq] = None
                self._pending_event.clear()
            self._send_frame(payload)
            try:
                return self._await_response(seq, timeout)
            except TimeoutError as e:
                last_err = e
                if attempt < retry:
                    time.sleep(retry_delay)
        raise last_err  # type: ignore[misc]

    def _await_response(self, seq: int, timeout: float) -> Payload:
        # seq 已在 _request 里预先注册过了, 这里不再重复
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._pending_event.wait(timeout=0.05)
            with self._seq_lock:
                resp = self._pending.get(seq)
                if resp is not None:
                    del self._pending[seq]
                    if resp.status != Status.OK:
                        from .exceptions import ProtocolError
                        raise ProtocolError(
                            f"MCU 返回错误: op={resp.op.name} svc=0x{resp.svc:02X} "
                            f"inst={resp.inst} prop=0x{resp.prop:02X} "
                            f"status={resp.status.name}"
                        )
                    return resp
            self._pending_event.clear()
        with self._seq_lock:
            self._pending.pop(seq, None)
        from .exceptions import TimeoutError
        raise TimeoutError(f"等响应超时 seq={seq} timeout={timeout}s")

    def discover(self, timeout: float = DEFAULT_RW_TIMEOUT) -> List[int]:
        seq = self._allocate_seq()
        payload = Payload(seq=seq, op=Op.DISCOVER, svc=0, inst=0, prop=0)
        # 同 _request: 先占坑再发, 避免快速响应的 race
        with self._seq_lock:
            self._pending[seq] = None
            self._pending_event.clear()
        self._send_frame(payload)
        resp = self._await_response(seq, timeout)
        return list(resp.value)


__all__ = ["MC602", "find_ch340_port", "CH340_VID", "CH340_PID_PRIMARY", "CH340_PID_ALT"]

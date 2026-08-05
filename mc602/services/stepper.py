"""
mc602.services.stepper — Stepper Service 底层 RPC 客户端

与下位机 firmware/devices/services.c::stepper_handler 一一对应 (SVC 0x30)。
底层是 SDK step_driver: 485 总线驱动器, 3 通道, 自带 100Hz 加减速线程。

通道常量: ST1 / ST2 / ST3 (见 drivers/constants.py)。
高层面向对象 API 在 drivers/stepper.py。
"""

from __future__ import annotations

from ..comm.packet import Op

# 速度量程 (与 step_driver.c STEP_SPD_MAX/MIN 一致)
STEP_SPD_MAX = 32000
STEP_SPD_MIN = 50      # |speed| < 50 时驱动器视为 0


class StepperService:
    """STEPPER 服务 (0x30) — 485 总线步进电机（底层 RPC 客户端）"""

    SVC = 0x30

    # GET/SET properties
    PROP_SPEED    = 0x01   # i16 rw  目标速度 (-32000~32000)
    PROP_DISTANCE = 0x02   # i32 r   脉冲距离 (驱动器反馈)
    PROP_ACC      = 0x03   # u16 rw  加减速 (0~32000, 默认 1000)

    # CALL commands
    CALL_STOP  = 0x80      # 速度置 0 (保持力矩)
    CALL_RESET = 0x81      # 复位/释放 (固件阻塞 ~100ms)

    def __init__(self, bot):
        self._bot = bot

    @staticmethod
    def _check_ch(ch: int) -> None:
        if not (1 <= ch <= 3):
            raise ValueError(f"步进通道必须在 1~3 (ST1~ST3), 收到 {ch}")

    # ----- 速度 -----

    def set_speed(self, ch: int, speed: int) -> None:
        """设置目标速度 (-32000~32000)。speed=0 停止 (保持力矩)。
        |speed| < 50 会被驱动器按 0 处理 (SDK 低速死区)。"""
        self._check_ch(ch)
        if not (-STEP_SPD_MAX <= speed <= STEP_SPD_MAX):
            raise ValueError(f"speed 必须在 -{STEP_SPD_MAX}~{STEP_SPD_MAX}, "
                             f"收到 {speed}")
        self._bot._request(
            Op.SET, self.SVC, ch, self.PROP_SPEED,
            value=int(speed).to_bytes(2, "little", signed=True),
            timeout=1.0, retry=2, retry_delay=0.1,
        )

    def get_speed(self, ch: int) -> int:
        """回读最近一次设置的目标速度 (固件侧记录)。"""
        self._check_ch(ch)
        r = self._bot._request(Op.GET, self.SVC, ch, self.PROP_SPEED)
        return int.from_bytes(r.value, "little", signed=True)

    # ----- 距离 -----

    def get_distance(self, ch: int) -> int:
        """读取驱动器反馈的累计脉冲数 (有符号, 方向区分正负)。"""
        self._check_ch(ch)
        r = self._bot._request(
            Op.GET, self.SVC, ch, self.PROP_DISTANCE,
            timeout=0.5, retry=0,  # 快速失败
        )
        return int.from_bytes(r.value, "little", signed=True)

    # ----- 加减速 -----

    def set_acc(self, ch: int, acc: int) -> None:
        """设置加减速 (0~32000, 默认 1000)。值越大加速越快。"""
        self._check_ch(ch)
        acc = max(0, min(STEP_SPD_MAX, int(acc)))
        self._bot._request(
            Op.SET, self.SVC, ch, self.PROP_ACC,
            value=int(acc).to_bytes(2, "little"),
            timeout=1.0, retry=2, retry_delay=0.1,
        )

    def get_acc(self, ch: int) -> int:
        """回读最近一次设置的加减速 (固件侧记录)。"""
        self._check_ch(ch)
        r = self._bot._request(Op.GET, self.SVC, ch, self.PROP_ACC)
        return int.from_bytes(r.value, "little", signed=False)

    # ----- 命令 -----

    def stop(self, ch: int) -> None:
        """停止: 目标速度置 0, 电机保持力矩 (不清距离)。"""
        self._check_ch(ch)
        self._bot._request(
            Op.CALL, self.SVC, ch, self.CALL_STOP,
            timeout=1.0, retry=2, retry_delay=0.1,
        )

    def reset(self, ch: int) -> None:
        """复位/释放: 速度 0 + 驱动器复位指令。
        ⚠️ 固件侧阻塞 ~100ms, 调用方需容忍响应延迟 (SDK 自动重试兜底)。"""
        self._check_ch(ch)
        self._bot._request(
            Op.CALL, self.SVC, ch, self.CALL_RESET,
            timeout=2.0, retry=2, retry_delay=0.3,
        )

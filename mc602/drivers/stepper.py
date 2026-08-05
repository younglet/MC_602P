"""
mc602.drivers.stepper — Stepper (per-instance) 面向对象封装

6 层规范: per-instance 设备对象, 内部委托 StepperService 做 RPC。

用法:
    st = robot.stepper(3)          # 3 号步进通道
    st.set_speed(2000)             # 正转, 脉冲速度
    st.speed = -1500               # property 写法 (反转)
    print(st.distance)             # 读累计脉冲
    st.acc = 2000                  # 调加减速
    st.stop()                      # 停 (保持力矩)
    st.reset()                     # 复位/释放
"""

from __future__ import annotations

from ..services.stepper import StepperService, STEP_SPD_MAX


class Stepper:
    """per-instance 步进电机对象 (ST1~ST3, 485 总线)"""

    def __init__(self, bot, ch):
        from ..drivers.constants import resolve_port, STEPPER_NAMES
        ch = resolve_port(ch, STEPPER_NAMES, "步进通道")
        self._bot = bot
        self._service = bot.stepper if bot is not None else None
        self.ch = ch

    # ----- 速度 -----

    def set_speed(self, speed: int) -> None:
        """设置目标速度 (-32000~32000)。speed=0 停止 (保持力矩)。"""
        self._service.set_speed(self.ch, speed)

    @property
    def speed(self) -> int:
        """回读最近一次目标速度。"""
        return self._service.get_speed(self.ch)

    @speed.setter
    def speed(self, v: int) -> None:
        self.set_speed(v)

    # ----- 距离 -----

    @property
    def distance(self) -> int:
        """驱动器反馈的累计脉冲数 (有符号)。"""
        return self._service.get_distance(self.ch)

    # ----- 加减速 -----

    def set_acc(self, acc: int) -> None:
        """设置加减速 (0~32000, 默认 1000, 越大越快)。"""
        self._service.set_acc(self.ch, acc)

    @property
    def acc(self) -> int:
        """回读最近一次 acc 设置 (固件侧记录)。"""
        return self._service.get_acc(self.ch)

    @acc.setter
    def acc(self, v: int) -> None:
        self.set_acc(v)

    # ----- 命令 -----

    def stop(self) -> None:
        """停止: 速度置 0, 保持力矩 (不清距离)。"""
        self._service.stop(self.ch)

    def reset(self) -> None:
        """复位/释放。⚠️ 固件阻塞 ~100ms。"""
        self._service.reset(self.ch)

    @property
    def is_moving(self) -> bool:
        return self.speed != 0

    def __repr__(self) -> str:
        return f"<Stepper ST{self.ch} speed={self.speed} distance={self.distance}>"

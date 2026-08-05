"""
mc602.drivers.mecanum_chassis — MecanumChassis (薄封装)

运动学/里程计已在固件 200Hz 外环控制器 (SVC 0x04) 实现。
上位机创建时把几何参数 (轴距/轮距/轮径/编码器 PPR) 推给固件,
之后只做指令下发与状态读取。

    car = MecanumChassis(bot, track=30, wheel_base=28, wheel_radius=3)
    car.move(vx=30, vy=0, omega=0.5)       # 车身速度 → 固件逆运动学
    car.goto(x=50, y=0, theta=0)           # 外环去目标位姿
    print(car.pose)                        # 固件里程计
    car.stop()
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..services.mecanum import ChassisService, STATUS_NAMES


@dataclass
class Pose2D:
    """2D pose (cm, rad)."""
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0

    def __repr__(self):
        return (f"Pose2D(x={self.x:.2f}cm, y={self.y:.2f}cm, "
                f"θ={math.degrees(self.theta):.1f}°)")


class MecanumChassis:
    """Mecanum 车 — 固件外环控制器客户端。

    Args:
        bot:          MC602 instance
        ports:        4 motor ports (固件固定使用 M1~M4, 保留兼容参数)
        track:        左右轮距 (cm)
        wheel_base:   前后轴距 (cm)
        wheel_radius: 轮半径 (cm)
        encoder_ppr:  每圈编码器脉冲 (默认 2048)
        roller_adjust: 辊子角度校准系数 (默认 1.052)
    """

    def __init__(self, bot, *,
                 ports: tuple = (1, 2, 3, 4),
                 track: float = 30.0,
                 wheel_base: float = 28.0,
                 wheel_radius: float = 3.0,
                 encoder_ppr: int = 2048,
                 roller_adjust: float = 1.052):
        if tuple(ports) != (1, 2, 3, 4):
            raise ValueError("固件外环固定使用 M1~M4, ports 参数已由固件接管")
        self._bot = bot
        self._service = bot.chassis if bot is not None else None
        self._geom = {
            "track": track, "wheel_base": wheel_base,
            "wheel_radius": wheel_radius,
            "encoder_ppr": encoder_ppr, "roller_adjust": roller_adjust,
        }
        # 创建即推送几何参数到下位机
        if self._service is not None:
            self._service.set_geometry(
                track=track, wheel_base=wheel_base,
                wheel_radius=wheel_radius, encoder_ppr=encoder_ppr,
                roller_adjust=roller_adjust,
            )

    # ── 控制 ──────────────────────────────────────────

    def move(self, vx: float = 0.0, vy: float = 0.0,
             omega: float = 0.0) -> None:
        """车身速度控制 (cm/s, rad/s)。固件逆运动学 → 4 轮。"""
        self._service.move(vx, vy, omega)

    def goto(self, x: float, y: float, theta: float = 0.0,
             max_speed: int = 80) -> None:
        """外环: 运动到目标位姿 (cm, rad)。到达后 state=ARRIVED。"""
        self._service.goto(x, y, theta, max_speed)

    def stop(self) -> None:
        self._service.move(0, 0, 0)

    def abort(self) -> None:
        """中止当前运动, 停车。"""
        self._service.abort()

    def emergency_stop(self) -> None:
        self._service.emergency_stop()

    # ── 状态 ──────────────────────────────────────────

    def update(self) -> Pose2D:
        """读固件里程计位姿。返回当前 pose (固件计算)。"""
        p = self._service.get_pose()
        return Pose2D(p["x"], p["y"], p["theta"])

    @property
    def pose(self) -> Pose2D:
        return self.update()

    @property
    def distance(self) -> float:
        """总里程 (cm)。"""
        return self._service.get_stats()["distance_cm"]

    @property
    def status(self) -> str:
        """状态名 (IDLE/RUNNING/ARRIVED/...)。"""
        st = self._service.get_status()
        return STATUS_NAMES.get(st["state"], f"UNKNOWN({st['state']})")

    def wait_arrived(self, poll_interval: float = 0.05,
                     timeout: float = 15.0) -> str:
        """轮询直到 ARRIVED/ABORTED/TIMED_OUT。返回状态名。"""
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            name = self.status
            if name in ("ARRIVED", "ABORTED", "TIMED_OUT", "EMERGENCY"):
                return name
            time.sleep(poll_interval)
        return "TIMED_OUT"

    # ── 里程计 ────────────────────────────────────────

    def reset_pose(self, x=0.0, y=0.0, theta=0.0) -> None:
        """里程计归零。固件仅支持归零 (0,0,0), 非零参数抛错。"""
        if (x, y, theta) != (0.0, 0.0, 0.0):
            raise ValueError("固件外环仅支持里程计归零 (0,0,0); "
                             "任意位姿需用 goto()")
        self._service.reset_odom()

    # ── 参数 ──────────────────────────────────────────

    def set_pid(self, kp_rho: float = 1.5, kp_alpha: float = 2.5,
                kp_beta: float = 0.8) -> None:
        """极坐标 P-controller 参数 (下位机)。"""
        self._service.set_pid(kp_rho, kp_alpha, kp_beta)

    def set_tolerance(self, pos_cm: float = 2.0, ang_deg: float = 3.0) -> None:
        self._service.set_tolerance(pos_cm, ang_deg)

    def set_max_vel(self, v_cm_s: float = 40.0, w_deg_s: float = 90.0) -> None:
        self._service.set_max_vel(v_cm_s, w_deg_s)

    def set_timeout(self, ms: int = 10000) -> None:
        self._service.set_timeout(ms)

    @property
    def geometry(self) -> dict:
        return dict(self._geom)

    def __repr__(self) -> str:
        return (f"<MecanumChassis {self._geom['track']}x"
                f"{self._geom['wheel_base']}cm r="
                f"{self._geom['wheel_radius']}cm {self.status}>")

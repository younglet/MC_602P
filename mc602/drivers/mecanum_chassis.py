"""
mc602.drivers.mecanum_chassis — MecanumChassis

Top-level: Motors (RPC) + MecanumMotion (math).

    chassis = MecanumChassis(bot, ports=(3,1,4,2), track=30, base=28, r=3)
    chassis.move(vx=30, vy=0, omega=0.5)
    chassis.stop()
    chassis.update()
    print(chassis.pose)
"""

from __future__ import annotations
from .motors import Motors
from ..motion.mecanum import MecanumMotion, WheelSpeeds, BodyVelocity, Pose2D


class MecanumChassis:
    """Mecanum car — RPC + kinematics + odometry.

    Args:
        bot:          MC602 instance
        ports:        4 motor ports in order (FL, FR, RL, RR)
        track:        left-right distance (cm)
        wheel_base:   front-rear distance (cm)
        wheel_radius: wheel radius (cm)
        encoder_ppr:  pulses per revolution
    """

    def __init__(self, bot, *,
                 ports: tuple = (1, 2, 3, 4),
                 track: float = 30.0,
                 wheel_base: float = 28.0,
                 wheel_radius: float = 3.0,
                 encoder_ppr: int = 2048):
        """Mecanum car.

        Args:
            bot:          MC602 instance
            ports:        4 motor ports in order (FL, FR, RL, RR)
            track:        left-right distance (cm)
            wheel_base:   front-rear distance (cm)
            wheel_radius: wheel radius (cm)
            encoder_ppr:  pulses per wheel revolution.
                          Common: N20=210, TT霍尔=260/390, AB相512线×4=2048.
                          !! 必须与实际电机匹配, 不然里程计角度会放大 N 倍 !!
        """
        self._chassis = Motors(bot, ports)
        self._motion = MecanumMotion(
            track=track, wheel_base=wheel_base,
            wheel_radius=wheel_radius, encoder_ppr=encoder_ppr,
        )

    # ── control ──────────────────────────────────────────

    def move(self, vx: float = 0.0, vy: float = 0.0,
             omega: float = 0.0) -> None:
        """Body velocity (cm/s, rad/s) → set all 4 motors."""
        w = self._motion.inverse(vx, vy, omega)
        self._chassis.set_speeds(*w.to_motor())

    def stop(self) -> None:
        self._chassis.stop()

    # ── odometry ─────────────────────────────────────────

    def update(self) -> Pose2D:
        """Read encoders → update odometry. Returns current pose."""
        encoders = self._chassis.get_encoders()
        return self._motion.update_odometry(*encoders)

    @property
    def pose(self) -> Pose2D:
        return self._motion.pose

    @property
    def distance(self) -> float:
        return self._motion.total_distance

    def reset_pose(self, x=0.0, y=0.0, theta=0.0) -> None:
        self._motion.reset_pose(x, y, theta)

    # ── direct access ────────────────────────────────────

    @property
    def motion(self) -> MecanumMotion:
        return self._motion

    @property
    def chassis(self) -> Motors:
        return self._chassis

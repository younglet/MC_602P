"""
mc602.motion.mecanum — Mecanum kinematics + odometry (pure math)

No RPC, no mc602 imports — unit-testable in isolation.

    m = MecanumMotion(track=30, wheel_base=28, wheel_radius=3, encoder_ppr=2048)
    w = m.inverse(vx=30, vy=0, omega=0.5)       # body → wheels (cm/s)
    b = m.forward(w)                              # wheels → body
    m.update_odometry(e1, e2, e3, e4)             # encoder → pose
    print(m.pose)                                 # Pose2D(x=..., y=..., θ=...)
"""

from __future__ import annotations
import math
import numpy as np
from dataclasses import dataclass


@dataclass
class WheelSpeeds:
    """Wheel linear speeds (cm/s). CW = positive."""
    m1: float = 0.0
    m2: float = 0.0
    m3: float = 0.0
    m4: float = 0.0

    def to_tuple(self):
        return (self.m1, self.m2, self.m3, self.m4)

    def to_motor(self, max_linear: float = 60.0) -> tuple:
        """Convert to motor commands (-100~+100)."""
        def clamp(v):
            return max(-100, min(100, int(v / max_linear * 100)))
        return (clamp(self.m1), clamp(self.m2),
                clamp(self.m3), clamp(self.m4))


@dataclass
class BodyVelocity:
    """Body-frame velocity (cm/s, rad/s)."""
    vx: float = 0.0
    vy: float = 0.0
    omega: float = 0.0


@dataclass
class Pose2D:
    """2D pose (cm, rad)."""
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0

    def __repr__(self):
        return (f"Pose2D(x={self.x:.2f}cm, y={self.y:.2f}cm, "
                f"θ={math.degrees(self.theta):.1f}°)")


class MecanumMotion:
    """Mecanum kinematics + odometry (pure math).

    Args:
        track:       left-right wheel distance (cm)
        wheel_base:  front-rear wheel distance (cm)
        wheel_radius: wheel radius (cm)
        encoder_ppr: pulses per wheel revolution
        roller_adjust: roller angle calibration (default 1.052)
    """

    def __init__(self, track: float = 30.0, wheel_base: float = 28.0,
                 wheel_radius: float = 3.0, encoder_ppr: int = 1,
                 roller_adjust: float = 1.052):
        # -- kinematics matrices --
        roller_angle = math.pi / 4 * roller_adjust
        self._tan_r = math.tan(roller_angle)
        self._wc = (track / 2) * self._tan_r + (wheel_base / 2)

        t, wc = self._tan_r, self._wc
        self._M_fwd = np.array([
            [ 1/4,  1/(4*t),  1/(4*wc)],
            [-1/4,  1/(4*t),  1/(4*wc)],
            [-1/4, -1/(4*t),  1/(4*wc)],
            [ 1/4, -1/(4*t),  1/(4*wc)],
        ])
        self._M_inv = np.array([
            [  1,  -1,  -1,   1],
            [  t,   t,  -t,  -t],
            [ wc,  wc,  wc,  wc],
        ])

        # -- encoder → distance --
        self._enc_to_dist = (2 * math.pi * wheel_radius) / encoder_ppr \
            if encoder_ppr > 0 else 0

        # -- odometry state --
        self._pose = Pose2D()
        self._last_enc = (0, 0, 0, 0)
        self.total_distance = 0.0

    # ═══ kinematics ═══════════════════════════════════════

    def inverse(self, vx=0.0, vy=0.0, omega=0.0) -> WheelSpeeds:
        """Body velocity (cm/s, rad/s) → wheel linear speeds (cm/s)."""
        body = np.array([vx, vy, omega])
        wheels = body @ self._M_inv
        return WheelSpeeds(*wheels)

    def forward(self, w: WheelSpeeds) -> BodyVelocity:
        """Wheel speeds → body velocity."""
        wv = np.array([w.m1, w.m2, w.m3, w.m4])
        body = wv @ self._M_fwd
        return BodyVelocity(float(body[0]), float(body[1]), float(body[2]))

    # ═══ odometry ════════════════════════════════════════

    def update_odometry(self, e1: int, e2: int, e3: int, e4: int) -> Pose2D:
        """Encoder values → update pose. Returns current pose."""
        prev = self._last_enc
        d1 = e1 - prev[0]
        d2 = e2 - prev[1]
        d3 = e3 - prev[2]
        d4 = e4 - prev[3]
        self._last_enc = (e1, e2, e3, e4)

        # encoder delta → wheel distance (cm)
        w = WheelSpeeds(
            self._enc_to_dist * d1, self._enc_to_dist * d2,
            self._enc_to_dist * d3, self._enc_to_dist * d4)
        body = self.forward(w)

        # integrate into world frame
        cos_t = math.cos(self._pose.theta)
        sin_t = math.sin(self._pose.theta)
        self._pose.x += body.vx * cos_t - body.vy * sin_t
        self._pose.y += body.vx * sin_t + body.vy * cos_t
        self._pose.theta += body.omega
        self._pose.theta = math.atan2(
            math.sin(self._pose.theta), math.cos(self._pose.theta))
        self.total_distance += math.sqrt(body.vx**2 + body.vy**2)

        return self._pose

    @property
    def pose(self) -> Pose2D:
        return self._pose

    def reset_pose(self, x=0.0, y=0.0, theta=0.0) -> None:
        self._pose = Pose2D(x, y, theta)
        self._last_enc = (0, 0, 0, 0)
        self.total_distance = 0.0

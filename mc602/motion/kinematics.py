"""
mc602.motion.kinematics — Mecanum wheel kinematics

Forward:  wheel speeds → body velocity (m/s, rad/s)
Inverse:  body velocity → wheel speeds (m/s)

Based on the physical roller-angle model (same as baidu_smartcar_2026).
Default parameters match the MC602P mecanum car.

Wheel layout (top view, X-shaped rollers, O-shaped ground contact):
        +x (forward)
         ▲
    M1   │   M2    ← front
    ◄┼───┼───┼►
         │
    M3   │   M4    ← rear
    ◄┼───┼───┼►
         │
         └──────► +y (right)

Reference: baidu_smartcar_2026/smartcar/whalesbot/vehicle/driver/mecanum.py
"""

from __future__ import annotations
import math
import numpy as np
from dataclasses import dataclass
from typing import Tuple


@dataclass
class WheelSpeeds:
    """Wheel linear speeds (m/s). CW = positive."""
    m1: float   # front-left
    m2: float   # front-right
    m3: float   # rear-left
    m4: float   # rear-right

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.m1, self.m2, self.m3, self.m4)

    def to_motor(self, max_linear: float = 0.6) -> Tuple[int, int, int, int]:
        """Convert to motor commands (-100~+100)."""
        def clamp(v):
            return max(-100, min(100, int(v / max_linear * 100)))
        return (clamp(self.m1), clamp(self.m2),
                clamp(self.m3), clamp(self.m4))


@dataclass
class BodyVelocity:
    """Body-frame velocity (m/s, rad/s)."""
    vx: float     # forward  (m/s)
    vy: float     # right    (m/s)
    omega: float  # CCW      (rad/s)


class MecanumKinematics:
    """Mecanum wheel kinematics — physical roller-angle model.

    Args:
        track:       distance between left and right wheels (m)
        wheel_base:  distance between front and rear wheels (m)
        wheel_radius: wheel radius (m)
        roller_adjust: roller angle calibration factor (default 1.052)
        encoder_ppr: encoder pulses per wheel revolution
    """

    def __init__(self,
                 track: float = 0.30,        # 轮距
                 wheel_base: float = 0.28,   # 轴距
                 wheel_radius: float = 0.03,  # 轮半径
                 roller_adjust: float = 1.052,
                 encoder_ppr: int = 1):
        self.track = track
        self.wheel_base = wheel_base
        self.radius = wheel_radius
        self.encoder_ppr = encoder_ppr

        # Mecanum roller angle (~45°)
        roller_angle = math.pi / 4 * roller_adjust
        self._tan_roller = math.tan(roller_angle)
        half_track = track / 2
        half_base = wheel_base / 2
        self._wheel_const = half_track * self._tan_roller + half_base

        # Forward: wheel velocity → body velocity  (4×3)
        t = self._tan_roller
        wc = self._wheel_const
        self._M_fwd = np.array([
            [ 1/4,  1/(4*t),  1/(4*wc)],
            [-1/4,  1/(4*t),  1/(4*wc)],
            [-1/4, -1/(4*t),  1/(4*wc)],
            [ 1/4, -1/(4*t),  1/(4*wc)],
        ])

        # Inverse: body velocity → wheel velocity  (3×4)
        self._M_inv = np.array([
            [  1,  -1,  -1,   1],
            [  t,   t,  -t,  -t],
            [ wc,  wc,  wc,  wc],
        ])

        # encoder → revolution → distance
        self._enc_to_rev = (2.0 * math.pi * wheel_radius) / encoder_ppr \
            if encoder_ppr > 0 else 0

    # ── unit conversion ────────────────────────────────

    def enc_to_dist(self, delta: int) -> float:
        """Encoder delta → wheel distance traveled (m)."""
        return self._enc_to_rev * delta

    # ── forward kinematics (wheels → body) ─────────────

    def forward(self, w: WheelSpeeds) -> BodyVelocity:
        """Wheel linear speeds (m/s) → body velocity (m/s, rad/s).

        Wheel ordering matches the layout: [m1(FL), m2(FR), m3(RL), m4(RR)].
        CW = positive.
        """
        wv = np.array([w.m1, w.m2, w.m3, w.m4])
        body = wv @ self._M_fwd
        return BodyVelocity(vx=float(body[0]), vy=float(body[1]),
                            omega=float(body[2]))

    def forward_enc(self, d1: int, d2: int, d3: int, d4: int) -> BodyVelocity:
        """Encoder deltas → body displacement (m, m, rad)."""
        w = WheelSpeeds(
            self.enc_to_dist(d1), self.enc_to_dist(d2),
            self.enc_to_dist(d3), self.enc_to_dist(d4))
        return self.forward(w)

    # ── inverse kinematics (body → wheels) ─────────────

    def inverse(self, vx: float = 0.0, vy: float = 0.0,
                omega: float = 0.0) -> WheelSpeeds:
        """Body velocity (m/s, rad/s) → wheel linear speeds (m/s)."""
        body = np.array([vx, vy, omega])
        wheels = body @ self._M_inv  # 3×4 → 1×4
        return WheelSpeeds(
            float(wheels[0]), float(wheels[1]),
            float(wheels[2]), float(wheels[3]))

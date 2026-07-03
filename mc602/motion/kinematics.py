"""
mc602.motion.kinematics — Mecanum wheel kinematics

Forward:  wheel speeds → body velocity
Inverse:  body velocity → wheel speeds

Reference:
  M1 (front-left)    M2 (front-right)
         ▲  ▲              ▲  ▲
         │  │              │  │
  ───────┼──┼──────────────┼──┼───────
         │  │              │  │
         ▼  ▼              ▼  ▼
  M3 (rear-left)     M4 (rear-right)

Wheel layout:
        +y (forward)
         ▲
    M1   │   M2
    ◄┼───┼───┼►
         │
    M3   │   M4
    ◄┼───┼───┼►
         │
         └──────► +x (right)
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Tuple


@dataclass
class WheelSpeeds:
    """Normalized wheel speeds (-1.0 ~ +1.0)"""
    m1: float   # front-left
    m2: float   # front-right
    m3: float   # rear-left
    m4: float   # rear-right

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.m1, self.m2, self.m3, self.m4)

    def to_motor(self) -> Tuple[int, int, int, int]:
        """Convert to motor commands (-100 ~ +100)"""
        def clamp(v):
            return max(-100, min(100, int(v * 100)))
        return (clamp(self.m1), clamp(self.m2),
                clamp(self.m3), clamp(self.m4))


@dataclass
class BodyVelocity:
    """Body-frame velocity"""
    vx: float     # m/s  forward
    vy: float     # m/s  right
    omega: float  # rad/s CCW


class MecanumKinematics:
    """Mecanum wheel kinematics.

    Args:
        wheel_radius: wheel radius in meters
        lx: half wheelbase X (distance from center to wheel, m)
        ly: half wheelbase Y (m)
        encoder_ppr: encoder pulses per wheel revolution
    """

    def __init__(self, wheel_radius: float = 0.034,
                 lx: float = 0.10, ly: float = 0.12,
                 encoder_ppr: int = 1):
        self.r = wheel_radius
        self.lx = lx
        self.ly = ly
        self.l_sum = lx + ly
        self.encoder_ppr = encoder_ppr
        # encoder → rad: 2π / ppr
        self._enc_to_rad = (2.0 * math.pi) / encoder_ppr if encoder_ppr > 0 else 0

    # ── unit scale ──────────────────────────────────────

    def norm_to_rads(self, norm: float) -> float:
        """Normalized speed (-1~+1) → rad/s"""
        return norm * 100  # approximate: norm*100 maps to motor PWM

    def rads_to_ms(self, rads: float) -> float:
        """Wheel angular velocity (rad/s) → linear (m/s)"""
        return rads * self.r

    def encoder_delta_to_dist(self, delta: int) -> float:
        """Encoder delta → distance traveled (m)"""
        return self._enc_to_rad * self.r * delta

    # ── inverse kinematics (body → wheels) ──────────────

    def inverse(self, vx: float = 0.0, vy: float = 0.0,
                omega: float = 0.0) -> WheelSpeeds:
        """Body velocity → normalized wheel speeds (-1~+1).

        Inverse kinematics:
          m1 = vx - vy - (lx+ly)*ω
          m2 = vx + vy + (lx+ly)*ω
          m3 = vx + vy - (lx+ly)*ω
          m4 = vx - vy + (lx+ly)*ω
        """
        ls = self.l_sum
        m1 = vx - vy - ls * omega
        m2 = vx + vy + ls * omega
        m3 = vx + vy - ls * omega
        m4 = vx - vy + ls * omega

        # normalize to -1 ~ +1
        max_w = max(abs(m1), abs(m2), abs(m3), abs(m4))
        if max_w > 1.0:
            m1 /= max_w
            m2 /= max_w
            m3 /= max_w
            m4 /= max_w

        return WheelSpeeds(m1, m2, m3, m4)

    def inverse_ms(self, vx_ms: float = 0.0, vy_ms: float = 0.0,
                   omega_rads: float = 0.0) -> WheelSpeeds:
        """Body velocity (m/s, rad/s) → normalized wheel speeds."""
        # convert to normalized body velocity first
        vx = vx_ms
        vy = vy_ms
        omega = omega_rads
        return self.inverse(vx, vy, omega)

    # ── forward kinematics (wheels → body) ──────────────

    def forward(self, w: WheelSpeeds) -> BodyVelocity:
        """Normalized wheel speeds → body velocity.

        Forward kinematics:
          vx = (m1 + m2 + m3 + m4) / 4
          vy = (-m1 + m2 + m3 - m4) / 4
          ω  = (-m1 + m2 - m3 + m4) / (4*(lx+ly))
        """
        vx = (w.m1 + w.m2 + w.m3 + w.m4) / 4.0
        vy = (-w.m1 + w.m2 + w.m3 - w.m4) / 4.0
        omega = (-w.m1 + w.m2 - w.m3 + w.m4) / (4.0 * self.l_sum)
        return BodyVelocity(vx, vy, omega)

    def forward_enc(self, d1: int, d2: int, d3: int, d4: int) -> BodyVelocity:
        """Encoder deltas → body displacement (m, m, rad)."""
        s1 = self.encoder_delta_to_dist(d1)
        s2 = self.encoder_delta_to_dist(d2)
        s3 = self.encoder_delta_to_dist(d3)
        s4 = self.encoder_delta_to_dist(d4)

        dx = ( s1 + s2 + s3 + s4) / 4.0
        dy = (-s1 + s2 + s3 - s4) / 4.0
        dtheta = (-s1 + s2 - s3 + s4) / (4.0 * self.l_sum)
        return BodyVelocity(dx, dy, dtheta)

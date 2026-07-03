"""
mc602.motion.odometry — Dead-reckoning odometry

Integrates encoder deltas into a 2D pose (x, y, θ) using
MecanumKinematics.forward_enc().

Usage:
    kin = MecanumKinematics(encoder_ppr=2048)
    odo = Odometry(kin)

    while True:
        e1, e2, e3, e4 = bot.mecanum.get_encoders()
        odo.update(e1, e2, e3, e4, dt=0.1)
        x, y, theta = odo.pose
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from .kinematics import MecanumKinematics


@dataclass
class Pose2D:
    """2D pose in world frame"""
    x: float = 0.0       # meters
    y: float = 0.0       # meters
    theta: float = 0.0   # radians (-π ~ +π)

    def __repr__(self):
        return (f"Pose2D(x={self.x:.4f}, y={self.y:.4f}, "
                f"θ={math.degrees(self.theta):.1f}°)")

    def to_tuple(self):
        return (self.x, self.y, self.theta)


class Odometry:
    """Track robot pose from encoder deltas.

    Args:
        kinematics: MecanumKinematics instance
        pose0: initial pose (default: origin)
    """

    def __init__(self, kinematics: MecanumKinematics,
                 pose0: Pose2D | None = None):
        self.kin = kinematics
        self.pose = pose0 or Pose2D()
        self._last_enc = (0, 0, 0, 0)
        self.total_distance = 0.0  # total distance traveled (m)

    def reset(self, pose: Pose2D | None = None) -> None:
        """Reset odometry to given pose (default: origin)."""
        self.pose = pose or Pose2D()
        self._last_enc = (0, 0, 0, 0)
        self.total_distance = 0.0

    def update(self, enc1: int, enc2: int, enc3: int, enc4: int,
               dt: float | None = None) -> Pose2D:
        """Update pose from new encoder readings.

        Args:
            enc1..enc4: absolute encoder values
            dt: time since last update (unused, kept for API compat)
        Returns:
            updated Pose2D
        """
        prev = self._last_enc
        d1 = enc1 - prev[0]
        d2 = enc2 - prev[1]
        d3 = enc3 - prev[2]
        d4 = enc4 - prev[3]
        self._last_enc = (enc1, enc2, enc3, enc4)

        # encoder deltas → body displacement
        body = self.kin.forward_enc(d1, d2, d3, d4)

        # integrate into world frame
        theta = self.pose.theta
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        # 1st-order integration
        self.pose.x += body.vx * cos_t - body.vy * sin_t
        self.pose.y += body.vx * sin_t + body.vy * cos_t
        self.pose.theta += body.omega

        # wrap angle
        self.pose.theta = math.atan2(
            math.sin(self.pose.theta), math.cos(self.pose.theta))

        # total distance
        self.total_distance += math.sqrt(body.vx ** 2 + body.vy ** 2)

        return self.pose

    @property
    def x(self) -> float:
        return self.pose.x

    @property
    def y(self) -> float:
        return self.pose.y

    @property
    def theta(self) -> float:
        return self.pose.theta

    @property
    def theta_deg(self) -> float:
        return math.degrees(self.pose.theta)

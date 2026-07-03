"""
mc602.motion.coordinate — 2D coordinate transforms

World frame ↔ robot frame, transform chaining.
Uses homogeneous 2D transforms (SE2).

    from mc602.motion.coordinate import Transform2D

    world_to_robot = Transform2D(x=1.0, y=2.0, theta=0.5)
    robot_point = (0.3, 0.4)
    world_point = world_to_robot.apply(robot_point)
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from .mecanum import BodyVelocity, Pose2D


@dataclass
class Transform2D:
    """2D rigid transform (translation in cm, rotation in rad)."""
    x: float = 0.0   # cm
    y: float = 0.0   # cm
    theta: float = 0.0  # radians

    @classmethod
    def from_pose(cls, pose: Pose2D) -> "Transform2D":
        return cls(pose.x, pose.y, pose.theta)

    @classmethod
    def identity(cls) -> "Transform2D":
        return cls()

    def apply(self, px: float, py: float) -> tuple[float, float]:
        """Transform a point from this frame to parent frame."""
        cos_t = math.cos(self.theta)
        sin_t = math.sin(self.theta)
        x = self.x + px * cos_t - py * sin_t
        y = self.y + px * sin_t + py * cos_t
        return (x, y)

    def apply_pose(self, pose: Pose2D) -> Pose2D:
        """Transform a pose."""
        nx, ny = self.apply(pose.x, pose.y)
        return Pose2D(nx, ny, self.theta + pose.theta)

    def apply_velocity(self, vel: BodyVelocity) -> BodyVelocity:
        """Transform body-frame velocity to world frame."""
        cos_t = math.cos(self.theta)
        sin_t = math.sin(self.theta)
        return BodyVelocity(
            vx=vel.vx * cos_t - vel.vy * sin_t,
            vy=vel.vx * sin_t + vel.vy * cos_t,
            omega=vel.omega,
        )

    def inverse(self) -> "Transform2D":
        """Inverse transform (parent → this frame)."""
        cos_t = math.cos(-self.theta)
        sin_t = math.sin(-self.theta)
        nx = -self.x * cos_t - self.y * sin_t
        ny =  self.x * sin_t - self.y * cos_t
        return Transform2D(nx, ny, -self.theta)

    def compose(self, other: "Transform2D") -> "Transform2D":
        """Compose two transforms: self ∘ other (apply other after self)."""
        nx, ny = self.apply(other.x, other.y)
        return Transform2D(nx, ny, self.theta + other.theta)

    def __repr__(self):
        return (f"Transform2D(x={self.x:.2f}cm, y={self.y:.2f}cm, "
                f"θ={math.degrees(self.theta):.1f}°)")

    def to_tuple(self):
        return (self.x, self.y, self.theta)

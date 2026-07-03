"""
mc602.services — 底层 Service RPC 客户端（薄包装）

每个 Service 一个文件，封装 GET/SET/CALL 请求。
设计上保持和下位机 device/devices/services.c 的 ProtoHandler 一一对应。
"""

from .motor import MotorService
from .system import SystemService

__all__ = ["MotorService", "SystemService"]

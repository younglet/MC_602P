"""
异常体系
========

所有 SDK 抛出的异常都继承自 :class:`MC602Error`，方便上层捕获。
"""

from __future__ import annotations


class MC602Error(Exception):
    """SDK 基础异常"""


# 历史别名 (旧名 WhalesBotError = 新名 MC602Error)
WhalesBotError = MC602Error


class ConnectionError(MC602Error):
    """串口连接失败 (打不开/断开)"""


class SerialNotFoundError(ConnectionError):
    """没找到 CH340 设备 (未插入或驱动未装)"""


class ProtocolError(MC602Error):
    """协议解析失败 (CRC 错/帧头错/长度异常)"""


class TimeoutError(MC602Error):  # noqa: A001  (重名 builtin 但语义不同)
    """指令超时 (下位机未在指定时间内响应)"""


class VerificationError(MC602Error):
    """固件指纹校验失败, 且 auto_flash=False"""


class FlashError(MC602Error):
    """固件烧录失败 (BootLoader 协议错误)"""

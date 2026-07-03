"""
mc602.comm — 通讯子模块 (Layer 2: Transport + Layer 3: Packet)

对外暴露:
    客户端:     MC602, find_ch340_port
    帧格式:     Op, Status, Payload
    编/解码:    encode_frame, try_decode_frame
    COBS:       cobs_encode, cobs_decode
    CRC8:       crc8

与下位机 firmware/protocol/ + firmware/core/dispatcher.c 严格对齐。

用法:
    from mc602.comm import MC602, Op, Status, Payload
    from mc602.comm import crc8, cobs_encode
"""

from .client import (
    CH340_PID_ALT,
    CH340_PID_PRIMARY,
    CH340_VID,
    MC602,
    find_ch340_port,
)
from .cobs import cobs_decode, cobs_encode
from .crc8 import CRC8, crc8
from .packet import (
    Command,
    FrameType,
    Op,
    Payload,
    Status,
    encode_frame,
    encode_response_frame,
    try_decode_frame,
)

__all__ = [
    # 客户端
    "MC602", "find_ch340_port",
    "CH340_VID", "CH340_PID_PRIMARY", "CH340_PID_ALT",
    # CRC
    "crc8", "CRC8",
    # COBS
    "cobs_encode", "cobs_decode",
    # 操作 / 状态
    "Op", "Status", "FrameType", "Command",
    # Payload
    "Payload",
    # 帧
    "encode_frame", "encode_response_frame", "try_decode_frame",
]

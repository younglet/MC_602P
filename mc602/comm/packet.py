"""
packet.py — 帧格式 + Payload 编/解码

帧格式 (HOST <-> MCU):
    [COBS(payload)]  [0x00 DELIMITER]  [CRC8(payload)]

Payload 格式 (HOST -> MCU):
    [seq:u8] [op:u8] [svc:u8] [inst:u8] [prop:u8] [value...]

Payload 格式 (MCU -> HOST 响应):
    [seq:u8] [op:u8] [svc:u8] [inst:u8] [prop:u8] [status:u8] [value...]

    seq    与请求一致 (主动推送为 0)
    op     回显请求的 op
    status 0=OK 1=NOT_FOUND 2=READ_ONLY 3=RANGE_ERR 4=TIMEOUT 5=HW_ERR

与下位机 firmware/core/dispatcher.c 严格对齐。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from .cobs import cobs_decode, cobs_encode
from .crc8 import crc8


# =========================================================================
# 操作码 / 状态码
# =========================================================================

class Op(IntEnum):
    DISCOVER = 0x00
    GET      = 0x01
    SET      = 0x02
    NOTIFY   = 0x03
    CALL     = 0x04
    ERROR    = 0x7F


class Status(IntEnum):
    OK         = 0x00
    NOT_FOUND  = 0x01
    READ_ONLY  = 0x02
    RANGE_ERR  = 0x03
    TIMEOUT    = 0x04
    HW_ERR     = 0x05


# 历史别名（早期版本叫 FrameType / Command，实际就是 Op）
FrameType = Op
Command   = Op


# =========================================================================
# Payload
# =========================================================================

@dataclass
class Payload:
    """协议层 payload (frame 解码后的内容)"""
    seq:    int                # 序号 (1~127, 0 是 NOTIFY 主动推送的固定值)
    op:     Op
    svc:    int
    inst:   int
    prop:   int
    status: Status = Status.OK   # 仅响应 / NOTIFY 有 status
    value:  bytes  = b""          # 数据段

    def encode(self) -> bytes:
        """编码请求 payload (无 status)"""
        return bytes([self.seq & 0xFF,
                      int(self.op) & 0xFF,
                      self.svc & 0xFF,
                      self.inst & 0xFF,
                      self.prop & 0xFF]) + bytes(self.value)

    def encode_response(self) -> bytes:
        """编码响应 payload (含 status 字节)"""
        return bytes([self.seq & 0xFF,
                      int(self.op) & 0xFF,
                      self.svc & 0xFF,
                      self.inst & 0xFF,
                      self.prop & 0xFF,
                      int(self.status) & 0xFF]) + bytes(self.value)

    @classmethod
    def decode(cls, raw: bytes | bytearray) -> "Payload":
        """
        解码响应 payload。响应一定有 status 字段 (第 6 字节)。
        """
        if len(raw) < 5:
            raise ValueError(f"payload too short: {len(raw)} < 5")
        return cls(
            seq    = raw[0],
            op     = Op(raw[1]),
            svc    = raw[2],
            inst   = raw[3],
            prop   = raw[4],
            status = Status(raw[5]),
            value  = bytes(raw[6:]),
        )


# =========================================================================
# 帧级编/解码 (raw bytes in/out)
# =========================================================================

def encode_frame(payload: Payload) -> bytes:
    """
    编码一个完整帧: payload -> COBS + 0x00 + CRC8
    """
    raw = payload.encode()
    return cobs_encode(raw) + bytes([0x00, crc8(raw)])


def encode_response_frame(payload: Payload) -> bytes:
    """编码响应帧 (payload 含 status)。用于上位机侧的手动构造 / 测试。"""
    raw = payload.encode_response()
    return cobs_encode(raw) + bytes([0x00, crc8(raw)])


def try_decode_frame(buf: bytearray) -> Optional[Payload]:
    """
    尝试从一个字节缓冲区中解析出最前面的一帧。
    返回: 解析成功返回 Payload, 否则 None (需要更多字节 / 帧不完整 / 校验失败)

    查找 0x00 分隔符; 必须有 0x00 之后至少 1 字节 (CRC8)。
    """
    # 找第一个 0x00
    try:
        delim = bytes(buf).index(0x00)
    except ValueError:
        return None
    if delim + 1 >= len(buf):
        # 帧不完整, 等 CRC 字节
        return None

    cobs_bytes = bytes(buf[:delim])
    expected_crc = buf[delim + 1]

    # COBS 解码
    payload = cobs_decode(cobs_bytes)
    if not payload and cobs_bytes not in (b"\x01",):
        # 解码失败 (但 cobs_bytes==0x01 是合法空 payload)
        return None

    # CRC8 校验
    actual_crc = crc8(payload)
    if actual_crc != expected_crc:
        return None

    # 解析 Payload
    try:
        p = Payload.decode(payload)
    except (ValueError, IndexError):
        return None
    return p


__all__ = [
    # Op / Status
    "Op", "Status", "FrameType", "Command",
    # Payload
    "Payload",
    # 帧
    "encode_frame", "encode_response_frame", "try_decode_frame",
]

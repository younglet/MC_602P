"""
cobs.py — Consistent Overhead Byte Stuffing (COBS) 编解码

保证编码后的数据不含 0x00, 用 0x00 作帧分隔符。
编码最大开销 +1 字节（254 字节数据 → 255 字节编码）。

与下位机 firmware/protocol/cobs.c 完全对应 (byte-level identical)。

用法:
    from mc602.comm import cobs_encode, cobs_decode
    encoded = cobs_encode(payload_bytes)   # 不含 0x00
    decoded = cobs_decode(encoded_bytes)   # 还原
"""

from __future__ import annotations

from typing import Union


def cobs_encode(data: Union[bytes, bytearray]) -> bytes:
    """
    COBS 编码。返回的字节流不含 0x00, 可用 0x00 作帧分隔符。
    与 firmware/protocol/cobs.c 中的 cobs_encode() 完全对应。
    """
    if not data:
        return bytes([0x01])

    out = bytearray()
    code_idx = 0
    code = 1
    out.append(0)  # 占位 (code_idx = 0)

    for b in data:
        if b == 0x00:
            out[code_idx] = code
            code_idx = len(out)
            out.append(0)  # 下一组 code 的占位
            code = 1
        else:
            out.append(b)
            code += 1
            if code == 0xFF:
                out[code_idx] = code
                code_idx = len(out)
                out.append(0)  # 下一组 code 的占位
                code = 1

    out[code_idx] = code
    return bytes(out)


def cobs_decode(data: Union[bytes, bytearray]) -> bytes:
    """
    COBS 解码。输入不能含 0x00 (那是帧分隔符)。
    与 firmware/protocol/cobs.c 中的 cobs_decode() 完全对应。
    """
    if not data:
        return b""

    out = bytearray()
    read_idx = 0
    n = len(data)

    while read_idx < n:
        code = data[read_idx]
        if code == 0:
            # 编码数据中不应出现 0x00; 视为错误但尽力恢复
            read_idx += 1
            continue

        read_idx += 1
        for _ in range(code - 1):
            if read_idx >= n:
                break
            out.append(data[read_idx])
            read_idx += 1

        # 若 code < 0xFF 且还有更多数据, 追加 0x00 (替换被压缩的零)
        if code < 0xFF and read_idx < n:
            out.append(0x00)

    return bytes(out)

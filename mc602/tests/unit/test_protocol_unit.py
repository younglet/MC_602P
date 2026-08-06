import sys
import os

# 获取当前文件所在目录的"上上级目录"的绝对路径
# (模拟从外部项目根导入 mc602 的效果)
grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602.comm.packet import (
    Payload, Op, Status,
    encode_frame, try_decode_frame,
    encode_response_frame,
)
from mc602.comm.crc8 import crc8
from mc602.comm.cobs import cobs_encode, cobs_decode
CRC8_CHECKS = [
    (b"", 0x00),                  # 空数据 -> 0
    (b"\x00", 0x00),              # 单 0x00 -> 0
    (b"\x01", 0x5e),              # 0x01 -> 0x5e (查表第 1 项)
    (b"\xff", 0xbe),              # 0xFF -> 0xBE (注意: crc8_table[0xff] = 0x9c, 需确认)
]
def assert_crc8_value():
    print("test 1: CRC-8/MAXIM 已知向量")
    assert crc8(b"\x00") == 0x00, "crc(0x00) 应为 0"
    assert crc8(b"\x01") == 0x5e, "crc(0x01) 应为 0x5e"
    assert crc8(b"\x02") == 0xbc, "crc(0x02) 应为 0xbc"
    assert crc8(b"\x00\x01") == 0x5e, "crc(0x00,0x01) 应为 0x5e"
    print("  [OK] CRC-8 已知向量全部通过")
def assert_crc8_matches_firmware_table():
    """遍历 0x00~0xFF, 对比我们的 _CRC8_TABLE 与固件 crc8.c 的 crc8_table[]."""
    print("test 2: CRC8 表与固件 100% 一致 (遍历 256 项)")
    firmware = bytes([
        0x00,0x5e,0xbc,0xe2,0x61,0x3f,0xdd,0x83,0xc2,0x9c,0x7e,0x20,0xa3,0xfd,0x1f,0x41,
        0x9d,0xc3,0x21,0x7f,0xfc,0xa2,0x40,0x1e,0x5f,0x01,0xe3,0xbd,0x3e,0x60,0x82,0xdc,
        0x23,0x7d,0x9f,0xc1,0x42,0x1c,0xfe,0xa0,0xe1,0xbf,0x5d,0x03,0x80,0xde,0x3c,0x62,
        0xbe,0xe0,0x02,0x5c,0xdf,0x81,0x63,0x3d,0x7c,0x22,0xc0,0x9e,0x1d,0x43,0xa1,0xff,
        0x46,0x18,0xfa,0xa4,0x27,0x79,0x9b,0xc5,0x84,0xda,0x38,0x66,0xe5,0xbb,0x59,0x07,
        0xdb,0x85,0x67,0x39,0xba,0xe4,0x06,0x58,0x19,0x47,0xa5,0xfb,0x78,0x26,0xc4,0x9a,
        0x65,0x3b,0xd9,0x87,0x04,0x5a,0xb8,0xe6,0xa7,0xf9,0x1b,0x45,0xc6,0x98,0x7a,0x24,
        0xf8,0xa6,0x44,0x1a,0x99,0xc7,0x25,0x7b,0x3a,0x64,0x86,0xd8,0x5b,0x05,0xe7,0xb9,
        0x8c,0xd2,0x30,0x6e,0xed,0xb3,0x51,0x0f,0x4e,0x10,0xf2,0xac,0x2f,0x71,0x93,0xcd,
        0x11,0x4f,0xad,0xf3,0x70,0x2e,0xcc,0x92,0xd3,0x8d,0x6f,0x31,0xb2,0xec,0x0e,0x50,
        0xaf,0xf1,0x13,0x4d,0xce,0x90,0x72,0x2c,0x6d,0x33,0xd1,0x8f,0x0c,0x52,0xb0,0xee,
        0x32,0x6c,0x8e,0xd0,0x53,0x0d,0xef,0xb1,0xf0,0xae,0x4c,0x12,0x91,0xcf,0x2d,0x73,
        0xca,0x94,0x76,0x28,0xab,0xf5,0x17,0x49,0x08,0x56,0xb4,0xea,0x69,0x37,0xd5,0x8b,
        0x57,0x09,0xeb,0xb5,0x36,0x68,0x8a,0xd4,0x95,0xcb,0x29,0x77,0xf4,0xaa,0x48,0x16,
        0xe9,0xb7,0x55,0x0b,0x88,0xd6,0x34,0x6a,0x2b,0x75,0x97,0xc9,0x4a,0x14,0xf6,0xa8,
        0x74,0x2a,0xc8,0x96,0x15,0x4b,0xa9,0xf7,0xb6,0xe8,0x0a,0x54,0xd7,0x89,0x6b,0x35,
    ])
    from mc602.comm.crc8 import _CRC8_TABLE
    pc = bytes(_CRC8_TABLE)
    if pc != firmware:
        for i, (a, b) in enumerate(zip(pc, firmware)):
            if a != b:
                raise AssertionError(f"CRC8 表 [0x{i:02X}] 不一致: PC={a:#04x} FW={b:#04x}")
        if len(pc) != len(firmware):
            raise AssertionError(f"CRC8 表长度不一致: PC={len(pc)} FW={len(firmware)}")
    assert pc == firmware, "CRC8 表必须与固件一致"
    print(f"  [OK] 256 项全部一致")
def assert_cobs_roundtrip():
    print("test 3: COBS 编/解码 round-trip")
    cases = [
        b"",
        b"abc",
        b"hello world",
        b"\x00",
        b"\x00\x00\x00",
        bytes(range(256)),
        bytes(range(1, 255)),
        b"\x01\x02\x03" + b"\x00" * 50 + b"\xff" * 50,
    ]
    for raw in cases:
        enc = cobs_encode(raw)
        assert 0x00 not in enc[:-1] or len(enc) == 1, f"COBS 编码应不含 0x00 (除单字符): got {enc.hex()} for {raw[:8].hex()}"
        dec = cobs_decode(enc)
        assert dec == raw, f"COBS round-trip 不一致: orig={raw.hex()} → dec={dec.hex()}"
    print(f"  [OK] {len(cases)} 个用例全部通过")
def assert_frame_roundtrip():
    """两种帧:
       - 请求帧 (PC→MCU): 用 encode_frame(), 不带 status 字段
       - 响应帧 (MCU→PC): 用 encode_response_frame(), 带 status 字段. try_decode_frame() 只响应这一种.
    """
    print("test 4a: 请求帧 (PC→MCU) 字节结构正确")
    p = Payload(
        seq=0x07, op=Op.SET, svc=0x01, inst=1, prop=0x01,
        value=bytes([50]),
    )
    frame = encode_frame(p)
    assert frame[-2] == 0x00, f"倒数第二字节必须是 0x00 分隔符, got {frame[-2]:#04x}"
    assert 0x00 not in frame[:-2], "COBS 部分不应含 0x00"
    payload_bytes = p.encode()
    cobs_part = frame[:-2]
    crc_field = frame[-1]
    assert crc_field == crc8(payload_bytes), "CRC8 字段不匹配"
    assert cobs_decode(cobs_part) == payload_bytes, "COBS 解码不等"
    print(f"  [OK] 请求帧: {frame.hex()} (COBS + DELIM + CRC8={crc_field:#04x})")
    print("test 4b: 响应帧 (MCU→PC) round-trip")
    p_resp = Payload(
        seq=0x07, op=Op.SET, svc=0x01, inst=1, prop=0x01,
        status=Status.OK, value=bytes([50]),
    )
    resp_frame = encode_response_frame(p_resp)
    parsed_resp = try_decode_frame(bytearray(resp_frame))
    assert parsed_resp is not None, "响应帧应能被 try_decode_frame 解析"
    assert parsed_resp.seq == p_resp.seq
    assert parsed_resp.op == Op.SET
    assert parsed_resp.svc == 0x01
    assert parsed_resp.inst == 1
    assert parsed_resp.prop == 0x01
    assert parsed_resp.status == Status.OK
    assert parsed_resp.value == bytes([50])
    print(f"  [OK] 响应帧: {resp_frame.hex()} → Payload(status=OK, value=[50])")
    print("test 4c: 响应帧 status=NOT_FOUND 解析正确")
    p_err = Payload(
        seq=0x07, op=Op.GET, svc=0x05, inst=1, prop=0x99,
        status=Status.NOT_FOUND, value=b"",
    )
    err_frame = encode_response_frame(p_err)
    parsed_err = try_decode_frame(bytearray(err_frame))
    assert parsed_err is not None
    assert parsed_err.status == Status.NOT_FOUND
    print(f"  [OK] 错误响应: status={parsed_err.status.name}")
    print("test 4d: 长度不完整时返回 None")
    bad_buf = bytearray(frame[:-1])  # 少一个 CRC 字节
    assert try_decode_frame(bad_buf) is None
    print(f"  [OK] 不完整帧返回 None")
    print("test 4e: CRC 损坏时返回 None")
    bad_crc = bytearray(frame)
    bad_crc[-1] ^= 0xFF  # 翻转 CRC
    assert try_decode_frame(bad_crc) is None
    print(f"  [OK] CRC 错误返回 None")
def assert_set_speed_m1_frame():
    """验证: bot.motor.set_speed(M1, 50) 生成的字节流"""
    print("test 5: SET_SPEED(M1, 50) 生成的字节流")
    p = Payload(
        seq=0x10, op=Op.SET, svc=0x01, inst=1, prop=0x01,
        value=bytes([50]),
    )
    frame = encode_frame(p)
    cobs_part = frame[:-2]
    delim = frame[-2]
    crc = frame[-1]
    assert delim == 0x00, "分隔符必须是 0x00"
    payload_bytes = bytes([0x10, 0x02, 0x01, 0x01, 0x01, 0x32])
    expected_crc = crc8(payload_bytes)
    assert crc == expected_crc, f"CRC 字段不匹配: frame={crc:#04x} expected={expected_crc:#04x}"
    assert 0x00 not in cobs_part, "COBS 部分不应含 0x00"
    dec = cobs_decode(cobs_part)
    assert dec == payload_bytes
    print(f"  [OK] 完整帧: {frame.hex()}")
    print(f"        = COBS({cobs_part.hex()}) + DELIM + CRC8({crc:#04x})")
    print(f"        解码 payload: {dec.hex()} = seq/0x10 op/SET svc/MOTOR inst/1 prop/speed value/50")
if __name__ == "__main__":
    print("==== mc602 协议层单元自检 ====\n")
    try:
        assert_crc8_matches_firmware_table()
        assert_crc8_value()
        assert_cobs_roundtrip()
        assert_frame_roundtrip()
        assert_set_speed_m1_frame()
        print("\n[ALL TESTS PASSED] PC 协议层与固件一致")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        sys.exit(1)

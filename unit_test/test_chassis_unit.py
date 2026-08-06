"""
test_chassis_unit.py — Chassis service/driver 纯单元测试 (无需硬件)

验证协议帧与固件 chassis.h/chassis.c 一致 (定点格式)。
运行: python mc602/tests/test_chassis_unit.py
"""

import os
import sys

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, grandparent_dir)

from mc602.comm.packet import Op, Payload
from mc602.services.mecanum import ChassisService
from mc602.drivers.mecanum_chassis import MecanumChassis

FAILURES = []


class FakeBot:
    def __init__(self):
        self.calls = []
        self._responses = {}
        self.chassis = ChassisService(self)

    def set_response(self, prop, value: bytes):
        self._responses[prop] = value

    def _request(self, op, svc, inst, prop, value=b"", **kwargs):
        self.calls.append((op, svc, inst, prop, value, kwargs))
        data = self._responses.get(prop, b"\x00" * 12)
        return Payload(seq=1, op=op, svc=svc, inst=inst, prop=prop,
                       status=0, value=data)


def check(name, cond):
    if cond:
        print(f"  [PASS] {name}")
    else:
        FAILURES.append(name)
        print(f"  [FAIL] {name}")


def test_geometry():
    print("[ChassisService — 几何]")
    bot = FakeBot()
    svc = bot.chassis

    # SET_GEOMETRY: track*10, base*10, radius*10, ppr, roller*1000 (全 u16le)
    svc.set_geometry(track=30, wheel_base=28, wheel_radius=3,
                     encoder_ppr=2048, roller_adjust=1.052)
    op, s, inst, prop, val, kw = bot.calls[-1]
    check("帧参数 (SET 0x04 0x10)",
          (op, s, inst, prop) == (Op.SET, 0x04, 0, 0x10))
    expect = (bytes([0x2C, 0x01])   # 300
              + bytes([0x18, 0x01]) # 280
              + bytes([0x1E, 0x00]) # 30
              + (2048).to_bytes(2, "little")
              + (1052).to_bytes(2, "little"))
    check("编码 (300,280,30,2048,1052)", val == expect)

    # GET_GEOMETRY 解码
    bot.set_response(0x10, expect)
    g = svc.get_geometry()
    check("解码 track", g["track"] == 30.0)
    check("解码 wheel_base", g["wheel_base"] == 28.0)
    check("解码 radius", g["wheel_radius"] == 3.0)
    check("解码 ppr", g["encoder_ppr"] == 2048)
    check("解码 roller", abs(g["roller_adjust"] - 1.052) < 1e-6)

    # 非法参数
    try:
        svc.set_geometry(track=0)
        check("非法几何拒绝", False)
    except ValueError:
        check("非法几何拒绝", True)


def test_control():
    print("[ChassisService — 控制]")
    bot = FakeBot()
    svc = bot.chassis

    # move → SET_TWIST (i16×3: vx*100, vy*100, ω*1000)
    svc.move(vx=30, vy=-10, omega=0.5)
    op, s, inst, prop, val, kw = bot.calls[-1]
    check("move 帧 (CALL 0x04 0x82)",
          (op, s, inst, prop) == (Op.CALL, 0x04, 0, 0x82))
    check("move 编码", val == ((3000).to_bytes(2, "little", signed=True)
                               + (-1000).to_bytes(2, "little", signed=True)
                               + (500).to_bytes(2, "little", signed=True)))

    # goto → i32×3 + u8
    svc.goto(x=50, y=0, theta=0, max_speed=60)
    op, s, inst, prop, val, kw = bot.calls[-1]
    check("goto 帧 (CALL 0x04 0x80)",
          (op, s, inst, prop) == (Op.CALL, 0x04, 0, 0x80))
    check("goto 编码", val == ((5000).to_bytes(4, "little", signed=True)
                               + (0).to_bytes(4, "little", signed=True)
                               + (0).to_bytes(4, "little", signed=True)
                               + bytes([60])))

    # stop / abort / emergency / reset_odom
    svc.move(0, 0, 0)
    check("stop → SET_TWIST 0", bot.calls[-1][4] == b"\x00" * 6)
    svc.abort()
    check("abort (0x81)", bot.calls[-1][3] == 0x81)
    svc.emergency_stop()
    check("emergency (0x84)", bot.calls[-1][3] == 0x84)
    svc.reset_odom()
    check("reset_odom (0x83)", bot.calls[-1][3] == 0x83)


def test_state():
    print("[ChassisService — 状态]")
    bot = FakeBot()
    svc = bot.chassis

    # POSE: i32×3 (x*100, y*100, θ*1000)
    bot.set_response(0x01, ((1234).to_bytes(4, "little", signed=True)
                            + (-567).to_bytes(4, "little", signed=True)
                            + (1570).to_bytes(4, "little", signed=True)))
    p = svc.get_pose()
    check("pose x", p["x"] == 12.34)
    check("pose y", p["y"] == -5.67)
    check("pose theta", abs(p["theta"] - 1.57) < 1e-6)

    # STATUS
    bot.set_response(0x02, bytes([2, 0]))
    st = svc.get_status()
    check("status state=ARRIVED(2)", st["state"] == 2)

    # STATS: u32×3
    bot.set_response(0x06, ((12345).to_bytes(4, "little")
                            + (3).to_bytes(4, "little")
                            + (42).to_bytes(4, "little")))
    st = svc.get_stats()
    check("stats distance", st["distance_cm"] == 123.45)
    check("stats arrived", st["arrived_count"] == 3)
    check("stats runtime", st["runtime_s"] == 42)


def test_speed_pid():
    print("[ChassisService — 车身速度环 PID]")
    bot = FakeBot()
    svc = bot.chassis

    # 默认参数 (空转保守: Kp=1/Ki=0.3/Kd=0)
    svc.set_speed_pid()
    expect_props = {0x38: 1000, 0x39: 300, 0x3A: 0,    # X: 1.0/0.3/0
                    0x3B: 1000, 0x3C: 300, 0x3D: 0,    # Y: 1.0/0.3/0
                    0x3E: 1000, 0x3F: 300, 0x40: 0,    # W: 1.0/0.3/0
                    0x41: 60, 0x42: 86}                 # 限幅 ±60cm/s ±86°/s
    check("默认发 11 帧", len(bot.calls) == 11)
    ok = True
    for (op, s, inst, prop, val, kw), (p, v) in zip(bot.calls, expect_props.items()):
        if (op, s, inst) != (Op.SET, 0x04, 0) or prop != p \
                or int.from_bytes(val, "little") != v:
            ok = False
            break
    check("默认参数帧 (K×1000, 限幅整数)", ok)

    # 自定义参数
    svc.set_speed_pid(kp_x=1.5, ki_x=0.0, kd_x=0.0,
                      kp_y=0, ki_y=0, kd_y=0, kp_w=0, ki_w=0, kd_w=0,
                      out_lim_v=50, out_lim_w=90)
    check("自定义 Kp_x (0x38=1500)",
          bot.calls[-11][3] == 0x38
          and int.from_bytes(bot.calls[-11][4], "little") == 1500)
    check("自定义限幅 (0x41=50, 0x42=90)",
          bot.calls[-2][3] == 0x41
          and int.from_bytes(bot.calls[-2][4], "little") == 50
          and bot.calls[-1][3] == 0x42
          and int.from_bytes(bot.calls[-1][4], "little") == 90)

    # 速度上限默认 (0.7 m/s, 3.0 rad/s ≈ 172°/s)
    svc.set_max_vel()
    check("set_max_vel 默认 70/172",
          bot.calls[-2][3] == 0x28
          and int.from_bytes(bot.calls[-2][4], "little") == 70
          and bot.calls[-1][3] == 0x29
          and int.from_bytes(bot.calls[-1][4], "little") == 172)

    # 电机满量程标定 (0x43)
    svc.set_wheel_full_v(100)
    check("wheel_full_v 0x43=100",
          bot.calls[-1][3] == 0x43
          and int.from_bytes(bot.calls[-1][4], "little") == 100)


def test_driver():
    print("[MecanumChassis driver]")
    bot = FakeBot()
    car = MecanumChassis(bot, track=30, wheel_base=28, wheel_radius=3)

    # 创建即推几何
    check("创建推几何 (SET 0x10)", bot.calls[0][3] == 0x10)

    car.move(vx=20, vy=0, omega=0.3)
    check("move 委托", bot.calls[-1][3] == 0x82)

    car.goto(10, 0, 0)
    check("goto 委托", bot.calls[-1][3] == 0x80)

    bot.set_response(0x01, ((100).to_bytes(4, "little", signed=True)
                            + (200).to_bytes(4, "little", signed=True)
                            + (0).to_bytes(4, "little", signed=True)))
    p = car.update()
    check("update 位姿", abs(p.x - 1.0) < 1e-6 and abs(p.y - 2.0) < 1e-6)

    # 非零 reset_pose 拒绝 (固件仅支持归零)
    try:
        car.reset_pose(1, 0, 0)
        check("非零 reset_pose 拒绝", False)
    except ValueError:
        check("非零 reset_pose 拒绝", True)
    car.reset_pose()
    check("reset_pose 归零委托", bot.calls[-1][3] == 0x83)

    # 非 M1~M4 ports 拒绝
    try:
        MecanumChassis(bot, ports=(3, 1, 4, 2))
        check("非标 ports 拒绝", False)
    except ValueError:
        check("非标 ports 拒绝", True)


if __name__ == "__main__":
    test_geometry()
    test_control()
    test_state()
    test_speed_pid()
    test_driver()
    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)}: {FAILURES}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)

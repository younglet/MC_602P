"""
test_servo_unit.py — Servo service/driver 纯单元测试 (无需硬件)

用 FakeBot 拦截 _request, 验证帧参数与固件协议一致。
运行: python mc602/tests/test_servo_unit.py
"""

import os
import sys

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, grandparent_dir)

from mc602.comm.packet import Op, Payload
from mc602.services.servo import ServoBusService, ServoPWMService
from mc602.drivers.servo import Servo485, ServoPWM

FAILURES = []


class FakeBot:
    def __init__(self):
        self.calls = []
        self._responses = {}
        self.servo_bus = ServoBusService(self)
        self.servo_pwm = ServoPWMService(self)

    def set_response(self, prop, value: bytes):
        self._responses[prop] = value

    def _request(self, op, svc, inst, prop, value=b"", **kwargs):
        self.calls.append((op, svc, inst, prop, value, kwargs))
        data = self._responses.get(prop, b"\x00\x00")
        return Payload(seq=1, op=op, svc=svc, inst=inst, prop=prop,
                       status=0, value=data)


def check(name, cond):
    if cond:
        print(f"  [PASS] {name}")
    else:
        FAILURES.append(name)
        print(f"  [FAIL] {name}")


def test_servobus():
    print("[ServoBusService — 485]")
    bot = FakeBot()
    svc = bot.servo_bus

    # set_angle: S1, angle=90, speed=40 → [i16 90][u8 40]
    svc.set_angle(1, 90)
    op, s, inst, prop, val, kw = bot.calls[-1]
    check("帧参数 (CALL 0x20 S1 0x80)",
          (op, s, inst, prop) == (Op.CALL, 0x20, 1, 0x80))
    check("编码 [90 i16][40 u8]",
          val == (90).to_bytes(2, "little", signed=True) + bytes([40]))

    # 负角度
    svc.set_angle(3, -45, speed=80)
    _, _, _, _, val, _ = bot.calls[-1]
    check("负角度编码", val == (-45).to_bytes(2, "little", signed=True) + bytes([80]))

    # 范围钳制
    svc.set_angle(2, 200, speed=0)   # angle→150, speed→1
    _, _, _, _, val, _ = bot.calls[-1]
    check("范围钳制", val == (150).to_bytes(2, "little", signed=True) + bytes([1]))

    # 非法 ID
    try:
        svc.set_angle(19, 0)
        check("非法 ID 拒绝", False)
    except ValueError:
        check("非法 ID 拒绝", True)

    # get_angle 回读
    bot.set_response(0x01, (-30).to_bytes(2, "little", signed=True))
    check("get_angle 解码", svc.get_angle(1) == -30)

    # change_id: [u8 now][u8 new], new 限 1~3
    svc.change_id(1, 3)
    op, s, inst, prop, val, kw = bot.calls[-1]
    check("change_id 帧参数 (CALL 0x20 0x81)",
          (op, s, inst, prop) == (Op.CALL, 0x20, 1, 0x81))
    check("change_id 编码 [1][3]", val == bytes([1, 3]))
    try:
        svc.change_id(1, 4)
        check("change_id 新 ID 限 1~3", False)
    except ValueError:
        check("change_id 新 ID 限 1~3", True)

    # read_angle / ping / read_version
    bot.set_response(0x82, (512).to_bytes(4, "little", signed=True))
    check("read_angle 解码 (i32)", svc.read_angle(1) == 512)
    bot.set_response(0x83, b"\x01")
    check("ping 在线", svc.ping(1) is True)
    bot.set_response(0x83, b"\x00")
    check("ping 离线", svc.ping(2) is False)
    bot.set_response(0x84, (21).to_bytes(2, "little"))
    check("read_version 解码", svc.read_version(1) == 21)


def test_servopwm():
    print("[ServoPWMService — PWM]")
    bot = FakeBot()
    svc = bot.servo_pwm

    # set_angle: D1 (=7), angle=90, speed=50 → inst=1, [u16 90][u8 50]
    svc.set_angle(7, 90)
    op, s, inst, prop, val, kw = bot.calls[-1]
    check("帧参数 (CALL 0x21 D1 0x80)",
          (op, s, inst, prop) == (Op.CALL, 0x21, 1, 0x80))
    check("编码 [90 u16][50 u8]",
          val == (90).to_bytes(2, "little") + bytes([50]))

    # 字符串端口 'D7' → inst 7
    svc.set_angle("D7", 30)
    _, _, inst, _, _, _ = bot.calls[-1]
    check("字符串端口 D7 → inst 7", inst == 7)

    # 范围钳制: angle 200→180, speed 5→10
    svc.set_angle(9, 200, speed=5)
    _, _, _, _, val, _ = bot.calls[-1]
    check("范围钳制", val == (180).to_bytes(2, "little") + bytes([10]))

    # 非法端口
    try:
        svc.set_angle(6, 0)
        check("非法端口拒绝", False)
    except ValueError:
        check("非法端口拒绝", True)

    # get_angle
    bot.set_response(0x01, (45).to_bytes(2, "little", signed=True))
    check("get_angle 解码", svc.get_angle(8) == 45)


def test_driver():
    print("[Servo drivers]")
    bot = FakeBot()

    s = Servo485(bot, 1)
    check("Servo485 servo_id", s.servo_id == 1)
    s.set_angle(90)
    check("Servo485 委托 (SVC 0x20)", bot.calls[-1][1] == 0x20)
    s.angle = -60
    check("angle setter", bot.calls[-1][4][:2] == (-60).to_bytes(2, "little", signed=True))

    # change_id 实例方法: 更新实例 servo_id
    s.change_id(3)
    check("change_id 实例委托", bot.calls[-1][3] == 0x81 and bot.calls[-1][4] == bytes([1, 3]))
    check("实例 servo_id 同步更新", s.servo_id == 3)

    # 读取方法实例委托
    bot.set_response(0x82, (300).to_bytes(4, "little", signed=True))
    check("read_angle 实例", s.read_angle() == 300)
    bot.set_response(0x83, b"\x01")
    check("ping 实例", s.ping() is True)
    bot.set_response(0x84, (21).to_bytes(2, "little"))
    check("read_version 实例", s.read_version() == 21)

    p = ServoPWM(bot, 7)
    check("ServoPWM D1 = 端口 7", p.port == 7 and p.name == "D1")
    p.set_angle(90, speed=60)
    check("ServoPWM 委托 (SVC 0x21, inst=1)", bot.calls[-1][1] == 0x21 and bot.calls[-1][2] == 1)
    check("ServoPWM repr", "D1" in repr(p) and "P7" in repr(p))

    try:
        Servo485(bot, 0)
        check("Servo485 非法 ID 拒绝", False)
    except ValueError:
        check("Servo485 非法 ID 拒绝", True)
    try:
        ServoPWM(bot, 6)
        check("ServoPWM 非法端口拒绝", False)
    except ValueError:
        check("ServoPWM 非法端口拒绝", True)


def test_export():
    print("[导入导出]")
    import mc602
    from mc602 import Servo485, ServoPWM, ServoBusService, ServoPWMService
    check("顶层导出", all(x in mc602.__all__ for x in
                          ["Servo485", "ServoPWM", "ServoBusService", "ServoPWMService"]))


if __name__ == "__main__":
    test_servobus()
    test_servopwm()
    test_driver()
    test_export()
    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)}: {FAILURES}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)

"""
test_stepper_unit.py — Stepper service/driver 纯单元测试 (无需硬件)

用 FakeBot 拦截 _request, 验证:
  - 帧参数 (svc/inst/prop) 与固件协议一致
  - 数值编解码 (i16/i32/u16 小端, 负数)
  - 量程校验
  - per-instance driver 的字符串端口解析

运行: python mc602/tests/test_stepper_unit.py
"""

import os
import sys

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602.comm.packet import Op, Payload
from mc602.services.stepper import StepperService
from mc602.drivers.stepper import Stepper

FAILURES = []


class FakeBot:
    """记录 _request 调用, 返回可配置的响应"""

    def __init__(self):
        self.calls = []          # [(op, svc, inst, prop, value, kwargs)]
        self._responses = {}     # (op, prop) -> bytes
        self.stepper = StepperService(self)

    def set_response(self, prop, value: bytes):
        self._responses[prop] = value

    def _request(self, op, svc, inst, prop, value=b"", **kwargs):
        self.calls.append((op, svc, inst, prop, value, kwargs))
        data = self._responses.get(prop, b"\x00" * 4)
        return Payload(seq=1, op=op, svc=svc, inst=inst, prop=prop,
                       status=0, value=data)


def check(name, cond):
    if cond:
        print(f"  [PASS] {name}")
    else:
        FAILURES.append(name)
        print(f"  [FAIL] {name}")


def test_service():
    print("[StepperService]")
    bot = FakeBot()
    svc = StepperService(bot)

    # SET speed: i16 小端, svc=0x30, ch=3
    svc.set_speed(3, 2000)
    op, s, inst, prop, val, kw = bot.calls[-1]
    check("set_speed 帧参数", (op, s, inst, prop) == (Op.SET, 0x30, 3, 0x01))
    check("set_speed 编码", val == (2000).to_bytes(2, "little", signed=True))

    # 负速度
    svc.set_speed(1, -1500)
    _, _, _, _, val, _ = bot.calls[-1]
    check("负速度编码", val == (-1500).to_bytes(2, "little", signed=True))

    # 量程校验
    try:
        svc.set_speed(1, 32001)
        check("超上限量程拒绝", False)
    except ValueError:
        check("超上限量程拒绝", True)
    try:
        svc.set_speed(1, -32001)
        check("超下限量程拒绝", False)
    except ValueError:
        check("超下限量程拒绝", True)

    # 通道校验
    try:
        svc.set_speed(4, 100)
        check("非法通道拒绝", False)
    except ValueError:
        check("非法通道拒绝", True)

    # GET speed: 负数回读
    bot.set_response(0x01, (-1500).to_bytes(2, "little", signed=True))
    v = svc.get_speed(2)
    check("get_speed 解码", v == -1500)

    # GET distance: i32 大数
    bot.set_response(0x02, (123456).to_bytes(4, "little", signed=True))
    v = svc.get_distance(3)
    check("get_distance 解码", v == 123456)

    # GET/SET acc
    bot.set_response(0x03, (2000).to_bytes(2, "little"))
    check("get_acc 解码", svc.get_acc(1) == 2000)
    svc.set_acc(1, 3000)
    _, _, _, _, val, _ = bot.calls[-1]
    check("set_acc 编码", val == (3000).to_bytes(2, "little"))

    # CALL stop/reset
    svc.stop(3)
    op, s, inst, prop, val, kw = bot.calls[-1]
    check("stop 帧参数", (op, s, inst, prop) == (Op.CALL, 0x30, 3, 0x80))
    svc.reset(3)
    op, s, inst, prop, val, kw = bot.calls[-1]
    check("reset 帧参数", (op, s, inst, prop) == (Op.CALL, 0x30, 3, 0x81))


def test_driver():
    print("[Stepper driver]")
    bot = FakeBot()
    st = Stepper(bot, 3)
    check("ch=3", st.ch == 3)
    check("repr", "ST3" in repr(st))

    st.set_speed(2000)
    op, s, inst, prop, val, _ = bot.calls[-1]
    check("driver 委托 set_speed", (op, s, inst, prop) == (Op.SET, 0x30, 3, 0x01))

    st.speed = -800
    check("speed setter", bot.calls[-1][4] == (-800).to_bytes(2, "little", signed=True))

    st.stop()
    check("driver stop", bot.calls[-1][3] == 0x80)
    st.reset()
    check("driver reset", bot.calls[-1][3] == 0x81)

    # 字符串端口: "3" / "ST3"
    check("str '3'", Stepper(bot, "3").ch == 3)
    check("str 'ST3'", Stepper(bot, "ST3").ch == 3)
    try:
        Stepper(bot, 0)
        check("driver 非法通道拒绝", False)
    except ValueError:
        check("driver 非法通道拒绝", True)


def test_export():
    print("[导入导出]")
    from mc602 import Stepper, StepperService, ST1, ST2, ST3
    check("顶层导出", (Stepper, StepperService, ST1, ST2, ST3) == (Stepper, StepperService, 1, 2, 3))
    import mc602
    check("__all__ 含 Stepper", "Stepper" in mc602.__all__)
    check("__all__ 含 StepperService", "StepperService" in mc602.__all__)


if __name__ == "__main__":
    test_service()
    test_driver()
    test_export()
    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)}: {FAILURES}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)

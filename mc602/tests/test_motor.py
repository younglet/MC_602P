"""
test_motor.py — 单电机正反转测试 (可配端口)

用法: 修改 PORT 选电机, 默认 M1.
"""
import sys, os, time
grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import (
    MC602, M1, M2, M3, M4,
    SerialNotFoundError, ConnectionError, ProtocolError, TimeoutError,
)

PORT = M1           # ← 改这里选电机: M1 M2 M3 M4
DURATION = 2.0
SPEED = 50
MIN_PULSES = 100


def test(port):
    print(f"  MC602P M{port} 电机测试")
    with MC602.connect() as bot:
        print(f"  OK {bot._port_name}, FW={bot.system.version}, V={bot.system.voltage:.2f}V")
        bot.motor.reset_encoder(port)
        time.sleep(0.1)
        enc0 = bot.motor.get_encoder(port)

        print(f"  正转 +{SPEED} ...")
        bot.motor.set_speed(port, SPEED)
        time.sleep(DURATION)
        enc_fwd = bot.motor.get_encoder(port)
        bot.motor.stop(port)
        time.sleep(0.3)

        print(f"  反转 -{SPEED} ...")
        bot.motor.set_speed(port, -SPEED)
        time.sleep(DURATION)
        enc_rev = bot.motor.get_encoder(port)
        bot.motor.stop(port)
        time.sleep(0.3)

        fwd = enc_fwd - enc0
        rev = enc_rev - enc_fwd
        ok = abs(fwd) > MIN_PULSES and abs(rev) > MIN_PULSES and fwd > 0 and rev < 0
        print(f"  正转={fwd:+d}  反转={rev:+d}  {'PASS' if ok else 'FAIL'}")
        return ok


if __name__ == "__main__":
    try:
        ok = test(PORT)
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"  FAIL: {e}")
        ok = False
    sys.exit(0 if ok else 1)

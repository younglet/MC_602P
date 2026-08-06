"""
test_motor.py — 电机基础硬件测试 (M1~M6)

正转/反转, 编码器方向与脉冲数验证。默认 M1, 可传参指定。

用法:
    python mc602/tests/test_motor.py            # M1
    python mc602/tests/test_motor.py 3          # M3
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import Robot, M1, SerialNotFoundError, ConnectionError

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else M1   # 电机端口
SPEED = 60          # 测试速度
DURATION = 1.5      # 每段秒数
MIN_PULSES = 100    # 有效转动最小脉冲


def main() -> int:
    print("=" * 55)
    print(f"  电机测试: M{PORT}")
    print("=" * 55)

    try:
        robot = Robot.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {robot.bot._port_name}, FW={robot.bot.system.version}")

        m = robot.motor(PORT); m.reset_encoder()
        time.sleep(0.1)
        enc0 = m.encoder

        print(f"[   ] 正转 +{SPEED} ({DURATION}s) ...")
        m.set_speed(SPEED)
        time.sleep(DURATION)
        enc_fwd = m.encoder
        m.stop()
        time.sleep(0.3)

        print(f"[   ] 反转 -{SPEED} ({DURATION}s) ...")
        m.set_speed(-SPEED)
        time.sleep(DURATION)
        enc_rev = m.encoder
        m.stop()
        time.sleep(0.3)

        fwd = enc_fwd - enc0
        rev = enc_rev - enc_fwd
        ok = abs(fwd) > MIN_PULSES and abs(rev) > MIN_PULSES \
             and fwd > 0 and rev < 0
        print(f"[   ] 正转={fwd:+d} 脉冲  反转={rev:+d} 脉冲")
        print(f"[{'PASS' if ok else 'FAIL'}] "
              f"{'方向与脉冲正常' if ok else '方向异常/无脉冲!'}")
        return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

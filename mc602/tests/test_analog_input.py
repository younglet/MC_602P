# [实机评测] 需要硬件
"""
analog_input_test.py — 模拟输入评测 (A1~A6 + AI1~AI3, 共 9 路)

每路采样 10 次, 显示均值/浮动 (0~4095, 12 位 ADC)。
浮空口读 0 属正常; 接信号的口应有稳定值。

用法: python mc602/examples/analog_input_test.py
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import Robot, SerialNotFoundError, ConnectionError

PORTS = [f"A{i}" for i in range(1, 7)] + [f"AI{i}" for i in range(1, 4)]
SAMPLES = 10


def main() -> int:
    print("=" * 55)
    print("  模拟输入评测 (A1~A6 + AI1~AI3)")
    print("=" * 55)

    try:
        robot = Robot.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {robot.bot._port_name}, FW={robot.bot.system.version}\n")
        for port in PORTS:
            a = robot.analog(port)
            vals = [a.read() for _ in range(SAMPLES)]
            avg = sum(vals) / len(vals)
            spread = max(vals) - min(vals)
            signal = "有信号" if max(vals) > 100 else "浮空/无信号"
            print(f"  {a.name:4s}: {vals}  均值={avg:5.0f}  浮动={spread:4d}  {signal}")
            time.sleep(0.05)

        print("\n[PASS] 采样完成 (接信号的口应有非零读数)")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

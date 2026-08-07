# [实机评测] 需要硬件
"""
test_lcd.py — LCD 显示测试: 写屏后第 2 行显示 "test"

用法: python mc602/tests/test_lcd.py
预期: 写屏后屏幕第 2 行显示 "test", 3 秒内保持显示, 恢复刷新
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import Robot, SerialNotFoundError, ConnectionError


def main() -> int:
    print("=" * 50)
    print("  LCD 测试: 写屏 'test'")
    print("=" * 50)

    try:
        robot = Robot.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with robot:
        print(f"[OK] {robot.bot._port_name}, FW={robot.bot.system.version}")
        lcd = robot.lcd                  # ← per-instance driver

        print(f"[   ] 写屏: 'test' ...")
        lcd.show_line(2, "test")

        print(f"[   ] 等待 3 秒, 观察屏幕第 2 行是否显示 'test' ...")
        time.sleep(3)

        print(f"[   ] 恢复刷新 ...")
        lcd.auto()
        print(f"[PASS] 完成")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

# [实机评测] 需要硬件
"""
lcd_test.py — LCD 显示测试: 运行 2 秒后屏幕显示 "test"

用法: python mc602/examples/lcd_test.py
预期: 连接后心跳刷屏 2 秒 (屏幕有电压/心跳信息), 然后写屏
      → 心跳残留清空, 屏幕显示 "test", 心跳不再覆盖
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import Robot, SerialNotFoundError, ConnectionError


def main() -> int:
    print("=" * 50)
    print("  LCD 测试: 2 秒后显示 'test'")
    print("=" * 50)

    try:
        robot = Robot.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {robot.bot._port_name}, FW={robot.bot.system.version}")
        lcd = robot.lcd                  # ← per-instance driver
        print(f"[   ] 等 2 秒 (心跳刷屏中, 屏幕应有电压/心跳信息) ...")
        time.sleep(2)

        print(f"[   ] 写屏: 'test' ...")
        lcd.show_line(2, "test")

        print(f"[   ] 等待 3 秒, 观察屏幕:")
        print(f"      - 第 2 行显示 'test'")
        print(f"      - 其他行已清空 (心跳残留消失)")
        print(f"      - 3 秒内心跳不再覆盖")
        time.sleep(3)

        print(f"[   ] 恢复心跳刷新 ...")
        lcd.auto()
        print(f"[PASS] 完成")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

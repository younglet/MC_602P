"""
servo_test.py — 485 总线舵机实机测试

舵机接在 485 总线 (与步进同链)。默认 S1, 可传参指定 ID。

用法:
    python mc602/tests/servo_test.py            # 485 S1
    python mc602/tests/servo_test.py 3          # 485 S3
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, S1, SerialNotFoundError, ConnectionError

SID = int(sys.argv[1]) if len(sys.argv) > 1 else S1   # 485 舵机 ID


def main() -> int:
    print("=" * 55)
    print(f"  485 总线舵机测试: S{SID}")
    print("=" * 55)

    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {bot._port_name}, FW={bot.system.version}")

        print(f"[   ] S{SID}: 0° → 90° → 0° → -90° → 0°")
        for angle in [0, 90, 0, -90, 0]:
            bot.servo_bus.set_angle(SID, angle, speed=60)
            time.sleep(1.0)
        print(f"[   ] 角度回读: {bot.servo_bus.get_angle(SID)} (应 0)")
        print(f"[   ] 在线检测: {bot.servo_bus.ping(SID)}")
        print(f"[   ] 固件版本: {bot.servo_bus.read_version(SID)}")

        print("[PASS] 485 舵机指令全部发送成功 (请目视确认转动)")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

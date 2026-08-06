"""
servo_pwm_test.py — PWM 舵机实机测试

PWM 舵机接在 D1~D7 (P7~P13)。默认 D1, 可传参指定端口。

用法:
    python mc602/tests/servo_pwm_test.py            # D1
    python mc602/tests/servo_pwm_test.py D3         # D3
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, SerialNotFoundError, ConnectionError

PORT = sys.argv[1] if len(sys.argv) > 1 else "D1"   # PWM 舵机端口


def main() -> int:
    print("=" * 55)
    print(f"  PWM 舵机测试: {PORT}")
    print("=" * 55)

    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {bot._port_name}, FW={bot.system.version}")

        print(f"[   ] {PORT}: 90° → 45° → 135° → 90°")
        for angle in [90, 45, 135, 90]:
            bot.servo_pwm.set_angle(PORT, angle, speed=60)
            time.sleep(1.0)
        print(f"[   ] 角度回读: {bot.servo_pwm.get_angle(PORT)} (应 90)")

        print("[PASS] PWM 舵机指令全部发送成功 (请目视确认转动)")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

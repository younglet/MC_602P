# [实机评测] 需要硬件
"""
servo_demo.py — 舵机实机测试 (485 总线 + PWM 两个版本)

485 舵机: 需要舵机在 485 总线 (与步进同链), 默认 S1
PWM 舵机: D1 端口 (D1=P7), 默认角度 90

用法:
    python mc602/examples/servo_demo.py            # 485 S1 + PWM D1
    python mc602/examples/servo_demo.py 3          # 485 S3
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import (
    MC602, S1,
    SerialNotFoundError, ConnectionError,
)

SID = int(sys.argv[1]) if len(sys.argv) > 1 else S1   # 485 舵机 ID
PWM_PORT = 1                                          # PWM 舵机端口 (D1)


def main() -> int:
    print("=" * 55)
    print(f"  舵机测试: 485=S{SID}  PWM=D{PWM_PORT} (P{6 + PWM_PORT})")
    print("=" * 55)

    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {bot._port_name}, FW={bot.system.version}")

        # ---- 485 总线舵机 ----
        print(f"[   ] 485 舵机 S{SID}: 0° → 90° → 0° → -90° → 0°")
        bot.servo_bus.set_angle(SID, 0)
        time.sleep(1.0)
        bot.servo_bus.set_angle(SID, 90, speed=60)
        time.sleep(1.0)
        bot.servo_bus.set_angle(SID, 0)
        time.sleep(1.0)
        bot.servo_bus.set_angle(SID, -90, speed=60)
        time.sleep(1.0)
        bot.servo_bus.set_angle(SID, 0)
        time.sleep(1.0)
        print(f"[   ] 485 目标角度回读: {bot.servo_bus.get_angle(SID)}")

        # ---- PWM 舵机 (D1~D7, D1=P7) ----
        print(f"[   ] PWM 舵机 D{PWM_PORT}: 90° → 45° → 135° → 90°")
        bot.servo_pwm.set_angle(PWM_PORT, 90)
        time.sleep(1.0)
        bot.servo_pwm.set_angle(PWM_PORT, 45, speed=60)
        time.sleep(1.0)
        bot.servo_pwm.set_angle(PWM_PORT, 135, speed=60)
        time.sleep(1.0)
        bot.servo_pwm.set_angle(PWM_PORT, 90)
        time.sleep(1.0)
        print(f"[   ] PWM 目标角度回读: {bot.servo_pwm.get_angle(PWM_PORT)}")

        print("[PASS] 舵机指令全部发送成功 (请目视确认舵机转动)")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

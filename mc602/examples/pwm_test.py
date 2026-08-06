# [实机评测] 需要硬件
"""
pwm_test.py — PWM 输出评测 (D1~D7 通用占空比)

每路扫描 0→25→50→75→100→0%, 读回验证。
需要示波器/万用表/灯观察实际波形。

用法: python mc602/examples/pwm_test.py
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, SerialNotFoundError, ConnectionError

PORTS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
STEPS = [0, 25, 50, 75, 100, 75, 50, 25, 0]
HOLD = 0.3          # 每档停留秒
TOLLERANCE = 1.0    # 回读允许误差 %


def main() -> int:
    print("=" * 55)
    print("  PWM 输出评测 (D1~D7, 40Hz)")
    print("=" * 55)

    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {bot._port_name}, FW={bot.system.version}\n")
        all_ok = True
        for port in PORTS:
            print(f"--- {port} ---")
            ok = True
            for step in STEPS:
                bot.servo_pwm.set_duty(port, step)
                time.sleep(HOLD)
                got = bot.servo_pwm.get_duty(port)
                mark = "OK" if abs(got - step) <= TOLLERANCE else "FAIL"
                if mark == "FAIL":
                    ok = False
                print(f"  {step:4.0f}% → 回读 {got:5.1f}%  {mark}")
            print(f"  {'✅' if ok else '❌'} {port}")
            all_ok &= ok

        print(f"\n[{'PASS' if all_ok else 'FAIL'}] 全部通道 {'正常' if all_ok else '有异常'}")
        print("  提示: 示波器/灯观察 D 口实际 PWM 波形 (40Hz)")
        return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

# [实机评测] 需要硬件
"""
digital_io_test.py — 数字 IO 评测 (P1~P6 + D1~D7)

每路输出 1 → 读回 → 输出 0 → 读回。
⚠️ D1~D7 与 PWM 舵机共用引脚, 测试会占用这些口。
需要万用表/灯验证实际电平。

用法: python mc602/examples/digital_io_test.py
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, SerialNotFoundError, ConnectionError

PORTS = [f"P{i}" for i in range(1, 7)] + [f"D{i}" for i in range(1, 8)]
HOLD = 0.1


def main() -> int:
    print("=" * 55)
    print("  数字 IO 评测 (P1~P6 + D1~D7)")
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
            io = bot.digital_out(port)
            io.write(1)
            time.sleep(HOLD)
            v1 = io.read()
            io.write(0)
            time.sleep(HOLD)
            v0 = io.read()
            ok = (v1 == 1) and (v0 == 0)
            all_ok &= ok
            print(f"  {io.name:4s}: 1→{v1}  0→{v0}  {'✅' if ok else '❌'}")
        # D 口测试完恢复默认 (数字输出低)

        print(f"\n[{'PASS' if all_ok else 'FAIL'}] 全部端口 {'正常' if all_ok else '有异常'}")
        return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

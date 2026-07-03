"""
btremote_monitor.py — 蓝牙手柄实时监控

持续显示 4 摇杆值和当前按下的按键列表.
L1+R1 退出.
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, SerialNotFoundError, ConnectionError, BTPad

KEYS = [BTPad.KEY_MAP.get(i, "—") for i in range(16)]


def main() -> int:
    print("=" * 55)
    print("  蓝牙手柄实时监控")
    print("=" * 55)

    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {bot._port_name}, FW={bot.system.version}")
        try:
            print(f"[BT] {bot.pad.get_name()}")
        except Exception:
            pass
        print("[BT] 等待连接...")
        while True:
            try:
                if bot.pad.get_state().connected:
                    break
            except Exception:
                pass
            time.sleep(0.3)
        print("[BT] 已连接! L1+R1 退出.\n")
        print(f"  {'st1':>5} {'st2':>5} {'st3':>5} {'st4':>5}  按键")

        while True:
            try:
                s = bot.pad.get_state()
            except Exception:
                time.sleep(0.05)
                continue

            # 退出
            if (s.keys & 0x0400) and (s.keys & 0x0800):
                print("\n[L1+R1] 退出")
                break

            # 按键列表
            pressed = [KEYS[b] for b in range(16)
                       if (s.keys & (1 << b)) and b < len(KEYS)]
            key_str = "+".join(pressed) if pressed else "—"

            sys.stdout.write(
                f"\r  {s.stick1:5d} {s.stick2:5d} {s.stick3:5d} {s.stick4:5d}  "
                f"{key_str}   "
            )
            sys.stdout.flush()
            time.sleep(0.03)

    return 0


if __name__ == "__main__":
    sys.exit(main())

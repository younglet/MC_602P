"""
btremote_key_test.py — 蓝牙手柄按键/组合键测试

打印每个按键的按下/释放事件, 识别组合键.
运行后按手柄按键即可看到输出.
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, SerialNotFoundError, ConnectionError, BTPad

KEYS = BTPad.KEY_MAP  # 配置统一在 BTPad 里

COMBO_NAMES = {
    (10, 11): "L1+R1 → 退出",
    (4, 6):   "△+▽",
    (0, 2):   "↑+↓",
    (1, 3):   "←+→",
}


def btn_name(bits: int) -> str:
    """按键 bitmap → 可读名称"""
    if bits == 0:
        return "(无)"
    names = []
    for bit, name in KEYS.items():
        if bits & (1 << bit):
            names.append(name)
    return " + ".join(names)


def combo_name(bits: int) -> str:
    """识别组合键"""
    active = tuple(sorted(b for b in KEYS if bits & (1 << b)))
    return COMBO_NAMES.get(active, "")


def main() -> int:
    print("=" * 55)
    print("  蓝牙手柄按键测试")
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
        print("[BT] 等待手柄连接...")
        while True:
            try:
                if bot.pad.get_state().connected:
                    break
            except Exception:
                pass
            time.sleep(0.3)

        print("[BT] 已连接! 按手柄按键测试, L1+R1 退出.\n")

        prev = 0
        while True:
            try:
                s = bot.pad.get_state()
            except Exception:
                time.sleep(0.05)
                continue

            btn = s.keys

            # L1+R1 → 退出
            if (btn & (1 << 10)) and (btn & (1 << 11)):
                print(f"\n  >>> L1+R1 退出 <<<")
                break

            # 其他组合键
            combo = combo_name(btn)
            if combo:
                print(f"  >>> 组合: {combo}")

            # 按下沿
            pressed = btn & ~prev
            # 释放沿
            released = prev & ~btn

            if pressed:
                print(f"  [按下] {btn_name(pressed)}   raw=0x{btn:04X}")
            if released:
                print(f"  [释放] {btn_name(released)}   raw=0x{btn:04X}")

            prev = btn
            time.sleep(0.03)  # ~30Hz 扫描

    return 0


if __name__ == "__main__":
    sys.exit(main())

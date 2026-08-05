"""
pad_mecanum.py — Bluetooth remote → mecanum car (固件直读摇杆版)

摇杆控制由固件 200Hz 闭环直接读取 (control_method="BTPad"),
上位机只处理键位: 加速/减速/停车/退出。

操作:
  左摇杆 ↑↓    前进/后退
  左摇杆 ←→    横移
  右摇杆 ←→    原地旋转
  ▽ (6)        停车 (再按恢复)
  L1 (10)       加速 (×1.5)
  R1 (11)       减速 (×0.4)
  L1+R1 同时按  退出
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import (MC602, MecanumChassis,
                    SerialNotFoundError, ConnectionError)

LOOP_HZ     = 10
MAX_SPEED   = 60.0     # cm/s, 摇杆满量程线速度
MAX_OMEGA   = 46.0     # deg/s, 摇杆满量程角速度
SPEED_FAST  = 1.5      # L1 倍率
SPEED_SLOW  = 0.4      # R1 倍率

BTN_UP=0; BTN_LEFT=1; BTN_DOWN=2; BTN_RIGHT=3
BTN_TRI=4; BTN_CIR=5; BTN_CROSS=6; BTN_SQU=7
BTN_O=8; BTN_BOX=9; BTN_L1=10; BTN_R1=11; BTN_NUM1=14; BTN_NUM2=15


def main() -> int:
    print("=" * 55)
    print("  蓝牙遥控 → 麦克纳姆车 (固件直读摇杆)")
    print("=" * 55)
    print(f"  摇杆满量程: {MAX_SPEED:.0f} cm/s / {MAX_OMEGA:.0f}°/s")
    print("  左摇杆: 前进/横移  右摇杆←→: 旋转")
    print("  ▽: 停车  L1: 加速(x1.5)  R1: 减速(x0.4)  L1+R1: 退出\n")

    try:
        bot = MC602.connect()
        car = MecanumChassis(
            bot, ports=(1, 2, 3, 4),
            track=30, wheel_base=28, wheel_radius=3,
            control_method="BTPad",      # ← 固件直读摇杆
        )
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] COM={bot._port_name}, FW={bot.system.version}, "
              f"V={bot.system.voltage:.1f}V")
        try:
            name = bot.pad.get_name()
            print(f"[BT] {name}")
        except Exception:
            pass

        # 速度档位 (L1/R1 调整, 下发固件满量程参数)
        speed = 1.0
        stopped = False
        prev_btn = 0

        def apply_speed():
            """把当前档位下发给固件 (摇杆满量程 = MAX_* × 倍率)"""
            car.set_direct_params(
                deadzone=15,
                max_v=MAX_SPEED * speed,
                max_w=MAX_OMEGA * speed,
            )

        apply_speed()

        while True:
            try:
                s = bot.pad.get_state()
            except Exception:
                time.sleep(0.1)
                continue

            btn = s.keys
            pressed = btn & ~prev_btn
            prev_btn = btn

            if (btn & (1 << BTN_L1)) and (btn & (1 << BTN_R1)):
                # 退出: 关闭固件直读 (自动停车)
                car.control_method = None
                print("\n  [L1+R1] 退出")
                break

            if pressed & (1 << BTN_L1):
                speed = SPEED_FAST
                apply_speed()
                print(f"  [L1] 加速 x{speed}")
            if pressed & (1 << BTN_R1):
                speed = SPEED_SLOW
                apply_speed()
                print(f"  [R1] 减速 x{speed}")

            if pressed & (1 << BTN_CROSS):
                stopped = not stopped
                if stopped:
                    car.control_method = None    # 关闭固件直读 → 停车
                else:
                    car.control_method = "BTPad" # 恢复固件直读
                    apply_speed()
                print(f"  [▽] {'停' if stopped else '行'}")

            # 手柄断开状态提示 (固件会自动停车)
            connected = s.connected if hasattr(s, "connected") else True
            status = "STOP" if stopped else ("BT-OFF" if not connected else "RUN")
            sys.stdout.write(
                f"\r  btn=0x{btn:04X}  spd={speed:.1f}  {status}   "
            )
            sys.stdout.flush()
            time.sleep(1.0 / LOOP_HZ)

        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        car = None
        print("\n[!] 中断")
        sys.exit(130)

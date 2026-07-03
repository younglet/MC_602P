"""
pad_mecanum.py — Bluetooth remote → mecanum car

Uses MecanumChassis (RPC + kinematics). Deadzone/calibration in BTPad.

操作:
  左摇杆 ↑↓    前进/后退
  左摇杆 ←→    横移
  右摇杆 ←→    原地旋转
  ▽ (6)        停车
  L1 (10)       加速
  R1 (11)       减速
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
MAX_SPEED   = 60.0     # cm/s, 摇杆推到底对应的车身速度
SPEED_FAST  = 1.0      # L1 倍率
SPEED_SLOW  = 0.4      # R1 倍率

BTN_UP=0; BTN_LEFT=1; BTN_DOWN=2; BTN_RIGHT=3
BTN_TRI=4; BTN_CIR=5; BTN_CROSS=6; BTN_SQU=7
BTN_O=8; BTN_BOX=9; BTN_L1=10; BTN_R1=11; BTN_NUM1=14; BTN_NUM2=15


def main() -> int:
    print("=" * 55)
    print("  蓝牙遥控 → 麦克纳姆车")
    print("=" * 55)
    print(f"  控制频率: {LOOP_HZ}Hz  最高速度: {MAX_SPEED:.0f} cm/s")
    print("  左摇杆: 前进/横移  右摇杆←→: 旋转")
    print("  ▽: 停车  L1: 加速  R1: 减速  L1+R1: 退出\n")

    try:
        bot = MC602.connect()
        car = MecanumChassis(
            bot, ports=(1, 2, 3, 4),
            track=30, wheel_base=28, wheel_radius=3,
        )
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] 连接失败: {e}")
        return 1

    with bot:
        print(f"[OK] COM={bot._port_name}, FW={bot.system.version}, "
              f"V={bot.system.voltage:.1f}V")

        try:
            name = bot.pad.get_name()
            print(f"[BT] {name}")
        except Exception:
            name = "?"
        print("[BT] 等待手柄连接...")

        while True:
            try:
                if bot.pad.get_state().connected:
                    break
            except Exception:
                pass
            sys.stdout.write(f"\r  等待中 ({name})... ")
            sys.stdout.flush()
            time.sleep(0.5)
        print("\n[BT] 已连接!")

        c1, c2, c3, c4, dz = bot.pad.calibrate()
        print(f"  中心: ({c1},{c2},{c3},{c4})  死区: ±{dz:.0f}")

        speed = 1.0
        prev_btn = 0
        stopped = False
        last_v = (0.0, 0.0, 0.0)

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
                car.stop()
                print("\n  [L1+R1] 退出")
                break

            if pressed & (1 << BTN_L1):
                speed = SPEED_FAST
                print(f"  [L1] 加速 x{speed}")
            if pressed & (1 << BTN_R1):
                speed = SPEED_SLOW
                print(f"  [R1] 减速 x{speed}")
            if pressed & (1 << BTN_CROSS):
                stopped = not stopped
                if stopped:
                    car.stop()
                print(f"  [▽] {'停' if stopped else '行'}")

            if not stopped:
                fwd     = bot.pad._deadzone(s.stick1, c1, dz) * MAX_SPEED * speed
                strafe  = bot.pad._deadzone(s.stick2, c2, dz) * MAX_SPEED * speed
                rot     = bot.pad._deadzone(s.stick4, c4, dz) * MAX_SPEED * speed
                v = (fwd, strafe, rot)
                if v != last_v:
                    last_v = v
                    try:
                        car.move(*v)
                    except Exception:
                        pass
            else:
                v = (0.0, 0.0, 0.0)

            fwd, strafe, rot = v
            active = "STOP" if stopped else ("RUN" if any(v) else "IDLE")
            sys.stdout.write(
                f"\r  raw=({s.stick1:4d},{s.stick2:4d},{s.stick3:4d},{s.stick4:4d}) "
                f"btn=0x{btn:04X} "
                f"v=({fwd:+5.1f},{strafe:+5.1f},{rot:+5.1f})cm/s "
                f"spd={speed:.1f} {active}   "
            )
            sys.stdout.flush()
            time.sleep(1.0 / LOOP_HZ)

    return 0


if __name__ == "__main__":
    sys.exit(main())

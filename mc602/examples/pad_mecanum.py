"""
pad_mecanum.py — 蓝牙遥控器控麦克纳姆车

配对蓝牙手柄后运行, 用摇杆实时控制 4 路电机.
死区/校准在 BTPad.calibrate() 中处理.

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

from mc602 import MC602, SerialNotFoundError, ConnectionError, BTPadState, MultiMotors

# ─── 可调参数 ──────────────────────────────────────────────
LOOP_HZ   = 10            # 控制频率
SPEED     = 1.0           # 默认速度系数
SPEED_FAST = 1.0          # L1 加速
SPEED_SLOW = 0.4          # R1 减速
# ─── 按键位 (与 port_btremote.h 一致) ─────────────────────
BTN_UP=0; BTN_LEFT=1; BTN_DOWN=2; BTN_RIGHT=3
BTN_TRI=4; BTN_CIR=5; BTN_CROSS=6; BTN_SQU=7
BTN_O=8; BTN_BOX=9; BTN_L1=10; BTN_R1=11; BTN_NUM1=14; BTN_NUM2=15
# ───────────────────────────────────────────────────────────


def mecanum_mix(fwd: float, strafe: float, rot: float, speed: float):
    """麦克纳姆混合 (-1.0~+1.0) → (m1,m2,m3,m4) -100~+100"""
    m1 = fwd - strafe - rot
    m2 = fwd + strafe + rot
    m3 = fwd + strafe - rot
    m4 = fwd - strafe + rot
    max_v = max(abs(m1), abs(m2), abs(m3), abs(m4))
    if max_v > 1.0:
        scale = 1.0 / max_v
        m1, m2, m3, m4 = m1 * scale, m2 * scale, m3 * scale, m4 * scale
    s = speed * 100
    return int(m1 * s), int(m2 * s), int(m3 * s), int(m4 * s)


def main() -> int:
    print("=" * 55)
    print("  蓝牙遥控 → 麦克纳姆车")
    print("=" * 55)
    print(f"  控制频率: {LOOP_HZ}Hz  死区: 自动校准")
    print("  左摇杆: 前进/横移  右摇杆←→: 旋转")
    print("  ▽: 停车  L1: 加速  R1: 减速  L1+R1: 退出\n")

    try:
        bot = MC602.connect()
        chassis = MultiMotors(bot, ports=(1, 2, 3, 4))
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

        # 自动校准
        c1, c2, c3, c4, dz_abs = bot.pad.calibrate()
        c = (c1, c2, c3, c4)
        print(f"  中心: st1={c1} st2={c2} st3={c3} st4={c4}  死区: ±{dz_abs:.0f}")

        speed = SPEED
        prev_btn = 0
        stopped = False
        last_m = (0, 0, 0, 0)

        while True:
            try:
                s = bot.pad.get_state()
            except Exception:
                time.sleep(0.1)
                continue

            btn = s.keys
            pressed = btn & ~prev_btn
            prev_btn = btn

            # L1+R1 → 退出 (用 & 而非 ==, 容忍其他键同时按)
            if (btn & (1 << BTN_L1)) and (btn & (1 << BTN_R1)):
                chassis.stop_all()
                print("\n  [L1+R1] 退出")
                break

            # 功能键
            if pressed & (1 << BTN_L1):
                speed = SPEED_FAST
                print(f"  [L1] 加速 x{speed}")
            if pressed & (1 << BTN_R1):
                speed = SPEED_SLOW
                print(f"  [R1] 减速 x{speed}")
            if pressed & (1 << BTN_CROSS):
                stopped = not stopped
                if stopped:
                    chassis.stop_all()
                    last_m = (0, 0, 0, 0)
                print(f"  [▽] {'停' if stopped else '行'}")

            if not stopped:
                fwd = bot.pad._deadzone(s.stick1, c[0], dz_abs)
                strafe = bot.pad._deadzone(s.stick2, c[1], dz_abs)
                rot = bot.pad._deadzone(s.stick4, c[3], dz_abs)
                m = mecanum_mix(fwd, strafe, rot, speed)

                if m != last_m:
                    last_m = m
                    try:
                        chassis.set_speeds(*m)
                    except Exception:
                        pass
            else:
                m = last_m

            m1, m2, m3, m4 = m
            active = "STOP" if stopped else ("RUN" if any(m) else "IDLE")
            sys.stdout.write(
                f"\r  raw=({s.stick1:4d},{s.stick2:4d},{s.stick3:4d},{s.stick4:4d}) "
                f"btn=0x{btn:04X} "
                f"M=[{m1:+4d},{m2:+4d},{m3:+4d},{m4:+4d}] "
                f"spd={speed:.1f} {active}   "
            )
            sys.stdout.flush()
            time.sleep(1.0 / LOOP_HZ)

    return 0


if __name__ == "__main__":
    sys.exit(main())

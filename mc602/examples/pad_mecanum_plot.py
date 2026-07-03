"""
pad_mecanum_plot.py — 蓝牙遥控 + 实时轨迹图

控制 20Hz, matplotlib 在主循环里 plt.pause(0.01) 刷新.
左摇杆: 前进/横移, 右摇杆: 旋转, A: 停车, L1+R1: 退出.
"""

import sys
import os
import time
import math
from collections import deque

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import (MC602, MecanumChassis,
                    SerialNotFoundError, ConnectionError)

LOOP_HZ     = 20
MAX_SPEED   = 60.0      # cm/s
SPEED_FAST  = 1.0
SPEED_SLOW  = 0.4
TRAJ_LEN    = 2000      # 显示最近多少个点

BTN_CROSS=6; BTN_L1=10; BTN_R1=11

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
except ImportError:
    print("pip install matplotlib")
    sys.exit(1)


def main() -> int:
    print("=" * 55)
    print("  蓝牙遥控 + 实时轨迹图")
    print("=" * 55)
    print(f"  控制频率: {LOOP_HZ}Hz  最高速度: {MAX_SPEED:.0f} cm/s")
    print("  L1=加速  R1=减速  ▽=停车  L1+R1=退出\n")

    try:
        bot = MC602.connect()
        car = MecanumChassis(
            bot, ports=(1, 2, 3, 4),
            track=30, wheel_base=28, wheel_radius=3,
        )
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    # ── matplotlib setup ──────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 7))
    fig.canvas.manager.set_window_title("Mecanum Trajectory")
    ax.set_aspect("equal")
    ax.set_xlabel("X (cm)")
    ax.set_ylabel("Y (cm)")
    ax.grid(True, alpha=0.3)
    ax.set_title("Waiting for BT...")

    traj_x, traj_y = deque(maxlen=TRAJ_LEN), deque(maxlen=TRAJ_LEN)
    (traj_line,) = ax.plot([], [], "b-", linewidth=1, alpha=0.6)
    (car_marker,) = ax.plot([], [], "ro", markersize=10)

    running = True

    def on_close(event):
        nonlocal running
        running = False

    fig.canvas.mpl_connect("close_event", on_close)
    plt.show(block=False)

    with bot:
        print(f"[OK] COM={bot._port_name}, FW={bot.system.version}")
        try:
            name = bot.pad.get_name()
            print(f"[BT] {name}")
        except Exception:
            name = "?"
        print("[BT] 等待手柄连接...")

        while running:
            try:
                if bot.pad.get_state().connected:
                    break
            except Exception:
                pass
            sys.stdout.write(f"\r  等待中 ({name})... ")
            sys.stdout.flush()
            time.sleep(0.3)
        if not running:
            return 0
        print("\n[BT] 已连接!")

        c1, c2, c3, c4, dz = bot.pad.calibrate()
        print(f"  中心: ({c1},{c2},{c3},{c4})  死区: ±{dz:.0f}")

        speed = 1.0
        prev_btn = 0
        stopped = False
        last_v = (0.0, 0.0, 0.0)

        while running:
            try:
                s = bot.pad.get_state()
            except Exception:
                s = None

            if s is not None:
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

                # 读编码器 → 里程计
                try:
                    car.update()
                except Exception:
                    pass

                # 更新图
                pose = car.pose
                traj_x.append(pose.x)
                traj_y.append(pose.y)
                traj_line.set_data(list(traj_x), list(traj_y))
                car_marker.set_data([pose.x], [pose.y])
                ax.relim()
                ax.autoscale_view(tight=True)
                ax.set_title(
                    f"X={pose.x:+6.1f}  Y={pose.y:+6.1f}  "
                    f"θ={math.degrees(pose.theta):+5.1f}°  "
                    f"d={car.distance:5.1f}cm  "
                    f"v=({v[0]:+5.1f},{v[1]:+5.1f},{v[2]:+5.1f})"
                )
            else:
                time.sleep(0.05)

            # 必须主线程里调, TkAgg 需要事件循环
            plt.pause(1.0 / LOOP_HZ)

    plt.close('all')
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
pad_mecanum_plot.py — 蓝牙遥控 + 实时地图 (matplotlib 暗色, 固定场地)

控制 15Hz, 固定 4000x4000cm 场地, 车在地图上移动 (视口不跟随).
红色箭头 = 车头朝向, 路径线段 = 轨迹 (颜色: 红=慢, 黄=中, 绿=快).
左摇杆: 前进/横移, 右摇杆: 旋转, A: 停车, L1+R1: 退出.
滚轮缩放, 中键拖动平移 (matplotlib 默认), 双击重置视野.
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

# ── 场地 / 视口 / 控制 ─────────────────────────────────
FIELD_W    = 4000.0
FIELD_H    = 4000.0
LOOP_HZ    = 15                # 控制频率 (Hz), 遥控够用
MAX_SPEED  = 60.0              # cm/s
MAX_OMEGA  = 1.5               # rad/s
SPEED_FAST = 1.0
SPEED_SLOW = 0.4
# 编码器 PPR (pulses per revolution) — 必须填对, 否则里程计角度会放大 N 倍!
ENCODER_PPR = 2048
TRAJ_LEN    = 800              # 路径缓存 (固定大场地, 800 点够)
VIEW_INIT   = 2200.0           # 初始视野半径 (含场地边距, 看全图)
VIEW_MIN    = 100.0            # 最小视野 (放大上限)
VIEW_MAX    = 5000.0           # 最大视野 (缩小下限)
ZOOM_STEP   = 1.25
ARROW_LEN   = 25.0

# ── 暗色主题色板 ──────────────────────────────────────
BG_COLOR    = "#1a1a1a"
FG_COLOR    = "#e0e0e0"
GRID_COLOR  = "#404040"
BORDER_COLOR= "#9e9e9e"
HEAD_COLOR  = "#ff5252"
DOT_COLOR   = "#ffffff"
TAIL_COLOR  = "#bdbdbd"

BTN_CROSS, BTN_L1, BTN_R1 = 6, 10, 11

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.collections import LineCollection
    from matplotlib.colors import Normalize
except ImportError:
    print("pip install matplotlib numpy")
    sys.exit(1)


def main() -> int:
    print("=" * 55)
    print("  蓝牙遥控 + 实时地图 (固定场地 / 速度色阶)")
    print("=" * 55)
    print(f"  场地: {FIELD_W:.0f}x{FIELD_H:.0f} cm  控制: {LOOP_HZ}Hz  "
          f"线速度: {MAX_SPEED:.0f} cm/s  角速度: {MAX_OMEGA:.1f} rad/s")
    print(f"  编码器 PPR: {ENCODER_PPR}  ← 必须与实际电机匹配!")
    print(f"  视野: ±{VIEW_INIT:.0f}cm (滚轮缩放, 中键平移, 双击重置)")
    print("  L1=加速  R1=减速  ▽=停车  L1+R1=退出\n")

    try:
        bot = MC602.connect()
        car = MecanumChassis(
            bot, ports=(1, 2, 3, 4),
            track=30, wheel_base=28, wheel_radius=3,
            encoder_ppr=ENCODER_PPR,
        )
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    # 车默认在场地中央
    car.reset_pose(FIELD_W / 2, FIELD_H / 2, 0.0)

    # ── matplotlib setup ──────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    fig.canvas.manager.set_window_title("Mecanum Live Map (固定场地)")
    ax.set_aspect("equal")
    ax.set_xlabel("X (cm)", color=FG_COLOR)
    ax.set_ylabel("Y (cm)", color=FG_COLOR)
    ax.tick_params(colors=FG_COLOR)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    ax.grid(True, alpha=0.6, color=GRID_COLOR, linewidth=0.5)
    ax.set_title("Waiting for BT...", color=FG_COLOR)
    # 固定视野 — 一开始就设好, 主循环里不再重设
    ax.set_autoscale_on(False)
    ax.set_xlim(-VIEW_INIT, VIEW_INIT)
    ax.set_ylim(-VIEW_INIT, VIEW_INIT)

    # 场地边界 (画一次, 不变)
    ax.add_patch(plt.Rectangle(
        (0, 0), FIELD_W, FIELD_H,
        fill=False, edgecolor=BORDER_COLOR, linewidth=1.5, zorder=1,
    ))

    # ── 轨迹: LineCollection, 共享色阶 ────────────────
    traj_pts = deque(maxlen=TRAJ_LEN)   # (x, y, speed_mag)
    speed_norm = Normalize(vmin=0, vmax=MAX_SPEED)
    traj_lines = LineCollection(
        [], cmap="RdYlGn", norm=speed_norm,
        linewidths=2.0, alpha=0.95, zorder=2,
    )
    ax.add_collection(traj_lines)
    cbar = fig.colorbar(traj_lines, ax=ax, shrink=0.62, pad=0.02)
    cbar.set_label("speed (cm/s)", color=FG_COLOR)
    cbar.ax.yaxis.set_tick_params(color=FG_COLOR)
    plt.setp(cbar.ax.get_yticklabels(), color=FG_COLOR)
    cbar.outline.set_edgecolor(GRID_COLOR)

    # ── 车体: 朝向箭头 + 中心点 + 车尾短横 ───────────
    car_arrow = ax.quiver(
        [0], [0], [ARROW_LEN], [0],
        angles="xy", scale_units="xy", scale=1,
        color=HEAD_COLOR, width=0.006, zorder=4,
    )
    (car_dot,)  = ax.plot([], [], "o", color=DOT_COLOR,
                          markersize=7, markeredgecolor=HEAD_COLOR,
                          markeredgewidth=1.2, zorder=6)
    (car_tail,) = ax.plot([], [], "-", color=TAIL_COLOR,
                          linewidth=2, zorder=5)

    running = True

    def on_close(event):
        nonlocal running
        running = False

    def on_scroll(event):
        """以鼠标位置为中心缩放"""
        if event.xdata is None or event.ydata is None:
            return
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        cur_w = xlim[1] - xlim[0]
        cur_h = ylim[1] - ylim[0]
        if event.button == "up":
            scale = 1 / ZOOM_STEP
        elif event.button == "down":
            scale = ZOOM_STEP
        else:
            return
        new_w = max(VIEW_MIN, min(VIEW_MAX, cur_w * scale))
        new_h = max(VIEW_MIN, min(VIEW_MAX, cur_h * scale))
        if abs(new_w - cur_w) < 1e-6:
            return
        dx = (event.xdata - xlim[0]) / cur_w
        dy = (event.ydata - ylim[0]) / cur_h
        new_x0 = event.xdata - dx * new_w
        new_y0 = event.ydata - dy * new_h
        ax.set_xlim(new_x0, new_x0 + new_w)
        ax.set_ylim(new_y0, new_y0 + new_h)
        fig.canvas.draw_idle()

    def on_double_click(event):
        """双击重置视野到全图"""
        if event.dblclick:
            ax.set_xlim(-VIEW_INIT, VIEW_INIT)
            ax.set_ylim(-VIEW_INIT, VIEW_INIT)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("close_event",       on_close)
    fig.canvas.mpl_connect("scroll_event",      on_scroll)
    fig.canvas.mpl_connect("button_press_event", on_double_click)
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
        pose = car.pose  # 缓存当前位姿

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
                    # 车上 vy / omega 与代码约定镜像 → 取反
                    strafe  = -bot.pad._deadzone(s.stick2, c2, dz) * MAX_SPEED * speed
                    rot     = -bot.pad._deadzone(s.stick4, c4, dz) * MAX_OMEGA * speed
                    v = (fwd, strafe, rot)
                    if v != last_v:
                        last_v = v
                        try:
                            car.move(*v)
                        except Exception:
                            pass
                else:
                    v = (0.0, 0.0, 0.0)

                try:
                    car.update()
                except Exception:
                    pass

                # ── 更新地图 (固定场地, 视口不动) ──
                pose = car.pose
                c, sn = math.cos(pose.theta), math.sin(pose.theta)
                speed_mag = math.hypot(v[0], v[1])

                traj_pts.append((pose.x, pose.y, speed_mag))
                pts = np.array(traj_pts, dtype=float)
                if len(pts) >= 2:
                    seg_xy  = np.stack([pts[:-1, :2], pts[1:, :2]], axis=1)
                    seg_clr = (pts[:-1, 2] + pts[1:, 2]) / 2
                    traj_lines.set_segments(seg_xy)
                    traj_lines.set_array(seg_clr)

                # 车体 (在 ax 坐标里, 不再在屏幕中央)
                car_arrow.set_offsets([[pose.x, pose.y]])
                car_arrow.set_UVC(c * ARROW_LEN, sn * ARROW_LEN)
                car_dot.set_data([pose.x], [pose.y])
                tail = 8.0
                tx, ty = -sn * tail, c * tail
                car_tail.set_data(
                    [pose.x - tx, pose.x + tx],
                    [pose.y - ty, pose.y + ty],
                )

                ax.set_title(
                    f"X={pose.x:+7.1f}  Y={pose.y:+7.1f}  "
                    f"θ={math.degrees(pose.theta):+6.1f}°  "
                    f"d={car.distance:6.1f}cm  "
                    f"|v|={speed_mag:5.1f}cm/s",
                    color=FG_COLOR,
                )
            else:
                time.sleep(0.05)

            plt.pause(1.0 / LOOP_HZ)

    plt.close('all')
    return 0


if __name__ == "__main__":
    sys.exit(main())

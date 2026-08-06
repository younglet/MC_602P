"""
speed_loop_eval.py — 车身速度环实车验证 (SVC 0x04, 固件 200Hz)

验证内容:
  1. 默认闭环 (cfg_vehicle.yaml 参考参数): 前进/横移/原地转/后退,
     采样 pose 差分估算实测速度, 统计稳态误差 → 速度环是否收敛。
  2. --compare 模式: 旁路 (三轴全 0 = 旧版开环) vs 默认闭环 贴地对比,
     负载下闭环应明显补偿速度损失。

安全: 车放地面且前后左右留 1m 空间, 或四轮架空 (推荐首次)。

用法:
    python mc602/tools/speed_loop_eval.py            # 默认闭环序列
    python mc602/tools/speed_loop_eval.py --compare  # 加旁路 vs 闭环对比
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, SerialNotFoundError, ConnectionError
from mc602.drivers.mecanum_chassis import MecanumChassis

SAMPLE_DT = 0.10    # 100ms 采样 (固件竞态规避)
DURATION = 3.5      # 每步时长 (调参需积分收敛)
INTER_CALL = 0.03   # 请求间隔
SETTLE = 0.5        # 稳态统计跳过开头过渡段

# (名称, vx, vy, w) — 低速序列
SEQ = [("前进", 20, 0, 0.0),
       ("横移", 0, 20, 0.0),
       ("原地转", 0, 0, 1.0),
       ("后退", -20, 0, 0.0)]


def sample_run(car: MecanumChassis, vx: float, vy: float, w: float):
    """跑 DURATION 秒, 采样 pose 差分 → [(t, v_lin, v_ang), ...]"""
    car.move(vx, vy, w)
    time.sleep(0.15)  # 等命令生效
    rows = []
    t0 = time.monotonic()
    prev = car.update()
    prev_t = t0
    while time.monotonic() - t0 < DURATION:
        time.sleep(INTER_CALL)
        try:
            now = time.monotonic()
            p = car.update()
        except Exception:
            continue  # 偶发丢帧跳过, 不中断
        dt = now - prev_t
        if dt > 0:
            v_lin = ((p.x - prev.x) ** 2 + (p.y - prev.y) ** 2) ** 0.5 / dt
            v_ang = (p.theta - prev.theta) / dt
            rows.append((now - t0, v_lin, v_ang))
        prev, prev_t = p, now
    car.move(0, 0, 0)
    return rows


def report(name: str, target_lin: float, target_ang: float, rows):
    """稳态平均 + 误差 → 收敛判断"""
    steady = [(t, vl, va) for t, vl, va in rows if t >= SETTLE]
    if not steady:
        print(f"  [!] {name}: 无有效采样")
        return False
    avg_lin = statistics.mean(vl for _, vl, _ in steady)
    avg_ang = statistics.mean(va for _, _, va in steady)
    ok = True
    if target_lin != 0:
        err = abs(avg_lin - abs(target_lin)) / abs(target_lin) * 100
        print(f"  {name}: 目标 {target_lin:+.0f} cm/s → 实测 {avg_lin:5.1f} cm/s"
              f" (稳态, 误差 {err:4.1f}%)")
        ok = ok and err < 15
    else:
        # 旋转/停车步: 线速度应接近 0
        print(f"  {name}: 目标线速度 0 → 实测 {avg_lin:5.1f} cm/s"
              f" (应≈0, 验证旋转不串线速度)")
        ok = ok and avg_lin < 5
    if target_ang != 0:
        err = abs(avg_ang - abs(target_ang)) / abs(target_ang) * 100
        print(f"         目标角速度 {target_ang:+.1f} rad/s"
              f" → 实测 {avg_ang:5.2f} rad/s (误差 {err:4.1f}%)")
        ok = ok and err < 15
    elif target_ang == 0 and target_lin == 0:
        print(f"         停车: 实测 {avg_lin:5.1f} cm/s")
    return ok


def main():
    ap = argparse.ArgumentParser(description="车身速度环实车验证")
    ap.add_argument("--compare", action="store_true",
                    help="旁路(旧版开环) vs 默认闭环 贴地对比")
    ap.add_argument("--tune", action="store_true",
                    help="Kp/Ki/Kd 自动扫描调参 (每组前进 20cm/s × 2.5s)")
    args = ap.parse_args()

    print("=" * 60)
    print("  车身速度环实车验证 (固件 200Hz)")
    print("=" * 60)
    print("  ⚠ 安全: 车放地面且四周留 1m 空间, 或四轮架空 (首次推荐架空)")
    input("  准备好后按回车开始...")

    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] 连接失败: {e}")
        sys.exit(1)

    try:
        with bot:
            car = MecanumChassis(bot, track=30, wheel_base=28, wheel_radius=3)

            # 0. 释放电机: abort 底盘 (上次残留 TWIST 会占用电机目标表)
            car.abort()
            time.sleep(0.2)

            # 1. 确认固件速度环参数
            g = car.geometry
            print(f"\n[几何] track={g['track']} wheel_base={g['wheel_base']} "
                  f"radius={g['wheel_radius']} ppr={g['encoder_ppr']} "
                  f"roller={g['roller_adjust']}")
            print("[速度环] 默认参数 (空转保守: Kp=1/Ki=0.3/Kd=0, 贴地后 --tune 精调)")
            print(f"         pid_x=1.0/0.3/0  pid_y=1.0/0.3/0  "
                  f"pid_w=1.0/0.3/0  限幅 ±60cm/s ±86°/s")

            # 2. 序列测试 (默认闭环)
            print("\n[序列测试 — 默认闭环]")
            all_ok = True
            for i, (name, vx, vy, w) in enumerate(SEQ, 1):
                print(f"  [{i}/{len(SEQ)}]", end=" ")
                rows = sample_run(car, vx, vy, w)
                all_ok &= report(name, vx if vx else vy, w, rows)
                time.sleep(0.4)

            # 2b. 可选: 调参扫描 (X 轴, Y/W 同比例)
            if args.tune:
                print("\n[调参扫描 — X 轴前进 20cm/s]")
                # (名称, kp, ki, kd) — 从保守到激进
                SCAN = [
                    ("P 0.5/Ki 0.3", 0.5, 0.3, 0.0),
                    ("P 0.8/Ki 0.5", 0.8, 0.5, 0.0),
                    ("P 1.0/Ki 0.5", 1.0, 0.5, 0.0),
                    ("P 1.0/Ki 1.0", 1.0, 1.0, 0.0),
                    ("P 1.5/Ki 1.0", 1.5, 1.0, 0.0),
                    ("P 2.0/Ki 1.5", 2.0, 1.5, 0.0),
                ]
                for name, kp, ki, kd in SCAN:
                    car.set_speed_pid(kp_x=kp, ki_x=ki, kd_x=kd,
                                      kp_y=kp, ki_y=ki, kd_y=kd,
                                      kp_w=kp * 1.5, ki_w=ki, kd_w=kd,
                                      out_lim_v=60, out_lim_w=86)
                    time.sleep(0.3)
                    rows = sample_run(car, 20, 0, 0)
                    steady = [vl for t, vl, va in rows if t >= SETTLE]
                    if steady:
                        avg = statistics.mean(steady)
                        print(f"  [{name}] 实测 {avg:5.1f} cm/s"
                              f" (期望 20, 误差 {abs(avg-20)/20*100:4.1f}%)")
                    else:
                        print(f"  [{name}] 无有效采样")
                    time.sleep(0.3)
                car.set_speed_pid()  # 恢复默认

            # 3. 可选: 旁路 vs 闭环对比 (贴地负载下差异明显)
            if args.compare:
                print("\n[对比 — 旁路(旧版) vs 闭环(默认)] 前进 20cm/s:")
                car.set_speed_pid(kp_x=0, ki_x=0, kd_x=0,
                                  kp_y=0, ki_y=0, kd_y=0,
                                  kp_w=0, ki_w=0, kd_w=0,
                                  out_lim_v=60, out_lim_w=86)
                time.sleep(0.2)
                rows = sample_run(car, 20, 0, 0)
                ok_bypass = report("旁路", 20, 0, rows)
                time.sleep(0.4)

                car.set_speed_pid()  # 恢复默认闭环
                time.sleep(0.2)
                rows = sample_run(car, 20, 0, 0)
                ok_closed = report("闭环", 20, 0, rows)
                print(f"  结论: {'闭环补偿生效 ✓' if ok_closed and not ok_bypass else '两者接近 (架空? 或负载太小)'}")

            car.abort()
            print("\n[OK] 测试完成, 已停车并释放底盘 (电机可自由使用)")
            sys.exit(0 if all_ok else 1)
    except KeyboardInterrupt:
        print("\n[!] 中断, 停车")
        try:
            car.abort()
        except Exception:
            pass
        sys.exit(130)


if __name__ == "__main__":
    main()

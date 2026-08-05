"""
chassis_calibrate.py — 麦轮底盘标定 (比赛前必做)

标定 3 项:
  1. 满速 max_v        — 电机 100% 的实际速度 (cm/s)
  2. 直线漂移          — 前进 1.5m 看横向偏移 (调 roller_adjust)
  3. 旋转角度误差      — 原地转 360° 看里程计角度 (调 wc / 确认编码器 PPR)

用法:
    python mc602/examples/chassis_calibrate.py

建议: 车架空或场地够大时跑。标定完把数值填进你的启动代码:
    car.set_max_vel(v_cm_s=<结果1>)
    car = MecanumChassis(bot, ..., roller_adjust=<结果2>)
"""

import sys
import os
import time
import math

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, MecanumChassis, SerialNotFoundError, ConnectionError

R = 3.0      # 轮半径 cm (按实际改)
PPR = 2048   # 编码器每圈脉冲 (按实际改)


def main() -> int:
    print("=" * 60)
    print("  麦轮底盘标定 (车架空或场地够大)")
    print("=" * 60)

    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {bot._port_name}, FW={bot.system.version}")
        car = MecanumChassis(bot, track=30, wheel_base=28,
                             wheel_radius=R, encoder_ppr=PPR)

        # ---------- 1. 满速标定 ----------
        print("\n[1/3] 满速标定: 4 路电机 100% 跑 2s ...")
        car.abort()
        time.sleep(0.3)
        for p in range(1, 5):
            bot.motor.reset_encoder(p)
        for p in range(1, 5):
            bot.motor.set_speed(p, 100)
        time.sleep(2)
        for p in range(1, 5):
            bot.motor.stop(p)
        time.sleep(0.2)
        e = [bot.motor.get_encoder(p) for p in range(1, 5)]
        dists = [abs(x) * (2 * math.pi * R / PPR) for x in e]
        max_v = sum(dists) / 4 / 2.0
        print(f"    各轮: {[round(d, 1) for d in dists]} cm")
        print(f"    → max_v = {max_v:.1f} cm/s")
        car.set_max_vel(v_cm_s=max_v)

        # ---------- 2. 直线漂移 (roller_adjust) ----------
        print("\n[2/3] 直线标定: vx=30 前进 5s (约 1.5m) ...")
        car.reset_pose()
        time.sleep(0.3)
        car.move(vx=30)
        time.sleep(5)
        car.stop()
        time.sleep(0.3)
        p = car.pose
        print(f"    终点: x={p.x:.1f}cm, y={p.y:.1f}cm, θ={math.degrees(p.theta):.1f}°")
        if abs(p.x) > 50 and abs(p.y) / abs(p.x) < 0.15:
            drift = p.y / p.x          # 横向漂移比例
            # 修正: tan_r 需要缩放 (1 - drift), roller_adjust 同比例
            new_adj = 1.052 * (1 - drift)
            print(f"    漂移率 {drift * 100:.2f}% → roller_adjust ≈ {new_adj:.3f}")
            print(f"    若 y 为正(偏左) 减小, 为负(偏右) 增大")
        else:
            print("    数据异常, 检查轮子/接线/场地")

        # ---------- 3. 旋转角度 ----------
        print("\n[3/3] 旋转标定: ω=1.57 转 4s (期望 360°) ...")
        car.reset_pose()
        time.sleep(0.3)
        car.move(omega=1.57)
        time.sleep(4)
        car.stop()
        time.sleep(0.3)
        p = car.pose
        print(f"    里程计 θ = {math.degrees(p.theta):.1f}° (期望 360°)")
        if abs(math.degrees(p.theta) - 360) > 3:
            print(f"    误差 {math.degrees(p.theta) - 360:+.1f}° → 检查 encoder_ppr / 轮径是否准确")
            print(f"    实际 ppr ≈ {PPR * 360.0 / math.degrees(p.theta):.0f}")

        print("\n" + "=" * 60)
        print("  标定结果填入启动代码:")
        print(f"    car.set_max_vel(v_cm_s={max_v:.1f})")
        print("    直线漂移按提示调 roller_adjust, 角度误差检查 PPR/轮径")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

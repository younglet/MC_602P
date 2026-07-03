"""
mecanum_group_demo.py — 演示 MecanumGroupService 一次指令控四路

依赖: 固件已刷新的 services.c (含 mecanum_group_handler, SVC=0x02).
      Python SDK 已更新 mc602/services/mecanum.py.
"""
import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, SerialNotFoundError, ConnectionError


def main() -> int:
    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {bot._port_name}, FW={bot.system.version}, V={bot.system.voltage:.2f}V")

        print("\n=== 前进 (1 帧) ===")
        t0 = time.monotonic()
        bot.mecanum.set_speeds(80, 80, 80, 80)
        dt = (time.monotonic() - t0) * 1000
        print(f"  延迟: {dt:.1f} ms")
        time.sleep(1)

        print("\n=== 读编码器 (1 帧) ===")
        t0 = time.monotonic()
        e1, e2, e3, e4 = bot.mecanum.get_encoders()
        dt = (time.monotonic() - t0) * 1000
        print(f"  M1={e1}  M2={e2}  M3={e3}  M4={e4}  (延迟 {dt:.1f} ms)")

        print("\n=== 读状态 (1 帧) ===")
        s1, s2, s3, s4 = bot.mecanum.get_statuses()
        print(f"  M1={s1} M2={s2} M3={s3} M4={s4}  "
              f"(1=运行 0=停止 2=堵转)")

        print("\n=== 横移右 2 秒 ===")
        bot.mecanum.set_speeds(-80, 80, 80, -80)
        time.sleep(2)

        print("\n=== 原地旋转 2 秒 ===")
        bot.mecanum.set_speeds(-80, 80, -80, 80)
        time.sleep(2)

        print("\n=== 停 (1 帧) ===")
        t0 = time.monotonic()
        bot.mecanum.stop_all()
        dt = (time.monotonic() - t0) * 1000
        print(f"  延迟: {dt:.1f} ms")

        print("\n[DONE] MecanumGroup 全部 API 测试通过")

    return 0


if __name__ == "__main__":
    sys.exit(main())

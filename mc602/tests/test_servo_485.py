"""
servo_485_test.py — 485 总线舵机实机测试

舵机接在 485 总线 (与步进同链)。默认 S1, 可传参指定 ID。

用法:
    python mc602/tests/servo_485_test.py            # 485 S1
    python mc602/tests/servo_485_test.py 3          # 485 S3
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import Robot, S1, SerialNotFoundError, ConnectionError

SID = int(sys.argv[1]) if len(sys.argv) > 1 else S1   # 485 舵机 ID


def main() -> int:
    print("=" * 55)
    print(f"  485 总线舵机测试: S{SID}")
    print("=" * 55)

    try:
        robot = Robot.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with robot:
        print(f"[OK] {robot.bot._port_name}, FW={robot.bot.system.version}")
        s = robot.servo485(SID)          # ← per-instance driver

        print(f"[   ] S{SID}: 0° → 90° → 0° → -90° → 0°")
        for angle in [0, 90, 0, -90, 0]:
            s.set_angle(angle, speed=60)
            time.sleep(1.0)
        print(f"[   ] 角度回读: {s.angle} (应 0)")
        print(f"[   ] 在线检测: {s.ping()}")
        print(f"[   ] 固件版本: {s.read_version()}")

        # ---- 可选: 修改 ID (回车跳过, 新 ID 限 1~3) ----
        try:
            ans = input(f"  修改 ID → 1~3 (回车跳过, 当前 S{SID}): ").strip()
            if ans:
                new_id = int(ans)
                if 1 <= new_id <= 3 and new_id != SID:
                    print(f"  ⚠️ 要求总线上只有 1 个舵机")
                    s.change_id(new_id)
                    print(f"  S{SID} → S{new_id} 修改完成")
                else:
                    print("  跳过: ID 必须 1~3 且不同于当前")
            else:
                print("  跳过 (保持 S{})".format(SID))
        except ValueError:
            print("  跳过: 无效输入")

        print("[PASS] 485 舵机测试完成 (请目视确认转动)")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

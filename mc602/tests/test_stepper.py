# [实机评测] 需要硬件
"""
stepper_demo.py — 步进电机实机测试 (485 总线, 默认 3 号通道)

流程: 设 acc → 正转 → 读距离 → 停 → 反转 → 读距离 → 停 → 复位

用法:
    python mc602/examples/stepper_demo.py          # 3 号通道
    python mc602/examples/stepper_demo.py 2        # 指定通道
"""

import sys
import os
import time

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import (
    MC602, ST1, ST2, ST3,
    SerialNotFoundError, ConnectionError,
)

CH = int(sys.argv[1]) if len(sys.argv) > 1 else ST3   # ← 3 号通道
SPEED = 3000        # 脉冲速度 (SDK 量程 ±32000)
DURATION = 2.0      # 每段运行秒数
ACC = 2000          # 加减速 (默认 1000)

CH_NAME = {ST1: "ST1", ST2: "ST2", ST3: "ST3"}


def main() -> int:
    print("=" * 55)
    print(f"  步进电机测试 {CH_NAME.get(CH, CH)}")
    print("=" * 55)

    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] {bot._port_name}, FW={bot.system.version}")

        print(f"[   ] 设 acc={ACC} ...")
        bot.stepper.set_acc(CH, ACC)
        time.sleep(0.1)

        d0 = bot.stepper.get_distance(CH)   # 起点绝对位置

        print(f"[   ] 正转 +{SPEED} ({DURATION}s) ...")
        bot.stepper.set_speed(CH, SPEED)
        time.sleep(DURATION)
        d_fwd = bot.stepper.get_distance(CH)
        bot.stepper.stop(CH)
        time.sleep(0.3)

        print(f"[   ] 反转 -{SPEED} ({DURATION}s) ...")
        bot.stepper.set_speed(CH, -SPEED)
        time.sleep(DURATION)
        d_rev = bot.stepper.get_distance(CH)
        bot.stepper.stop(CH)
        time.sleep(0.3)

        # 注意: distance 是驱动器累计的绝对位置 (非阶段增量), 必须做差
        fwd = d_fwd - d0
        rev = d_rev - d_fwd
        ok = fwd > 0 and rev < 0 and abs(rev) > 100
        print(f"[   ] 正转增量={fwd:+d}  反转增量={rev:+d}  (绝对位置: {d0} → {d_fwd} → {d_rev})")
        print(f"[{'PASS' if ok else 'FAIL'}] {'方向正确' if ok else '方向异常/无脉冲!'}")

        print("[   ] 复位/释放 (阻塞 ~100ms) ...")
        bot.stepper.reset(CH)

        return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)

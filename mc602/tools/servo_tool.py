"""
servo_tool.py — 485 舵机配置工具 (扫描 / 改 ID)

用法:
    python mc602/tools/servo_tool.py scan                      # 扫描 1~3
    python mc602/tools/servo_tool.py scan --max-id 18          # 扫描 1~18
    python mc602/tools/servo_tool.py change-id 1 2             # S1 → S2
    python mc602/tools/servo_tool.py ping 1                    # 在线检测

    # 指定串口 (默认自动找 CH340)
    python mc602/tools/servo_tool.py scan --port COM7
"""

from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mc602 import MC602, SerialNotFoundError, ConnectionError


def do_scan(bot, max_id: int) -> int:
    print(f"扫描 485 总线舵机 (ID 1~{max_id}) ...")
    found = bot.servo_bus.scan(max_id)
    if not found:
        print("  未发现舵机")
        print("  检查: 总线接线 / 舵机供电 / 舵机 ID 是否在范围内")
        return 1
    print(f"  在线: S" + ", S".join(str(i) for i in found))
    return 0


def do_change_id(bot, id_now: int, id_new: int) -> int:
    print(f"修改舵机 ID: S{id_now} → S{id_new} ...")
    print("  ⚠️ 要求总线上只有 1 个舵机 (SDK 限制)")
    bot.servo_bus.change_id(id_now, id_new)
    print(f"  完成。重新扫描验证: python mc602/tools/servo_tool.py scan")
    return 0


def do_ping(bot, servo_id: int) -> int:
    ok = bot.servo_bus.ping(servo_id)
    print(f"S{servo_id}: {'在线 ✅' if ok else '离线 ❌'}")
    if ok:
        print(f"  角度: {bot.servo_bus.read_angle(servo_id)}°, "
              f"版本: {bot.servo_bus.read_version(servo_id)}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="485 舵机配置工具")
    parser.add_argument("cmd", choices=["scan", "change-id", "ping"],
                        help="scan: 扫描在线舵机 | change-id: 改 ID | ping: 在线检测")
    parser.add_argument("args", nargs="*", help="参数 (change-id: <now> <new>, ping: <id>)")
    parser.add_argument("--max-id", type=int, default=3,
                        help="扫描范围上限 (默认 3, 最大 18)")
    parser.add_argument("--port", default=None, help="串口 (默认自动找 CH340)")
    args = parser.parse_args()

    try:
        bot = MC602.connect(port=args.port)
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] 连接失败: {e}")
        return 1

    with bot:
        print(f"[OK] {bot._port_name}, FW={bot.system.version}")
        try:
            if args.cmd == "scan":
                return do_scan(bot, args.max_id)
            if args.cmd == "change-id":
                if len(args.args) < 2:
                    print("[!] 用法: change-id <id_now> <id_new>")
                    return 1
                return do_change_id(bot, int(args.args[0]), int(args.args[1]))
            if args.cmd == "ping":
                if len(args.args) < 1:
                    print("[!] 用法: ping <servo_id>")
                    return 1
                return do_ping(bot, int(args.args[0]))
        except Exception as e:
            print(f"[!] 失败: {e}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

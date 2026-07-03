import sys
import os

# 获取当前文件所在目录的"上上级目录"的绝对路径
# (模拟从外部项目根导入 mc602 的效果)
grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

import time

from mc602 import (
    MC602, M1,
    SerialNotFoundError,
    ConnectionError,
    ProtocolError,
    TimeoutError,
)
def section(title: str) -> None:
    print(f"\n=== {title} ===")
def main() -> int:
    print("MC602P smart_car_sdk — M1 演示 (mc602)")
    print("要求: 已烧录带 COBS+CRC8 协议的固件 (rx_process_start() 已运行)")
    section("1. 连接控制器")
    try:
        bot = MC602.connect()
    except SerialNotFoundError as e:
        print(f"[!] {e}")
        return 1
    except ConnectionError as e:
        print(f"[!] {e}")
        return 2
    print(f"[OK] 已连接 {bot._port_name} @ {bot._baudrate} bps")
    try:
        with bot:
            section("2. 协议握手 — DISCOVER / 信息查询")
            try:
                svcs = bot.discover(timeout=1.0)
                print(f"[OK] 服务列表: {[hex(s) for s in svcs]}")
            except TimeoutError:
                print("[!] DISCOVER 超时 — 协议引擎可能未启动, 请确认固件已烧录且 user_main.c 调用了 rx_process_start()")
                return 3
            print(f"[OK] 固件版本: {bot.system.version}")
            print(f"[OK] 电池电压: {bot.system.voltage:.2f} V")
            print(f"[OK] 启动时间: {bot.system.uptime} s")
            section("3. 读取 M1 初始状态")
            encoder = bot.motor.get_encoder(M1)
            status = bot.motor.get_status(M1)
            status_name = ["停止", "运行", "堵转", "PID到位", "PID超时"][status]
            print(f"[OK] 编码器: {encoder}  状态: {status_name}")
            bot.motor.reset_encoder(M1)
            print("[OK] 已复位编码器")
            section("4. M1 正转 +50 (3 秒)")
            t0 = time.monotonic()
            bot.motor.set_speed(M1, 50)
            time.sleep(0.3)
            enc1 = bot.motor.get_encoder(M1)
            print(f"  [+0.3s] encoder={enc1} status={bot.motor.get_status(M1)}  → 开始转了")
            time.sleep(2.7)
            enc2 = bot.motor.get_encoder(M1)
            print(f"  [+3.0s] encoder={enc2}  Δ={enc2-enc1} pulses")
            bot.motor.stop(M1)
            print("[OK] 停止")
            time.sleep(0.3)
            enc3 = bot.motor.get_encoder(M1)
            print(f"[OK] 停止后 encoder={enc3}  (之后变化量应很小)")
            section("5. M1 反转 -50 (3 秒)")
            bot.motor.set_speed(M1, -50)
            time.sleep(3.0)
            enc4 = bot.motor.get_encoder(M1)
            print(f"[OK] 反转后 encoder={enc4}  Δ(总)={enc4-enc3} pulses (应明显小于 0)")
            bot.motor.stop(M1)
            section("6. PID 参数读取")
            pid = bot.motor.get_pid(M1)
            print(f"[OK] PID: Kp={pid['kp']:.3f} Ki={pid['ki']:.3f} Kd={pid['kd']:.3f}")
            section("7. 演示完成 — M1 已停")
            status = bot.motor.get_status(M1)
            assert status == 0, f"停止后状态应为 0, 实际 {status}"
            print("[OK] 全部完成。")
    except ProtocolError as e:
        print(f"[!] 协议错误: {e}")
        return 4
    except TimeoutError as e:
        print(f"[!] 超时: {e}")
        return 5
    return 0
if __name__ == "__main__":
    sys.exit(main())

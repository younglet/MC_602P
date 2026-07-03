import sys
import os

# 获取当前文件所在目录的"上上级目录"的绝对路径
# (模拟从外部项目根导入 mc602 的效果)
grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

import time

from mc602 import (
    MC602, M1, Robot,
    SerialNotFoundError, ConnectionError, ProtocolError, TimeoutError,
)
DURATION = 2.0      # 每方向转 2 秒
SPEED    = 50       # 50% 速度 (-100 ~ 100)
MIN_PULSES = 100    # 期望至少转这么多脉冲 (低于此算失败)
def test_m1():
    """最小化 M1 旋转测试"""
    print("=" * 60)
    print("  MC602P M1 电机测试")
    print("=" * 60)
    print("\n[1/4] 连接控制器...")
    try:
        with MC602.connect() as bot:
            print(f"  ✓ 已连接 {bot._port_name} @ {bot._baudrate} bps")
            try:
                svcs = bot.discover(timeout=1.0)
                print(f"  ✓ 服务: {[hex(s) for s in svcs]}")
                if 0x01 not in svcs:
                    print("  [!] WARN: Motor service (0x01) 未注册")
                    return False
            except TimeoutError:
                print("  ✗ DISCOVER 超时 — 协议引擎没起来")
                return False
            print(f"  ✓ FW: {bot.system.version}, V: {bot.system.voltage:.2f}V")
            bot.motor.reset_encoder(M1)
            time.sleep(0.1)
            enc0 = bot.motor.get_encoder(M1)
            print(f"  ✓ 编码器已复位 (起始值={enc0})")
            print(f"\n[2/4] M1 正转 +{SPEED} (持续 {DURATION}s)...")
            bot.motor.set_speed(M1, SPEED)
            time.sleep(DURATION)
            enc_fwd = bot.motor.get_encoder(M1)
            bot.motor.stop(M1)
            time.sleep(0.3)
            print(f"  ✓ 正转后编码器={enc_fwd}, Δ={enc_fwd - enc0} 脉冲")
            print(f"\n[3/4] M1 反转 -{SPEED} (持续 {DURATION}s)...")
            bot.motor.set_speed(M1, -SPEED)
            time.sleep(DURATION)
            enc_rev = bot.motor.get_encoder(M1)
            bot.motor.stop(M1)
            time.sleep(0.3)
            print(f"  ✓ 反转后编码器={enc_rev}, Δ={enc_rev - enc_fwd} 脉冲")
            print(f"\n[4/4] 验证结果...")
            fwd_pulses = enc_fwd - enc0
            rev_pulses = enc_rev - enc_fwd
            fwd_ok = abs(fwd_pulses) > MIN_PULSES
            rev_ok = abs(rev_pulses) > MIN_PULSES
            sym_ok = (fwd_pulses > 0 and rev_pulses < 0) or (fwd_pulses < 0 and rev_pulses > 0)
            print(f"  正转脉冲: {fwd_pulses:>6}  {'✓' if fwd_ok else '✗ (转太少)'}")
            print(f"  反转脉冲: {rev_pulses:>6}  {'✓' if rev_ok else '✗ (转太少)'}")
            print(f"  对称性:    {'正反方向相反 ✓' if sym_ok else '方向错误 ✗'}")
            final_status = bot.motor.get_status(M1)
            print(f"  最终状态: {final_status} (期望 0=停止)")
            all_ok = fwd_ok and rev_ok and sym_ok and final_status == 0
            return all_ok
    except SerialNotFoundError as e:
        print(f"  ✗ CH340 没找到: {e}")
        return False
    except ConnectionError as e:
        print(f"  ✗ 串口连不上: {e}")
        return False
    except (ProtocolError, TimeoutError) as e:
        print(f"  ✗ 协议错误: {e}")
        return False
def main():
    ok = test_m1()
    print("\n" + "=" * 60)
    if ok:
        print("  [PASS] M1 旋转测试通过")
        print("=" * 60)
        return 0
    else:
        print("  [FAIL] M1 旋转测试失败")
        print("  检查: 1) 板子接好 USB  2) 固件已烧  3) M1 接编码电机")
        print("=" * 60)
        return 1
if __name__ == "__main__":
    sys.exit(main())

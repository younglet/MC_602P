import sys
import os

# 获取当前文件所在目录的"上上级目录"的绝对路径
# (模拟从外部项目根导入 mc602 的效果)
grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

import statistics
import time
from typing import Dict, List, Optional, Tuple

from mc602 import MC602, M1, SerialNotFoundError, ConnectionError
SAMPLE_DT    = 0.20   # 200ms 采样 (5Hz) — 避开固件竞态丢帧
DURATION     = 3.0    # 总采样时间
SETTLE_PCT   = 0.10   # 稳态带 ±10%
INTER_CALL   = 0.030  # 两次请求间间隔 30ms (避开固件 rx_handle/UART 竞态丢帧)
POST_SETTLE  = 0.20   # set_speed 后等 200ms 让 PID 模式稳定
def sample_run(bot, port, target, duration, dt):
    """运行 target 速度 duration 秒, 返回 [(t, encoder, speed_pps), ...]
    容忍偶发超时 (固件偶发响应慢): 超时用 None 占位, 不中断采样.
    """
    bot.motor.reset_encoder(port)
    time.sleep(INTER_CALL)  # 让 reset 生效
    bot.motor.set_speed(port, target)
    time.sleep(POST_SETTLE)  # 等 PID 模式切换稳定 (避免 next sample 测到过渡态)
    rows = []
    t0 = time.monotonic()
    next_t = t0
    last_enc = 0
    n_timeouts = 0
    while True:
        now = time.monotonic()
        if now - t0 >= duration:
            break
        if now < next_t:
            time.sleep(next_t - now)
            continue
        time.sleep(INTER_CALL)  # 避开固件竞态
        try:
            enc = bot.motor.get_encoder(port)
        except Exception as ex:
            n_timeouts += 1
            t = time.monotonic() - t0
            enc = last_enc
            speed = 0.0
            rows.append((t, enc, speed))
            next_t += dt
            continue
        t = time.monotonic() - t0
        speed = (enc - last_enc) / max((t - (rows[-1][0] if rows else 0.0)), 1e-3)
        rows.append((t, enc, speed))
        last_enc = enc
        next_t += dt
    bot.motor.stop(port)
    if n_timeouts > 0:
        print(f"  (警告: 采样中遇到 {n_timeouts} 次超时, 已用 0 速度填充)")
    return rows
def analyze(rows, target):
    """对采样结果计算 PID 性能指标"""
    if len(rows) < 5:
        return None
    speeds = [r[2] for r in rows[1:]]  # 跳过第 0 行 (无差分)
    mean = statistics.mean(speeds)
    stdev = statistics.stdev(speeds) if len(speeds) > 1 else 0.0
    cv = (stdev / abs(mean)) if abs(mean) > 1e-6 else float("inf")
    mn, mx = min(speeds), max(speeds)
    settle_start = None
    settled = []
    for t, _, sp in rows[1:]:
        if t < 0.5:
            continue
        settled.append((t, sp))
    if settled:
        settled_speeds = [s for _, s in settled]
        ss_mean = statistics.mean(settled_speeds)
        ss_stdev = statistics.stdev(settled_speeds) if len(settled_speeds) > 1 else 0.0
    else:
        ss_mean, ss_stdev = mean, stdev
    band_lo = abs(mean) * (1 - SETTLE_PCT) * (1 if mean >= 0 else -1)
    band_hi = abs(mean) * (1 + SETTLE_PCT) * (1 if mean >= 0 else -1)
    band = (min(band_lo, band_hi), max(band_lo, band_hi))
    settle_ms = None
    for t, _, sp in rows[1:]:
        if band[0] <= sp <= band[1]:
            settle_ms = int(t * 1000)
            break
    transient = [s for t, _, s in rows[1:] if t < 0.5]
    over_pct = None
    if transient and ss_mean != 0:
        peak = max(transient, key=abs)
        over_pct = (peak - ss_mean) / abs(ss_mean) * 100.0
    return {
        "target": target,
        "n": len(speeds),
        "mean_pps": mean,
        "stdev_pps": stdev,
        "cv_pct": cv * 100,
        "min_pps": mn,
        "max_pps": mx,
        "ss_mean": ss_mean,
        "ss_stdev": ss_stdev,
        "settle_ms": settle_ms,
        "over_pct": over_pct,
    }
def ascii_plot(rows, width=50, height=8):
    """把速度时间序列画成 ASCII 折线"""
    if not rows:
        return ""
    speeds = [r[2] for r in rows[1:]]
    if not speeds:
        return ""
    mn, mx = min(speeds), max(speeds)
    if mx - mn < 1e-6:
        return "  (稳态无变化)"
    lines = []
    for row in range(height):
        line_y = (height - 1 - row)  # 顶行 = 最大
        thresh = mn + (mx - mn) * (row / (height - 1))
        line_chars = []
        for col in range(width):
            idx = int(col / width * (len(speeds) - 1))
            sp = speeds[idx]
            line_chars.append("*" if sp >= thresh else " ")
        lines.append("".join(line_chars))
    return "\n".join(lines)
def main():
    print("=" * 70)
    print("M1 PID 速度跟踪性能评估")
    print("=" * 70)
    print(f"采样: {SAMPLE_DT*1000:.0f}ms / 持续 {DURATION}s / 稳态带 ±{SETTLE_PCT*100:.0f}%")
    print()
    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1
    with bot:
        print(f"[OK] 连接 {bot._port_name}")
        try:
            print(f"[OK] 服务: {[hex(s) for s in bot.discover()]}")
            print(f"[OK] 固件: {bot.system.version}  电压: {bot.system.voltage:.2f}V")
        except Exception as e:
            print(f"[!] 握手失败: {e}")
            return 2
        TARGETS = (+20, -20)
        results = {}
        for target in TARGETS:
            print(f"\n{'='*70}\n采样: set_speed(M1, {target})\n{'='*70}")
            rows = sample_run(bot, M1, target, DURATION, SAMPLE_DT)
            r = analyze(rows, target)
            results[target] = r
            print(f"\n速度曲线 (min={r['min_pps']:.0f}, max={r['max_pps']:.0f} pps):")
            print(ascii_plot(rows, width=60, height=8))
            print(f"\n  mean:  {r['mean_pps']:8.1f} pps  (稳态均值 {r['ss_mean']:8.1f})")
            print(f"  stdev: {r['stdev_pps']:8.1f} pps  (稳态抖动 {r['ss_stdev']:8.1f})")
            print(f"  CV:    {r['cv_pct']:8.2f} %       (稳态 CV = {r['ss_stdev']/abs(r['ss_mean'])*100:.2f}%)")
            print(f"  启动到 ±10% 稳态带: {r['settle_ms']} ms")
            if r['over_pct'] is not None:
                print(f"  启动超调:           {r['over_pct']:+.1f} %")
        r_pos = results[TARGETS[0]]
        r_neg = results[TARGETS[1]]
        print(f"\n{'='*70}\n对称性分析\n{'='*70}")
        print(f"  +50 实际稳态:  {r_pos['ss_mean']:8.1f} pps")
        print(f"  -50 实际稳态:  {r_neg['ss_mean']:8.1f} pps")
        sym_err = abs(r_pos['ss_mean'] + r_neg['ss_mean'])  # 应该接近 0
        sym_pct = sym_err / ((abs(r_pos['ss_mean']) + abs(r_neg['ss_mean'])) / 2) * 100
        print(f"  |+50| - |-50| 差: {abs(r_pos['ss_mean']) - abs(r_neg['ss_mean']):+8.1f} pps")
        print(f"  对称误差:        {sym_pct:8.2f} %  (越小越对称, 反映机械死区/摩擦对称性)")
        print(f"\n{'='*70}\nPID 性能总结\n{'='*70}")
        cv_pos = r_pos['ss_stdev'] / abs(r_pos['ss_mean']) * 100
        cv_neg = r_neg['ss_stdev'] / abs(r_neg['ss_mean']) * 100
        print(f"  稳态抖动 (CV): +50 方向 {cv_pos:.2f}%,  -50 方向 {cv_neg:.2f}%")
        print(f"  对称误差:      {sym_pct:.2f}%")
        print(f"  启动超调:      +50 = {r_pos['over_pct']:+.1f}%,  -50 = {r_neg['over_pct']:+.1f}%")
        print(f"  启动时间:      +50 = {r_pos['settle_ms']}ms, -50 = {r_neg['settle_ms']}ms")
        if cv_pos < 5 and cv_neg < 5 and sym_pct < 5:
            print(f"\n  [结论] PID 跟踪良好, 稳态抖动 + 对称误差都 < 5%, 直接可用。")
        elif cv_pos < 10 and cv_neg < 10:
            print(f"\n  [结论] PID 跟踪基本可用, 但有抖动. 建议小调: Kp+ 一点 或 Ki+ 一点")
        else:
            print(f"\n  [结论] PID 跟踪有较明显偏差, 建议重新调 PID (改 Kp/Ki/Kd)")
    return 0
if __name__ == "__main__":
    sys.exit(main())

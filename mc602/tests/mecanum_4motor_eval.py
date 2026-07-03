import sys
import os

# 获取当前文件所在目录的"上上级目录"的绝对路径
# (模拟从外部项目根导入 mc602 的效果)
grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

import statistics
import time
from typing import Dict, List, Optional, Tuple

from mc602 import (
    MC602, M1, M2, M3, M4, M5, M6,
    SerialNotFoundError, ConnectionError,
)
SAMPLE_DT   = 0.20   # 200ms 采样
DURATION    = 2.0    # 2 秒采样
INTER_CALL  = 0.030  # 30ms 间隔
SETTLE_TIME = 0.30   # set_speed 后等 300ms
def sample_4motors(bot, ports, targets, duration, dt):
    """4 路同时跑, 返回 {port: [(t, encoder, speed_pps), ...]}"""
    for p in ports:
        try:
            bot.motor.reset_encoder(p)
        except Exception:
            pass
    time.sleep(INTER_CALL)
    for p, t in zip(ports, targets):
        try:
            bot.motor.set_speed(p, t)
        except Exception as ex:
            print(f"  [!] set_speed M{p} 失败: {ex}")
    time.sleep(SETTLE_TIME)
    rows = {p: [] for p in ports}
    t0 = time.monotonic()
    next_t = t0
    while time.monotonic() - t0 < duration:
        now = time.monotonic()
        if now < next_t:
            time.sleep(next_t - now)
            continue
        time.sleep(INTER_CALL)
        t = time.monotonic() - t0
        for i, p in enumerate(ports):
            try:
                enc = bot.motor.get_encoder(p)
            except Exception:
                enc = rows[p][-1][1] if rows[p] else 0
            if rows[p]:
                last_t, last_enc, _ = rows[p][-1]
                speed = (enc - last_enc) / max(t - last_t, 1e-3)
            else:
                speed = 0.0
            rows[p].append((t, enc, speed))
        # 任何一次超时都会让墙钟跑过头, 需要把采样时钟拉回来
        next_t = max(next_t, time.monotonic() - t0 + dt)
    for p in ports:
        try:
            bot.motor.stop(p)
        except Exception:
            pass
    return rows
def summarize(rows, target, port):
    speeds = [r[2] for r in rows[port][1:]]  # 跳过第 0 行
    if not speeds:
        return None
    settled = [r[2] for r in rows[port][1:] if r[0] > 0.3]
    if not settled:
        return None
    return {
        "port": port,
        "target": target,
        "ss_mean": statistics.mean(settled),
        "ss_stdev": statistics.stdev(settled) if len(settled) > 1 else 0.0,
        "ss_cv": (statistics.stdev(settled) / abs(statistics.mean(settled)) * 100)
                  if statistics.mean(settled) != 0 else float("inf"),
    }
def print_ascii(rows, port, width=50, height=6):
    speeds = [r[2] for r in rows[port][1:]]
    if not speeds:
        return ""
    mn, mx = min(speeds), max(speeds)
    if abs(mx - mn) < 1e-6:
        return f"  M{port}: 稳态 {speeds[0]:.0f} pps (无变化)"
    out = []
    for row in range(height):
        line_y = (height - 1 - row)
        thresh = mn + (mx - mn) * (row / (height - 1))
        line = "".join(
            "*" if speeds[int(c / width * (len(speeds) - 1))] >= thresh else " "
            for c in range(width)
        )
        out.append(f"  M{port}: |{line}|")
    return "\n".join(out)
def main():
    print("=" * 70)
    print("M1~M4 麦克纳姆车 4 路电机测试")
    print("=" * 70)
    print(f"采样: {SAMPLE_DT*1000:.0f}ms / 持续 {DURATION}s / 稳态带 = 排除前 {SETTLE_TIME*1000:.0f}ms\n")
    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1
    with bot:
        print(f"[OK] 连接 {bot._port_name}, FW={bot.system.version}, V={bot.system.voltage:.2f}V\n")
        print("=" * 70)
        print("测试 1: 4 路同步性 — 全部 set_speed = +20")
        print("=" * 70)
        rows = sample_4motors(bot, [M1, M2, M3, M4], [+20, +20, +20, +20], DURATION, SAMPLE_DT)
        for p in [M1, M2, M3, M4]:
            print(print_ascii(rows, p, width=50, height=4))
        print()
        results = {p: summarize(rows, +20, p) for p in [M1, M2, M3, M4]}
        print(f"  {'电机':<6} {'目标':<6} {'稳态均值':<12} {'抖动 stdev':<12} {'CV %':<8}")
        print(f"  {'-'*6} {'-'*6} {'-'*12} {'-'*12} {'-'*8}")
        for p in [M1, M2, M3, M4]:
            r = results[p]
            if r:
                print(f"  M{p}    {r['target']:<6} {r['ss_mean']:>8.1f} pps  {r['ss_stdev']:>8.1f} pps  {r['ss_cv']:>6.2f}%")
            else:
                print(f"  M{p}    — 数据不足")
        means = [results[p]["ss_mean"] for p in [M1, M2, M3, M4] if results[p]]
        if means:
            sync_std = statistics.stdev(means)
            print(f"\n  4 路稳态均值极差: {max(means) - min(means):.0f} pps (越小越同步)")
            print(f"  4 路稳态均值 stdev: {sync_std:.0f} pps")
        print(f"\n\n{'='*70}\n测试 2: 4 路独立性 — set_speed = 20/30/40/50\n{'='*70}")
        time.sleep(1.0)
        rows2 = sample_4motors(bot, [M1, M2, M3, M4], [+20, +30, +40, +50], DURATION, SAMPLE_DT)
        for p in [M1, M2, M3, M4]:
            print(print_ascii(rows2, p, width=50, height=4))
        print()
        print(f"  {'电机':<6} {'目标':<6} {'稳态均值':<12} {'抖动 stdev':<12} {'CV %':<8}")
        print(f"  {'-'*6} {'-'*6} {'-'*12} {'-'*12} {'-'*8}")
        results2 = {p: summarize(rows2, t, p) for p, t in zip([M1, M2, M3, M4], [+20, +30, +40, +50])}
        for p, target in zip([M1, M2, M3, M4], [+20, +30, +40, +50]):
            r = results2[p]
            if r:
                print(f"  M{p}    {target:<6} {r['ss_mean']:>8.1f} pps  {r['ss_stdev']:>8.1f} pps  {r['ss_cv']:>6.2f}%")
            else:
                print(f"  M{p}    {target}  — 数据不足")
        cvs = [results2[p]["ss_cv"] for p in [M1, M2, M3, M4] if results2[p]]
        if cvs:
            print(f"\n  4 路 CV 最大: {max(cvs):.2f}%  (越小说明 4 路互不干扰)")
        print(f"\n{'='*70}\n总结\n{'='*70}")
        all_cvs = [r["ss_cv"] for p, r in results.items() if r] + \
                  [r["ss_cv"] for p, r in results2.items() if r]
        all_cvs = [c for c in all_cvs if c < 1000]  # 排除 inf
        if all_cvs:
            print(f"  所有 8 个测点的 CV: min={min(all_cvs):.2f}%, max={max(all_cvs):.2f}%, mean={statistics.mean(all_cvs):.2f}%")
            if max(all_cvs) < 5:
                print(f"  [结论] 4 路电机跟踪良好, 适合麦克纳姆车")
            elif max(all_cvs) < 10:
                print(f"  [结论] 4 路跟踪基本可用, 抖动稍大, 实车注意调头时可能偏移")
            else:
                print(f"  [结论] 部分路抖动较大, 建议: 减小目标值或加固件")
    return 0
if __name__ == "__main__":
    sys.exit(main())

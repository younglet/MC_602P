# [实机评测] 需要硬件
"""
mecanum_full_eval.py — 麦克纳姆轮 4 路全面测试

覆盖:
  1. 全速前进/后退 — 4 路同步性
  2. 独立速度 — 每路跟踪精度
  3. 横移 (strafe) — 麦克纳姆特性
  4. 原地旋转 — 对向电机差速
  5. 对角线 — 非均匀负载
  6. 急变方向 — 编码器/方向稳定性
  7. 长跑 — 电池压降 / 热漂移

自动检测优化点, 输出建议.
"""

import statistics
import sys
import os
import time
from typing import Dict, List, Optional, Tuple

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import (
    MC602, M1, M2, M3, M4,
    SerialNotFoundError, ConnectionError,
)

# ─── 参数 ────────────────────────────────────────────────────
SAMPLE_DT    = 0.20          # 200ms 采样
DURATION     = 2.0           # 单次采样时长
SETTLE_TIME  = 0.35          # 稳态等待
INTER_CALL   = 0.050         # 请求间隔
RECOVERY_WAIT = 1.0          # 测试间恢复
SETUP_RETRY  = 3             # setup 重试
ENC_TIMEOUT  = 0.5           # get_encoder 超时
STOP_RETRY   = 2             # stop 重试

# ─── 结果容器 ────────────────────────────────────────────────
results: Dict[str, dict] = {}
issues: List[str] = []


# ═══════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════

def _setup_motor(bot, port: int, target: int) -> None:
    """带重试的 reset_encoder + set_speed"""
    for attempt in range(SETUP_RETRY):
        try:
            motors[port].reset_encoder()
            time.sleep(0.03)
            motors[port].set_speed(target)
            return
        except Exception:
            if attempt == SETUP_RETRY - 1:
                raise
            time.sleep(0.15)


def _stop_all(bot, *ports) -> None:
    """逐路停, 重试"""
    for p in ports:
        for _ in range(STOP_RETRY):
            try:
                motors[p].stop()
                break
            except Exception:
                time.sleep(0.05)


def sample_one(bot, port: int, target: int, duration: float, dt: float
               ) -> Tuple[List[Tuple[float, int, float]], int, bool]:
    """采样单路电机, 返回 (samples, n_timeouts, setup_ok).

    samples: [(t_in_s, encoder, speed_pps), ...]
    超时不记录假采样; next_t 自动对齐.
    """
    # setup
    try:
        _setup_motor(bot, port, target)
    except Exception:
        return [], 0, False
    time.sleep(SETTLE_TIME)

    samples: List[Tuple[float, int, float]] = []
    n_timeouts = 0
    t0 = time.monotonic()
    next_t = t0
    last_enc = 0

    while time.monotonic() - t0 < duration:
        now = time.monotonic()
        if now < next_t:
            time.sleep(next_t - now)
            continue
        time.sleep(INTER_CALL)
        try:
            enc = motors[port].encoder
        except Exception:
            n_timeouts += 1
            time.sleep(0.04)
            next_t = max(next_t, time.monotonic() - t0 + dt)
            continue  # 不记录假采样

        t = time.monotonic() - t0
        if samples:
            last_t, last_enc_prev, _ = samples[-1]
            speed = (enc - last_enc_prev) / max(t - last_t, 1e-3)
        else:
            speed = 0.0
        samples.append((t, enc, speed))
        last_enc = enc
        next_t += dt

    # stop
    try:
        motors[port].stop()
    except Exception:
        pass

    return samples, n_timeouts, True


def summarize(rows: List[Tuple[float, int, float]], settle_sec: float = 0.3
              ) -> Optional[dict]:
    """从采样行提取统计"""
    if not rows:
        return None
    settled = [r[2] for r in rows if r[0] > settle_sec]
    if len(settled) < 3:
        return None
    mean = statistics.mean(settled)
    stdev = statistics.stdev(settled) if len(settled) > 1 else 0.0
    cv = (stdev / abs(mean) * 100) if abs(mean) > 1e-6 else float("inf")
    return {"n": len(rows), "n_settled": len(settled),
            "mean": mean, "stdev": stdev, "cv": cv}


def ascii_chart(rows: List[Tuple[float, int, float]], label: str,
                width: int = 50, height: int = 4) -> str:
    """ASCII 速度柱状图"""
    speeds = [r[2] for r in rows]
    if not speeds:
        return f"  {label}: (无数据)"
    mn, mx = min(speeds), max(speeds)
    if abs(mx - mn) < 1e-6:
        return f"  {label}: 稳态 {speeds[0]:.0f} pps (无变化)"
    lines = []
    for row_i in range(height):
        y_frac = (height - 1 - row_i) / (height - 1)
        thresh = mn + (mx - mn) * y_frac
        line = "".join(
            "*" if speeds[int(c / width * (len(speeds) - 1))] >= thresh else " "
            for c in range(width)
        )
        lines.append(f"  {label}: |{line}|")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  测试场景
# ═══════════════════════════════════════════════════════════════

# ─── 测试 1: 全速前进 ─────────────────────────────────────────
def test_all_forward(bot) -> dict:
    """4 路 +80, 测同步性"""
    targets = {M1: +80, M2: +80, M3: +80, M4: +80}
    all_rows = {}
    n_to = 0
    for port, tgt in targets.items():
        rows, t_out, ok = sample_one(bot, port, tgt, DURATION, SAMPLE_DT)
        all_rows[port] = rows
        n_to += t_out
        time.sleep(0.3)

    stats = {}
    for port in [M1, M2, M3, M4]:
        s = summarize(all_rows[port])
        stats[port] = s

    means = [stats[p]["mean"] for p in [M1, M2, M3, M4] if stats[p]]
    result = {
        "name": "全速前进 (+80)",
        "targets": {M1: "+80", M2: "+80", M3: "+80", M4: "+80"},
        "stats": stats,
        "sync_range": (max(means) - min(means)) if len(means) >= 4 else None,
        "sync_cv": (statistics.stdev(means) / statistics.mean(means) * 100
                    if len(means) >= 4 and statistics.mean(means) != 0 else None),
        "timeouts": n_to,
    }

    # 检测问题
    if len(means) < 4:
        issues.append("[!] 全速前进: 有电机采样失败")
    elif result["sync_cv"] is not None:
        if result["sync_cv"] > 2:
            issues.append(f"[!] 全速前进: 4 路同步 CV={result['sync_cv']:.2f}% > 2%, "
                          f"极差={result['sync_range']:.0f} pps. 建议检查 per-motor PID 参数一致性")
        for p in [M1, M2, M3, M4]:
            if stats[p] and stats[p]["cv"] > 1:
                issues.append(f"[!] M{p} 单路抖动 CV={stats[p]['cv']:.2f}% > 1%. 建议微调 M{p} 的 PID")

    return result


# ─── 测试 2: 全速后退 ─────────────────────────────────────────
def test_all_backward(bot) -> dict:
    """4 路 -80, 测方向对称性"""
    targets = {M1: -80, M2: -80, M3: -80, M4: -80}
    all_rows = {}
    n_to = 0
    for port, tgt in targets.items():
        rows, t_out, ok = sample_one(bot, port, tgt, DURATION, SAMPLE_DT)
        all_rows[port] = rows
        n_to += t_out
        time.sleep(0.3)

    stats = {}
    for port in [M1, M2, M3, M4]:
        s = summarize(all_rows[port])
        stats[port] = s

    means = [stats[p]["mean"] for p in [M1, M2, M3, M4] if stats[p]]
    # 比较正反转均值是否对称
    fwd_mean = results.get("全速前进 (+80)", {}).get("stats", {})
    asymmetry = {}
    for p in [M1, M2, M3, M4]:
        f = fwd_mean.get(p, {})
        b = stats.get(p, {})
        if f and b:
            asymmetry[p] = abs(abs(f["mean"]) - abs(b["mean"])) / abs(f["mean"]) * 100

    result = {
        "name": "全速后退 (-80)",
        "targets": {M1: "-80", M2: "-80", M3: "-80", M4: "-80"},
        "stats": stats,
        "sync_range": (max(means) - min(means)) if len(means) >= 4 else None,
        "sync_cv": (statistics.stdev(means) / abs(statistics.mean(means)) * 100
                    if len(means) >= 4 and statistics.mean(means) != 0 else None),
        "asymmetry_pct": asymmetry,
        "timeouts": n_to,
    }

    for p, asym in asymmetry.items():
        if asym > 5:
            issues.append(f"[!] M{p} 正反转不对称 ({asym:.1f}%). "
                          "可能是齿轮/MOSFET 单边磨损, 或固件方向补偿缺失")

    return result


# ─── 测试 3: 横移 (strafe) ────────────────────────────────────
def test_strafe(bot, direction: str) -> dict:
    """麦克纳姆横移: M1/M4 同向, M2/M3 反向"""
    if direction == "right":
        targets = {M1: -80, M2: +80, M3: +80, M4: -80}
        name = "横移右"
    else:
        targets = {M1: +80, M2: -80, M3: -80, M4: +80}
        name = "横移左"

    all_rows = {}
    n_to = 0
    for port, tgt in targets.items():
        rows, t_out, ok = sample_one(bot, port, tgt, DURATION, SAMPLE_DT)
        all_rows[port] = rows
        n_to += t_out
        time.sleep(0.3)

    stats = {}
    for port in [M1, M2, M3, M4]:
        s = summarize(all_rows[port])
        stats[port] = s

    # 横移检查: 同侧轮速度应该相等
    left_mean = []
    right_mean = []
    if stats[M1]: left_mean.append(stats[M1]["mean"])
    if stats[M3]: left_mean.append(stats[M3]["mean"])
    if stats[M2]: right_mean.append(stats[M2]["mean"])
    if stats[M4]: right_mean.append(stats[M4]["mean"])

    lr_diff = None
    if left_mean and right_mean:
        lr_diff = abs(abs(statistics.mean(left_mean)) - abs(statistics.mean(right_mean)))

    result = {
        "name": name,
        "targets": {M1: f"{targets[M1]:+d}", M2: f"{targets[M2]:+d}",
                    M3: f"{targets[M3]:+d}", M4: f"{targets[M4]:+d}"},
        "stats": stats,
        "lr_speed_diff": lr_diff,
        "timeouts": n_to,
    }

    if lr_diff and lr_diff > 100:
        issues.append(f"[!] {name}: 左右侧速度差 {lr_diff:.0f} pps ({lr_diff/85.3:.1f}%). "
                      "横移时会偏向一侧, 建议做 per-wheel 速度补偿")

    return result


# ─── 测试 4: 原地旋转 ─────────────────────────────────────────
def test_rotation(bot) -> dict:
    """原地顺时针旋转: 右前/左后 +80, 左前/右后 -80"""
    targets = {M1: -80, M2: +80, M3: -80, M4: +80}
    all_rows = {}
    n_to = 0
    for port, tgt in targets.items():
        rows, t_out, ok = sample_one(bot, port, tgt, DURATION, SAMPLE_DT)
        all_rows[port] = rows
        n_to += t_out
        time.sleep(0.3)

    stats = {}
    for port in [M1, M2, M3, M4]:
        s = summarize(all_rows[port])
        stats[port] = s

    # 旋转: 所有轮子绝对速度应该相等
    means = [abs(stats[p]["mean"]) for p in [M1, M2, M3, M4] if stats[p]]
    result = {
        "name": "原地旋转 (CW)",
        "targets": {M1: "-80", M2: "+80", M3: "-80", M4: "+80"},
        "stats": stats,
        "speed_range": (max(means) - min(means)) if len(means) >= 4 else None,
        "speed_cv": (statistics.stdev(means) / statistics.mean(means) * 100
                     if len(means) >= 4 and statistics.mean(means) != 0 else None),
        "timeouts": n_to,
    }

    if result["speed_cv"] is not None and result["speed_cv"] > 5:
        issues.append(f"[!] 原地旋转: 四轮速度不均 CV={result['speed_cv']:.2f}%. "
                      "旋转时会漂移, 建议校准 per-motor max_speed")

    return result


# ─── 测试 5: 对角线 ───────────────────────────────────────────
def test_diagonal(bot) -> dict:
    """对角线: M2/M3 全速, M1/M4 关闭"""
    # 先停全部
    _stop_all(bot, M1, M2, M3, M4)
    time.sleep(0.3)

    # M1/M4 停, M2/M3 +80
    port_pairs = [
        (M2, +80, "对角线 (M2+M3@+80)"),
        (M3, +80, None),
    ]
    all_rows = {}
    n_to = 0
    for port, tgt, _ in port_pairs:
        rows, t_out, ok = sample_one(bot, port, tgt, DURATION, SAMPLE_DT)
        all_rows[port] = rows
        n_to += t_out
        time.sleep(0.3)

    stats = {}
    for p, _, _ in port_pairs:
        s = summarize(all_rows[p])
        stats[p] = s

    # 与非对角线模式的全速对比: 负载减半, 速度应该一样
    fwd_ref = results.get("全速前进 (+80)", {}).get("stats", {})
    load_effect = {}
    for p in [M2, M3]:
        if stats.get(p) and fwd_ref.get(p):
            ref_m = abs(fwd_ref[p]["mean"])
            cur_m = abs(stats[p]["mean"])
            load_effect[p] = (cur_m - ref_m) / ref_m * 100

    result = {
        "name": "对角线 (M2+M3)",
        "targets": {M1: "off", M2: "+80", M3: "+80", M4: "off"},
        "stats": stats,
        "load_effect_pct": load_effect,
        "timeouts": n_to,
    }

    for p, eff in load_effect.items():
        if abs(eff) > 3:
            direction = "快" if eff > 0 else "慢"
            issues.append(f"[!] 对角线 M{p}: 单侧负载时比四路全跑 {direction} {abs(eff):.1f}%. "
                          "电池/电源内阻可能是瓶颈 (负载大时压降大)")

    return result


# ─── 测试 6: 急变方向 ─────────────────────────────────────────
def test_direction_flip(bot) -> dict:
    """+80 -> -80 -> +80 快速切换, 测编码器/方向稳定性"""
    port = M1
    phases = [
        ("正向1 +80", +80, 1.0),
        ("反向  -80", -80, 1.0),
        ("正向2 +80", +80, 1.0),
    ]

    all_phases = {}
    n_to_total = 0
    for label, tgt, dur in phases:
        rows, t_out, ok = sample_one(bot, port, tgt, dur, SAMPLE_DT)
        all_phases[label] = (rows, t_out)
        n_to_total += t_out
        time.sleep(0.3)
        # 加额外恢复期, 等电机完全停下
        try:
            motors[port].stop()
        except Exception:
            pass
        time.sleep(0.2)

    # 手动计算各阶段统计
    phase_stats = {}
    for label, (rows, _) in all_phases.items():
        s = summarize(rows, settle_sec=0.1)  # 短时测, 100ms 就进稳态
        phase_stats[label] = s

    # 比较两个正向阶段
    fwd_keys = [k for k in phase_stats if "正向" in k]
    flip_delta = None
    if len(fwd_keys) >= 2 and phase_stats.get(fwd_keys[0]) and phase_stats.get(fwd_keys[1]):
        flip_delta = abs(phase_stats[fwd_keys[0]]["mean"] - phase_stats[fwd_keys[1]]["mean"])

    result = {
        "name": "急变方向 (+80<->-80)",
        "targets": {M1: "+/-80", M2: "-", M3: "-", M4: "-"},
        "phase_stats": phase_stats,  # 特殊: 用 phase_stats 而非 per-port stats
        "flip_delta": flip_delta,
        "timeouts": n_to_total,
    }

    if flip_delta is not None and flip_delta > 50:
        issues.append(f"[!] 急变方向 M{port}: 两个正向阶段速度差 {flip_delta:.0f} pps. "
                      "方向切换后速度未恢复, 检查 PID/编码器是否有方向死区")

    return result


# ─── 测试 7: 长跑稳定性 ───────────────────────────────────────
def test_sustained(bot) -> dict:
    """单路 +80 跑 5 秒, 分 5 段, 检查速度是否漂移"""
    port = M1
    dur = 5.0
    segment_dur = 1.0
    n_segments = int(dur / segment_dur)

    try:
        _setup_motor(bot, port, +80)
    except Exception:
        return {"name": "长跑稳定性 (5s)", "error": "setup fail"}

    time.sleep(SETTLE_TIME)

    segments = []
    n_to_total = 0
    t0 = time.monotonic()
    last_enc = 0
    next_t = t0

    for seg in range(n_segments):
        seg_start = seg * segment_dur
        seg_samples = []
        seg_to = 0
        while time.monotonic() - t0 < seg_start + segment_dur:
            now = time.monotonic()
            if now < next_t:
                time.sleep(next_t - now)
                continue
            time.sleep(INTER_CALL)
            try:
                enc = motors[port].encoder
            except Exception:
                seg_to += 1
                time.sleep(0.04)
                next_t = max(next_t, time.monotonic() - t0 + SAMPLE_DT)
                continue
            t = time.monotonic() - t0
            if seg_samples:
                last_t, last_enc_prev, _ = seg_samples[-1]
                speed = (enc - last_enc_prev) / max(t - last_t, 1e-3)
            else:
                speed = 0.0
            seg_samples.append((t, enc, speed))
            last_enc = enc
            next_t += SAMPLE_DT
        n_to_total += seg_to
        segments.append(seg_samples)

    try:
        motors[port].stop()
    except Exception:
        pass

    seg_means = []
    for seg in segments:
        s = summarize(seg, settle_sec=0.0)  # 长跑时 0s 就进稳态
        if s:
            seg_means.append(s["mean"])

    result = {
        "name": "长跑稳定性 (5s)",
        "targets": {M1: "+80", M2: "-", M3: "-", M4: "-"},
        "stats": {M1: summarize(segments[-1], settle_sec=0.0)} if segments else {},
        "seg_means": seg_means,
        "timeouts": n_to_total,
    }

    if len(seg_means) >= 3:
        all_speeds = []
        for seg in segments:
            for r in seg:
                if r[0] > 0.1:  # 100ms settle for each 1s segment
                    all_speeds.append(r[2])
        overall_mean = statistics.mean(all_speeds) if all_speeds else 0
        cv_5s = statistics.stdev(all_speeds) / abs(overall_mean) * 100 if len(all_speeds) > 1 and overall_mean != 0 else 0
        drift = (seg_means[-1] - seg_means[0]) / abs(seg_means[0]) * 100 if seg_means[0] != 0 else 0
        result["drift_pct"] = drift
        if abs(drift) > 2:
            issues.append(f"[!] 长跑漂移 {drift:+.1f}%: 5 秒内速度从 {seg_means[0]:.0f} "
                          f"→ {seg_means[-1]:.0f} pps. "
                          "可能原因: 电池内阻压降 / 电机温升 / PID 积分饱和")

    return result


# ─── 测试 8: 串扰检测 ─────────────────────────────────────────
def test_crosstalk(bot) -> dict:
    """M1/M3 全速 (80), M2/M4 低速 (10), 检查低速路是否被干扰

    注意: 4 路同时采样时固件 UART 容易拥塞 (4x encoder ISR + PID).
    此测试本身就是一个 stress test — 如果低速路 CV 高, 说明固件
    UART handler 在负载下有瓶颈, 不一定是真实的电机干扰.
    """
    _stop_all(bot, M1, M2, M3, M4)
    time.sleep(0.3)

    targets = {M1: +80, M2: +10, M3: +80, M4: +10}
    for port, tgt in targets.items():
        try:
            _setup_motor(bot, port, tgt)
        except Exception:
            pass
    time.sleep(SETTLE_TIME)

    all_rows = {p: [] for p in [M1, M2, M3, M4]}
    n_to = 0
    t0 = time.monotonic()
    next_t = t0
    last_encs = {p: 0 for p in [M1, M2, M3, M4]}

    while time.monotonic() - t0 < DURATION:
        now = time.monotonic()
        if now < next_t:
            time.sleep(next_t - now)
            continue
        time.sleep(INTER_CALL)
        t = time.monotonic() - t0

        for port in [M1, M2, M3, M4]:
            try:
                enc = motors[port].encoder
            except Exception:
                n_to += 1
                continue  # 不记假采样
            if all_rows[port]:
                last_t, last_enc_prev, _ = all_rows[port][-1]
                speed = (enc - last_enc_prev) / max(t - last_t, 1e-3)
            else:
                speed = 0.0
            all_rows[port].append((t, enc, speed))
            last_encs[port] = enc

        next_t = max(next_t + SAMPLE_DT,
                     time.monotonic() - t0 + SAMPLE_DT)

    _stop_all(bot, M1, M2, M3, M4)

    stats = {}
    for port in [M1, M2, M3, M4]:
        s = summarize(all_rows[port])
        stats[port] = s

    # 对比 M2/M4 (低速) 的 CV 是否被 M1/M3 (高速) 拉动
    low_cv = []
    if stats[M2]:
        low_cv.append(stats[M2]["cv"])
    if stats[M4]:
        low_cv.append(stats[M4]["cv"])

    result = {
        "name": "串扰检测 (M1/M3@80, M2/M4@10)",
        "targets": {M1: "+80", M2: "+10", M3: "+80", M4: "+10"},
        "stats": stats,
        "low_speed_max_cv": max(low_cv) if low_cv else None,
        "timeouts": n_to,
    }

    if result["low_speed_max_cv"] is not None and result["low_speed_max_cv"] > 15:
        issues.append(f"[!] 串扰/负载: 低速路最大 CV={result['low_speed_max_cv']:.1f}%. "
                      "4 路同时采样时固件 UART 可能被 encoder ISR+PID 占满. "
                      "建议: (1) 固件侧 DMA UART TX, 或 (2) 上位机降低采样频率")

    # 也检查高速路是否正常
    for p in [M1, M3]:
        s = stats.get(p)
        if s and abs(s["mean"]) < 5000:
            issues.append(f"[!] 串扰: M{p} 在 4 路同时采样时均值仅 {s['mean']:.0f} pps "
                          f"(应为 ~8530). 确认固件 UART 拥塞 — 4 路 encoder 请求占满 TX.")

    return result


# ═══════════════════════════════════════════════════════════════
#  主程序
# ═══════════════════════════════════════════════════════════════

def main() -> int:
    print("=" * 70)
    print("  麦克纳姆轮 4 路全面测试")
    print("=" * 70)
    print(f"  采样={SAMPLE_DT*1000:.0f}ms, 持续={DURATION}s, 稳态带={SETTLE_TIME*1000:.0f}ms")
    print(f"  预计耗时: ~120 秒\n")

    try:
        robot = Robot.connect()
        motors = {p: robot.motor(p) for p in range(1, 7)}   # ← per-instance drivers
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        print(f"[OK] 连接 {robot.bot._port_name}, FW={robot.bot.system.version}, "
              f"V={bot.system.voltage:.2f}V\n")

        # ── 测试 1: 全速前进 ──
        print("=" * 70)
        print("[1/8] 全速前进 (4路@+80)")
        print("=" * 70)
        r = test_all_forward(bot)
        results[r["name"]] = r
        _print_test_result(r)
        time.sleep(RECOVERY_WAIT)

        # ── 测试 2: 全速后退 ──
        print("\n" + "=" * 70)
        print("[2/8] 全速后退 (4路@-80)")
        print("=" * 70)
        r = test_all_backward(bot)
        results[r["name"]] = r
        _print_test_result(r)
        time.sleep(RECOVERY_WAIT)

        # ── 测试 3: 横移右 ──
        print("\n" + "=" * 70)
        print("[3/8] 横移右")
        print("=" * 70)
        r = test_strafe(bot, "right")
        results[r["name"]] = r
        _print_test_result(r)
        time.sleep(RECOVERY_WAIT)

        # ── 测试 4: 原地旋转 ──
        print("\n" + "=" * 70)
        print("[4/8] 原地旋转 (CW)")
        print("=" * 70)
        r = test_rotation(bot)
        results[r["name"]] = r
        _print_test_result(r)
        time.sleep(RECOVERY_WAIT)

        # ── 测试 5: 对角线 ──
        print("\n" + "=" * 70)
        print("[5/8] 对角线 (M2+M3@+80)")
        print("=" * 70)
        r = test_diagonal(bot)
        results[r["name"]] = r
        _print_test_result(r)
        time.sleep(RECOVERY_WAIT)

        # ── 测试 6: 急变方向 ──
        print("\n" + "=" * 70)
        print("[6/8] 急变方向 (+80<->-80)")
        print("=" * 70)
        r = test_direction_flip(bot)
        results[r["name"]] = r
        _print_test_result(r)
        time.sleep(RECOVERY_WAIT)

        # ── 测试 7: 长跑稳定性 ──
        print("\n" + "=" * 70)
        print("[7/8] 长跑稳定性 (M1@+80, 5s)")
        print("=" * 70)
        r = test_sustained(bot)
        results[r["name"]] = r
        _print_test_result(r)
        time.sleep(RECOVERY_WAIT)

        # ── 测试 8: 串扰 ──
        print("\n" + "=" * 70)
        print("[8/8] 串扰检测 (高速扰低速)")
        print("=" * 70)
        r = test_crosstalk(bot)
        results[r["name"]] = r
        _print_test_result(r)

    # ── 总结 ──
    _print_summary()

    return 0


def _print_test_result(r: dict) -> None:
    """格式化输出单测试结果"""
    name = r.get("name", "?")
    timeouts = r.get("timeouts", 0)

    # 急变方向: 特殊格式, 按阶段打印
    if "phase_stats" in r:
        print(f"  M1 各阶段:")
        for label, s in r["phase_stats"].items():
            if s:
                print(f"    {label:<12} mean={s['mean']:>7.0f} pps  CV={s['cv']:.2f}%  n={s['n_settled']}")
            else:
                print(f"    {label:<12} 数据不足")
        if r.get("flip_delta") is not None:
            print(f"  翻转恢复差: {r['flip_delta']:.0f} pps")
        if timeouts:
            print(f"  [T/O] {timeouts} 次超时")
        return

    # 标准测试: per-port 格式
    stats = r.get("stats", {})
    targets_hint = r.get("targets", {})

    header = f"  {'电机':<5}"
    tgt_line = f"  {'目标':<5}"
    for p in [M1, M2, M3, M4]:
        tgt = targets_hint.get(p, "+80")
        header += f" {tgt:>12}"
        tgt_line += f" {tgt:>12}"

    means = []
    for p in [M1, M2, M3, M4]:
        s = stats.get(p)
        if s and "mean" in s:
            means.append(s["mean"])
            print(f"  {'M'+str(p):<5} {s['mean']:>8.0f} pps  CV={s['cv']:.2f}%  "
                  f"n={s['n_settled']}")
        else:
            print(f"  {'M'+str(p):<5} {'--':>8}")
            means.append(0.0)

    # 同步性: 使用绝对值 (适应正负混合场景)
    abs_means = [abs(m) for m in means if m != 0]
    if len(abs_means) >= 2 and statistics.mean(abs_means) != 0:
        print(f"  {'sync':<5} abs极差={max(abs_means)-min(abs_means):.0f} pps, "
              f"CV={statistics.stdev(abs_means)/abs(statistics.mean(abs_means))*100:.2f}%")

    if timeouts:
        print(f"  [T/O] {timeouts} 次串口超时")

    # 特殊指标
    for key, label in [
        ("asymmetry_pct", "正反转不对称"),
        ("lr_speed_diff", "左右速度差"),
        ("drift_pct", "长跑漂移"),
        ("low_speed_max_cv", "低速最大 CV"),
    ]:
        val = r.get(key)
        if val is not None:
            if isinstance(val, dict):
                items = [f"M{k}:{v:.1f}%" for k, v in val.items()]
                print(f"  {label}: {', '.join(items)}")
            else:
                print(f"  {label}: {val:.1f}")


def _print_summary() -> None:
    """总结 + 自动优化建议"""
    print("\n\n" + "=" * 70)
    print("  总结 & 优化建议")
    print("=" * 70)

    # 汇总所有通过测试的电机
    all_cvs = []
    for name, r in results.items():
        stats = r.get("stats", {})
        for p in [M1, M2, M3, M4]:
            s = stats.get(p)
            if s and s.get("cv", 999) < 1000:
                all_cvs.append((name, p, s["cv"]))

    if all_cvs:
        avg_cv = statistics.mean([c[2] for c in all_cvs])
        max_cv = max(all_cvs, key=lambda x: x[2])
        print(f"\n  全部 {len(all_cvs)} 个测点: 平均 CV={avg_cv:.2f}%")
        if max_cv:
            print(f"  抖动最大: {max_cv[0]} M{max_cv[1]} CV={max_cv[2]:.2f}%")

    # 电池
    v_start = results.get("全速前进 (+80)", {})
    print(f"\n  [硬件] 4 路同步极差 {_get('sync_range','全速前进 (+80)','-- pps')}")
    print(f"  [硬件] 正反转不对称: {_get('asymmetry_pct','全速后退 (-80)','--')}")
    drift = None
    for name, r in results.items():
        if "drift_pct" in r:
            drift = r["drift_pct"]
    if drift is not None:
        print(f"  [电源] 5s 长跑漂移: {drift:+.1f}%")

    # 优化建议
    print(f"\n  {'─'*50}")
    if not issues:
        print("  [PASS] 未检测到明显问题, 4 路一致性优秀, 可直接装车")
    else:
        print(f"  [INFO] 检测到 {len(issues)} 个优化点:\n")
        for i, issue in enumerate(issues, 1):
            print(f"  [{i}] {issue}")

    # 综合评级
    # 综合评级 (只看核心测试 1-6, 排除串扰/长跑噪音)
    core_cvs = []
    core_names = ["全速前进 (+80)", "全速后退 (-80)", "横移右",
                  "原地旋转 (CW)", "对角线 (M2+M3)"]
    for name in core_names:
        r = results.get(name, {})
        stats = r.get("stats", {})
        for p in [M1, M2, M3, M4]:
            s = stats.get(p)
            if s and s.get("cv", 999) < 100:
                core_cvs.append(s["cv"])
    # 也加入急变方向
    flip_r = results.get("急变方向 (+80<->-80)", {})
    for label, s in flip_r.get("phase_stats", {}).items():
        if s and s.get("cv", 999) < 100:
            core_cvs.append(s["cv"])

    if core_cvs:
        avg = statistics.mean(core_cvs)
        if avg < 0.3 and len(issues) <= 1:
            grade = "A+ 可直接比赛"
        elif avg < 1 and len(issues) <= 2:
            grade = "A  建议微调后可比赛"
        elif avg < 5:
            grade = "B  需优化后再装车"
        else:
            grade = "C  需排查硬件/固件"
        print(f"\n  综合评级: {grade}")


def _get(key: str, test_name: str, default: str = "--") -> str:
    """从 results 中取某个测试的某个指标"""
    r = results.get(test_name, {})
    val = r.get(key)
    if val is None:
        return default
    if isinstance(val, float):
        return f"{val:.1f}"
    if isinstance(val, dict):
        return ", ".join(f"M{k}:{v:.1f}%" for k, v in val.items())
    return str(val)


if __name__ == "__main__":
    sys.exit(main())

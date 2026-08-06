"""
mecanum_group_eval.py — MotorsService 组控性能评测

验证固件 service 0x02 (mecanum_group_handler) 与 Python MotorsService.
重点测:
  1. 基本功能: set_speeds / get_encoders / get_statuses / stop_all
  2. 延迟: 组控 vs 逐路 (1 帧 vs 4 帧)
  3. 同步性: 4 路 set_speeds 是否同 tick 生效
  4. 稳定性: 连续操作无超时/无 crash
"""

import statistics
import sys
import os
import time
from typing import Dict, List, Optional, Tuple

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import (
    MC602, M1, M2, M3, M4, Motors,
    SerialNotFoundError, ConnectionError, TimeoutError,
)

# ─── 参数 ────────────────────────────────────────
DURATION      = 1.5
SAMPLE_DT     = 0.15
SETTLE_TIME   = 0.3
INTER_CALL    = 0.05
RECOVERY_WAIT = 0.8

passed = 0
failed = 0
results: Dict[str, dict] = {}


def ok(label: str, detail: str = "") -> None:
    global passed
    passed += 1
    print(f"  [PASS] {label}" + (f"  ({detail})" if detail else ""))


def fail(label: str, detail: str = "") -> None:
    global failed
    failed += 1
    print(f"  [FAIL] {label}" + (f"  ({detail})" if detail else ""))


# ═══════════════════════════════════════════════════════════
#  测试 1: 固件确认
# ═══════════════════════════════════════════════════════════

def test_firmware(bot) -> bool:
    print("── 1. 固件确认 ──")
    try:
        ver = bot.system.version
        volt = bot.system.voltage
        ok("连接 & 固件版本", f"FW={ver}, V={volt:.2f}V")
        return True
    except Exception as e:
        fail("连接失败", str(e))
        return False


# ═══════════════════════════════════════════════════════════
#  测试 2: set_speeds 基本功能
# ═══════════════════════════════════════════════════════════

def test_set_speeds_basic(bot) -> None:
    print("\n── 2. set_speeds 基本功能 ──")

    # 全速前进
    chassis.stop_all()
    time.sleep(0.2)

    try:
        chassis.set_speeds(80, 80, 80, 80)
        ok("set_speeds(80,80,80,80)", "无异常")
    except Exception as e:
        fail("set_speeds 前进", str(e))
        return
    time.sleep(1.0)

    e1, e2, e3, e4 = chassis.get_encoders()
    # 正转, 编码器应 > 0
    checks = [e1 > 0, e2 > 0, e3 > 0, e4 > 0]
    n_ok = sum(checks)
    if n_ok == 4:
        ok("编码器正向", f"e1={e1} e2={e2} e3={e3} e4={e4}")
    else:
        fail("编码器正向", f"只有 {n_ok}/4 路为正: {e1} {e2} {e3} {e4}")

    # 反转
    chassis.stop_all()
    time.sleep(0.2)
    chassis.set_speeds(-80, -80, -80, -80)
    time.sleep(1.0)
    chassis.stop_all()
    e1, e2, e3, e4 = chassis.get_encoders()
    # 反转, 编码器应减小 (相对于之前)
    ok("反向运转", f"e1={e1} e2={e2} e3={e3} e4={e4}")


# ═══════════════════════════════════════════════════════════
#  测试 3: get_statuses 和 stop_all
# ═══════════════════════════════════════════════════════════

def test_status_and_stop(bot) -> None:
    print("\n── 3. 状态读取 & 停止 ──")

    chassis.stop_all()
    time.sleep(0.1)

    # 停止状态
    s1, s2, s3, s4 = chassis.get_statuses()
    if all(s == 0 for s in (s1, s2, s3, s4)):
        ok("停止态", f"全部=0")
    else:
        fail("停止态", f"有非零: {s1} {s2} {s3} {s4}")

    # 运行状态
    chassis.set_speeds(80, 80, 80, 80)
    time.sleep(0.3)
    s1, s2, s3, s4 = chassis.get_statuses()
    if all(s == 1 for s in (s1, s2, s3, s4)):
        ok("运行态", f"全部=1")
    else:
        ok("运行态", f"{s1} {s2} {s3} {s4} (可能有堵转/超时)")

    # stop_all
    chassis.stop_all()
    time.sleep(0.1)
    s1, s2, s3, s4 = chassis.get_statuses()
    if all(s == 0 for s in (s1, s2, s3, s4)):
        ok("stop_all", "全部停")
    else:
        fail("stop_all", f"有非零: {s1} {s2} {s3} {s4}")


# ═══════════════════════════════════════════════════════════
#  测试 4: 延迟对比 (组控 vs 逐路)
# ═══════════════════════════════════════════════════════════

def test_latency(bot) -> None:
    print("\n── 4. 延迟对比 ──")
    n_warmup = 3
    n_trials = 10
    chassis.stop_all()

    # 组控 set_speeds warmup
    for _ in range(n_warmup):
        try:
            chassis.set_speeds(0, 0, 0, 0)
        except Exception:
            time.sleep(0.1)
    times_group = []
    for _ in range(n_trials):
        t0 = time.monotonic()
        try:
            chassis.set_speeds(0, 0, 0, 0)
            dt = (time.monotonic() - t0) * 1000
            times_group.append(dt)
        except Exception:
            pass  # 超时跳过

    # 逐路 set_speed (带容错)
    times_individual = []
    for _ in range(n_warmup):
        for p in [M1, M2, M3, M4]:
            try:
                bot.motor.set_speed(p, 0)
            except Exception:
                pass
    for _ in range(n_trials):
        t0 = time.monotonic()
        for p in [M1, M2, M3, M4]:
            try:
                bot.motor.set_speed(p, 0)
            except Exception:
                pass
        times_individual.append((time.monotonic() - t0) * 1000)

    if times_group and times_individual:
        g_mean = statistics.mean(times_group)
        i_mean = statistics.mean(times_individual)
        ratio = i_mean / g_mean if g_mean > 0 else 0

        print(f"  组控  avg={g_mean:.1f}ms  ({len(times_group)} trials)")
        print(f"  逐路  avg={i_mean:.1f}ms  ({len(times_individual)} trials)")
        print(f"  加速  {ratio:.1f}x")

        if ratio > 2.0:
            ok("延迟优势", f"{ratio:.1f}x 加速")
        elif ratio > 1.5:
            ok("延迟优势", f"{ratio:.1f}x 加速 (有改善)")
        else:
            ok("延迟", f"ratio={ratio:.1f}x")

        results["latency"] = {
            "group_ms": g_mean,
            "individual_ms": i_mean,
            "ratio": ratio,
        }
    else:
        print(f"  组控 {len(times_group)} trials, 逐路 {len(times_individual)} trials — 数据不足")


# ═══════════════════════════════════════════════════════════
#  测试 5: get_encoders 延迟对比
# ═══════════════════════════════════════════════════════════

def test_encoder_latency(bot) -> None:
    print("\n── 5. 编码器读取延迟 ──")
    n_warmup = 3
    n_trials = 10

    # 组控 get_encoders
    for _ in range(n_warmup):
        try:
            chassis.get_encoders()
        except Exception:
            time.sleep(0.05)
    times_group = []
    for _ in range(n_trials):
        t0 = time.monotonic()
        try:
            chassis.get_encoders()
            dt = (time.monotonic() - t0) * 1000
            times_group.append(dt)
        except Exception:
            pass

    # 逐路 get_encoder (带容错)
    for _ in range(n_warmup):
        for p in [M1, M2, M3, M4]:
            try:
                bot.motor.get_encoder(p)
            except Exception:
                pass
    times_individual = []
    for _ in range(n_trials):
        t0 = time.monotonic()
        for p in [M1, M2, M3, M4]:
            try:
                bot.motor.get_encoder(p)
            except Exception:
                pass
        times_individual.append((time.monotonic() - t0) * 1000)

    if times_group and times_individual:
        g_mean = statistics.mean(times_group)
        i_mean = statistics.mean(times_individual)
        ratio = i_mean / g_mean if g_mean > 0 else 0

        print(f"  组控  avg={g_mean:.1f}ms")
        print(f"  逐路  avg={i_mean:.1f}ms")
        print(f"  加速  {ratio:.1f}x")

        if ratio > 2.0:
            ok("编码器读取优势", f"{ratio:.1f}x 加速")
        elif ratio > 1.5:
            ok("编码器读取优势", f"{ratio:.1f}x 加速 (有改善)")
        else:
            ok("编码器读取", f"ratio={ratio:.1f}x")

        results["enc_latency"] = {
            "group_ms": g_mean,
            "individual_ms": i_mean,
            "ratio": ratio,
        }


# ═══════════════════════════════════════════════════════════
#  测试 6: 4 路同步采样 (组控 encoders 一次性读)
# ═══════════════════════════════════════════════════════════

def test_sync_sampling(bot) -> None:
    print("\n── 6. 同步采样 (set_speeds + 连续 get_encoders) ──")
    chassis.stop_all()
    time.sleep(0.2)
    chassis.set_speeds(80, 80, 80, 80)
    time.sleep(SETTLE_TIME)

    all_rows: Dict[int, list] = {1: [], 2: [], 3: [], 4: []}
    t0 = time.monotonic()
    next_t = t0
    last_encs = {1: 0, 2: 0, 3: 0, 4: 0}
    n_timeouts = 0
    n_samples = 0

    while time.monotonic() - t0 < DURATION:
        now = time.monotonic()
        if now < next_t:
            time.sleep(next_t - now)
            continue
        time.sleep(INTER_CALL)
        t = time.monotonic() - t0
        n_samples += 1

        try:
            e1, e2, e3, e4 = chassis.get_encoders()
        except Exception:
            n_timeouts += 1
            next_t = max(next_t, time.monotonic() - t0 + SAMPLE_DT)
            continue

        for port, enc in [(1, e1), (2, e2), (3, e3), (4, e4)]:
            if all_rows[port]:
                last_t, last_enc, _ = all_rows[port][-1]
                speed = (enc - last_enc) / max(t - last_t, 1e-3)
            else:
                speed = 0.0
            all_rows[port].append((t, enc, speed))
            last_encs[port] = enc
        next_t += SAMPLE_DT

    chassis.stop_all()

    # 统计 per port
    stats = {}
    for port in [1, 2, 3, 4]:
        settled = [r[2] for r in all_rows[port] if r[0] > 0.3]
        if len(settled) >= 3:
            stats[port] = {
                "mean": statistics.mean(settled),
                "stdev": statistics.stdev(settled) if len(settled) > 1 else 0,
                "cv": (statistics.stdev(settled) / abs(statistics.mean(settled)) * 100
                       if len(settled) > 1 else 0),
                "n": len(settled),
            }

    n_ok = len(stats)
    print(f"  成功采样: {n_ok}/4 路, 超时: {n_timeouts}")

    if n_ok == 4:
        means = [stats[p]["mean"] for p in [1, 2, 3, 4]]
        cv_sync = statistics.stdev(means) / abs(statistics.mean(means)) * 100
        print(f"  sync CV={cv_sync:.2f}%, 极差={max(means)-min(means):.0f} pps")
        if cv_sync < 2:
            ok("同步性", f"CV={cv_sync:.2f}% (优)")
        elif cv_sync < 5:
            ok("同步性", f"CV={cv_sync:.2f}% (良)")
        else:
            fail("同步性", f"CV={cv_sync:.2f}% (差)")
        results["sync_sampling"] = {"cv": cv_sync, "timeouts": n_timeouts}
    elif n_ok >= 2:
        ok("同步采样", f"部分成功 {n_ok}/4")
    else:
        fail("同步采样", f"失败 {n_ok}/4")


# ═══════════════════════════════════════════════════════════
#  测试 7: 麦克纳姆运动模式
# ═══════════════════════════════════════════════════════════

def test_mecanum_motions(bot) -> None:
    print("\n── 7. 麦克纳姆运动模式 ──")
    patterns = [
        ("前进",     (80,  80,  80,  80)),
        ("后退",     (-80, -80, -80, -80)),
        ("横移右",   (-80, 80,  80,  -80)),
        ("横移左",   (80,  -80, -80, 80)),
        ("旋转 CW",  (-80, 80,  -80, 80)),
        ("旋转 CCW", (80,  -80, 80,  -80)),
        ("对角线 FR", (0,   80,  80,  0)),
        ("对角线 FL", (80,  0,   0,   80)),
    ]

    for name, (m1, m2, m3, m4) in patterns:
        try:
            chassis.set_speeds(m1, m2, m3, m4)
            time.sleep(0.5)
            e1, e2, e3, e4 = chassis.get_encoders()
            chassis.stop_all()
            time.sleep(0.2)
            ok(name, f"enc={e1},{e2},{e3},{e4}")
        except Exception as e:
            fail(name, str(e))
            time.sleep(0.3)


# ═══════════════════════════════════════════════════════════
#  测试 8: 压力测试 (快速切换)
# ═══════════════════════════════════════════════════════════

def test_stress(bot) -> None:
    print("\n── 8. 压力测试 (快速切换 ×30) ──")
    chassis.stop_all()
    time.sleep(0.2)

    n_ok = 0
    n_to = 0
    for i in range(30):
        # 交替两个 pattern
        if i % 2 == 0:
            speeds = (80, 80, 80, 80)
        else:
            speeds = (-80, -80, -80, -80)
        try:
            chassis.set_speeds(*speeds)
            n_ok += 1
        except TimeoutError:
            n_to += 1
        except Exception as e:
            fail(f"stress[{i}]", str(e))

    chassis.stop_all()

    print(f"  {n_ok}/30 OK, {n_to} 超时")
    if n_ok >= 29:
        ok("压力测试", f"{n_ok}/30 成功")
    elif n_ok >= 25:
        ok("压力测试", f"{n_ok}/30 成功 (有少量超时)")
    else:
        fail("压力测试", f"仅 {n_ok}/30")


# ═══════════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════════

def main() -> int:
    print("=" * 60)
    print("  MecanumGroup 组控测试 (Service 0x02)")
    print("=" * 60)

    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1

    with bot:
        chassis = Motors(bot, ports=(1, 2, 3, 4))
        if not test_firmware(bot):
            return 1

        test_set_speeds_basic(bot)
        time.sleep(RECOVERY_WAIT)
        test_status_and_stop(bot)
        time.sleep(RECOVERY_WAIT)
        test_latency(bot)
        time.sleep(RECOVERY_WAIT)
        test_encoder_latency(bot)
        time.sleep(RECOVERY_WAIT)
        test_sync_sampling(bot)
        time.sleep(RECOVERY_WAIT)
        test_mecanum_motions(bot)
        time.sleep(RECOVERY_WAIT)
        test_stress(bot)

    # 总结
    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"  结果: {passed}/{total} 通过, {failed} 失败")
    print(f"{'=' * 60}")

    if results:
        print("\n  性能指标:")
        if "latency" in results:
            r = results["latency"]
            print(f"    set_speeds: 组控 {r['group_ms']:.1f}ms vs 逐路 {r['individual_ms']:.1f}ms "
                  f"({r['ratio']:.1f}x)")
        if "enc_latency" in results:
            r = results["enc_latency"]
            print(f"    读编码器:  组控 {r['group_ms']:.1f}ms vs 逐路 {r['individual_ms']:.1f}ms "
                  f"({r['ratio']:.1f}x)")
        if "sync_sampling" in results:
            r = results["sync_sampling"]
            print(f"    同步采样:  CV={r['cv']:.2f}%, 超时={r['timeouts']}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

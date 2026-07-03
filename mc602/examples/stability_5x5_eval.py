import sys
import os

# 获取当前文件所在目录的"上上级目录"的绝对路径
# (模拟从外部项目根导入 mc602 的效果)
grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

import time

from mc602 import (
    MC602, M1, M2, M3, M4,
    SerialNotFoundError, ConnectionError, TimeoutError, ProtocolError,
)
SAMPLE_DT   = 0.20
DURATION    = 2.0
INTER_CALL  = 0.030
SETTLE_TIME = 0.30
RECOVERY_WAIT = 0.5  # 测试间等待 (让固件喘气)
TARGET_SPEED = 20
N_REPEAT     = 5
def single_test(bot, port, target, duration, dt) -> Optional[Dict]:
    """单次测, 返回 {mean, stdev, cv, n_samples, n_timeouts} 或 None (失败)"""
    try:
        bot.motor.reset_encoder(port)
    except Exception:
        return None
    time.sleep(INTER_CALL)
    try:
        bot.motor.set_speed(port, target)
    except Exception:
        return None
    time.sleep(SETTLE_TIME)
    samples = []
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
            enc = bot.motor.get_encoder(port)
        except Exception:
            n_timeouts += 1
            enc = last_enc
        t = time.monotonic() - t0
        if samples:
            last_t, last_enc_prev, _ = samples[-1]
            speed = (enc - last_enc_prev) / max(t - last_t, 1e-3)
        else:
            speed = 0.0
        samples.append((t, enc, speed))
        last_enc = enc
        next_t += dt
    try:
        bot.motor.stop(port)
    except Exception:
        pass
    settled_speeds = [r[2] for r in samples if r[0] > 0.3]
    if len(settled_speeds) < 3:
        return {"n_samples": len(samples), "n_timeouts": n_timeouts,
                "ss_mean": 0.0, "ss_stdev": 0.0, "ss_cv": 0.0, "fail": "data"}
    mean = statistics.mean(settled_speeds)
    stdev = statistics.stdev(settled_speeds) if len(settled_speeds) > 1 else 0.0
    cv = (stdev / abs(mean) * 100) if abs(mean) > 1e-6 else float("inf")
    return {
        "n_samples": len(samples),
        "n_timeouts": n_timeouts,
        "ss_mean": mean,
        "ss_stdev": stdev,
        "ss_cv": cv,
    }
def main():
    print("=" * 70)
    print("4 电机 × 5 次重复 稳定性测试")
    print("=" * 70)
    print(f"目标: set_speed(M, +{TARGET_SPEED})  采样: {SAMPLE_DT*1000:.0f}ms / {DURATION}s")
    print(f"总测点数: 4 电机 × {N_REPEAT} 次 = 20\n")
    try:
        bot = MC602.connect()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] {e}")
        return 1
    with bot:
        print(f"[OK] 连接 {bot._port_name}, FW={bot.system.version}, V={bot.system.voltage:.2f}V\n")
        results: Dict = {}
        n_total_timeouts = 0
        for port in [M1, M2, M3, M4]:
            print(f"{'='*70}\n电机 M{port}\n{'='*70}")
            for rep in range(1, N_REPEAT + 1):
                sys.stdout.write(f"  test {rep}/{N_REPEAT} ... ")
                sys.stdout.flush()
                r = single_test(bot, port, TARGET_SPEED, DURATION, SAMPLE_DT)
                if r is None:
                    print("FAILED (set_speed/reset)")
                    results[(port, rep)] = {"fail": "setup"}
                    time.sleep(RECOVERY_WAIT)
                    continue
                if r.get("fail") == "data":
                    print(f"数据不足 (样本 {r['n_samples']})")
                    results[(port, rep)] = r
                    continue
                results[(port, rep)] = r
                n_total_timeouts += r["n_timeouts"]
                print(f"mean={r['ss_mean']:8.1f} pps  stdev={r['ss_stdev']:6.1f}  CV={r['ss_cv']:5.2f}%  "
                      f"timeouts={r['n_timeouts']}")
                time.sleep(RECOVERY_WAIT)
        print(f"\n\n{'='*70}\n详细数据表 (按电机分组)\n{'='*70}")
        print(f"{'电机':<6} {'重复':<6} {'稳态均值':<14} {'抖动 stdev':<14} {'CV%':<8} {'超时数':<6} {'状态':<8}")
        print("-" * 70)
        for port in [M1, M2, M3, M4]:
            for rep in range(1, N_REPEAT + 1):
                r = results.get((port, rep), {})
                if r.get("fail"):
                    print(f"M{port}    #{rep}    —                —                —        —        {r['fail']}")
                else:
                    print(f"M{port}    #{rep}    {r['ss_mean']:>10.1f} pps  {r['ss_stdev']:>10.1f}      "
                          f"{r['ss_cv']:>6.2f}  {r['n_timeouts']:>4}    OK")
        print(f"\n\n{'='*70}\n汇总统计\n{'='*70}")
        print(f"\n[A] 每电机跨 5 次重复的稳定性 (看重复性):")
        print(f"{'电机':<6} {'均值':<14} {'重复 stdev':<14} {'重复 CV%':<10} {'最快/最慢':<14}")
        print("-" * 60)
        for port in [M1, M2, M3, M4]:
            means = [results[(port, rep)]["ss_mean"]
                     for rep in range(1, N_REPEAT + 1)
                     if (port, rep) in results and "ss_mean" in results[(port, rep)]]
            if len(means) < 2:
                print(f"M{port}    数据不足")
                continue
            mean_of_means = statistics.mean(means)
            std_of_means = statistics.stdev(means)
            cv_of_means = (std_of_means / abs(mean_of_means) * 100) if mean_of_means else 0
            print(f"M{port}    {mean_of_means:>10.1f} pps  {std_of_means:>10.1f}      "
                  f"{cv_of_means:>6.2f}%   {min(means):.0f} ~ {max(means):.0f}")
        print(f"\n[B] 4 电机一致性 (跨电机, 5 次重复的全局均值):")
        all_means = []
        for port in [M1, M2, M3, M4]:
            for rep in range(1, N_REPEAT + 1):
                if (port, rep) in results and "ss_mean" in results[(port, rep)]:
                    all_means.append((port, rep, results[(port, rep)]["ss_mean"]))
        if all_means:
            speeds = [x[2] for x in all_means]
            overall_mean = statistics.mean(speeds)
            overall_stdev = statistics.stdev(speeds)
            overall_cv = overall_stdev / abs(overall_mean) * 100
            print(f"  全部 20 个测点:  mean={overall_mean:.1f} pps  stdev={overall_stdev:.1f}  CV={overall_cv:.2f}%")
            print(f"  最快: {max(speeds):.0f} pps,  最慢: {min(speeds):.0f} pps,  极差: {max(speeds)-min(speeds):.0f} pps")
            print(f"  极差 / 均值: {(max(speeds)-min(speeds))/abs(overall_mean)*100:.2f}%")
        print(f"\n[C] 串口超时统计:")
        print(f"  20 个测点总超时数: {n_total_timeouts}")
        if n_total_timeouts > 0:
            print(f"  超时率: {n_total_timeouts/(20*10)*100:.1f}% (假设每测点 ~10 次请求)")
        print(f"\n{'='*70}\n结论\n{'='*70}")
        if all_means:
            overall_cv = statistics.stdev([x[2] for x in all_means]) / abs(statistics.mean([x[2] for x in all_means])) * 100
            if overall_cv < 2:
                print(f"  [优] 20 个测点 CV={overall_cv:.2f}%, 4 电机一致性极高")
            elif overall_cv < 5:
                print(f"  [良] CV={overall_cv:.2f}%, 4 电机基本一致")
            else:
                print(f"  [差] CV={overall_cv:.2f}%, 电机间差异大, 需做速度补偿")
    return 0
if __name__ == "__main__":
    sys.exit(main())

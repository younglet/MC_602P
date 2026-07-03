"""
test_motor_plot.py — Real-time motor step response plot

Opens a matplotlib window FIRST, then runs the motor.
Speed curve updates live during sampling.
"""
import sys, os, time
grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import (MC602, M1, M2, M3, M4,
                   SerialNotFoundError, ConnectionError)

PORT = M1
TARGET_SPEED = 80
DURATION = 3.0
DT = 0.05

# ── matplotlib setup (before motor starts) ──────────────
try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
except ImportError:
    print("pip install matplotlib")
    sys.exit(1)

plt.ion()
fig, ax = plt.subplots(figsize=(10, 5))
fig.canvas.manager.set_window_title(f"M{PORT} Step Response")
(line,) = ax.plot([], [], "b-", linewidth=1.5)
(ss_line,) = ax.plot([], [], "g--", linewidth=1, alpha=0.7)
ax.set_xlim(0, DURATION)
ax.set_ylim(-500, 12000)
ax.set_xlabel("Time (s)")
ax.set_ylabel("Speed (pps)")
ax.set_title(f"M{PORT}  @+{TARGET_SPEED}  (waiting for data...)")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.pause(0.1)

# ── connect & run ───────────────────────────────────────
try:
    bot = MC602.connect()
except (SerialNotFoundError, ConnectionError) as e:
    print(f"[!] {e}")
    sys.exit(1)

with bot:
    print(f"M{PORT} step +{TARGET_SPEED}, {DURATION}s")
    bot.motor.reset_encoder(PORT)
    time.sleep(0.05)

    ts, speeds = [], []
    n_to = 0
    t0 = time.monotonic()
    next_t = t0
    last_enc = 0
    ss_mean = None

    bot.motor.set_speed(PORT, TARGET_SPEED)

    while time.monotonic() - t0 < DURATION:
        now = time.monotonic()
        if now < next_t:
            time.sleep(0.01)
            continue
        try:
            enc = bot.motor.get_encoder(PORT)
        except Exception:
            n_to += 1
            next_t = max(next_t + DT, time.monotonic() - t0 + DT)
            continue
        t = time.monotonic() - t0
        speed = (enc - last_enc) / max(
            t - (ts[-1] if ts else 0), 1e-3) if ts else 0.0
        ts.append(t)
        speeds.append(speed)
        last_enc = enc
        next_t += DT

        # ── live update ──
        line.set_data(ts, speeds)
        ax.set_xlim(0, max(DURATION, ts[-1] + 0.2))
        if speeds:
            ax.set_ylim(min(speeds) * 0.5, max(speeds) * 1.3)
        # steady-state line (last 30% of data)
        n_ss = max(len(speeds) // 3, 3)
        if n_ss >= 3:
            import statistics
            recent = speeds[-n_ss:]
            ss_mean = statistics.mean(recent)
            ss_line.set_data([0, DURATION], [ss_mean, ss_mean])
        ax.set_title(f"M{PORT} @+{TARGET_SPEED}  "
                     f"t={ts[-1]:.1f}s  speed={speeds[-1]:.0f}  "
                     f"ss={ss_mean:.0f}" if ss_mean else "")
        plt.pause(0.01)

    bot.motor.stop(PORT)

# ── final stats ─────────────────────────────────────────
import statistics
half = len(speeds) // 2
settled = speeds[half:]
ss_mean = statistics.mean(settled) if settled else 0
ss_std = statistics.stdev(settled) if len(settled) > 1 else 0
ss_cv = ss_std / abs(ss_mean) * 100 if ss_mean else 0

t_rise = None
lo, hi = ss_mean * 0.1, ss_mean * 0.9
t_start = None
for tx, sx in zip(ts, speeds):
    if not t_start and sx >= lo:
        t_start = tx
    if t_start and sx >= hi:
        t_rise = tx - t_start
        break

overshoot = (max(speeds) - ss_mean) / abs(ss_mean) * 100 if ss_mean else 0

ax.set_title(
    f"M{PORT} @+{TARGET_SPEED}  |  "
    f"ss={ss_mean:.0f} pps  CV={ss_cv:.2f}%  "
    f"rise={t_rise*1000:.0f}ms" if t_rise else f"ss={ss_mean:.0f} pps"
)
ax.legend(
    [line, ss_line],
    [f"Speed (TO:{n_to})",
     f"Steady={ss_mean:.0f}  CV={ss_cv:.2f}%  "
     f"Rise={t_rise*1000:.0f}ms  Over={overshoot:.1f}%"],
    fontsize=9,
)
plt.ioff()
plt.show(block=True)

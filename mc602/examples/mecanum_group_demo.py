"""
mecanum_group_demo.py — MotorChassis demo (1 frame, 4 motors)
"""
import sys, os, time
grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, MotorChassis, SerialNotFoundError, ConnectionError


def main():
    bot = MC602.connect()
    chassis = MotorChassis(bot, ports=(1, 2, 3, 4))
    with bot:
        print(f"{bot._port_name}, FW={bot.system.version}, V={bot.system.voltage:.2f}V")

        print("Forward (1 frame)")
        t0 = time.monotonic()
        chassis.set_speeds(80, 80, 80, 80)
        dt = (time.monotonic() - t0) * 1000
        print(f"  delay: {dt:.1f} ms")
        time.sleep(0.5)

        print("Read encoders (1 frame)")
        t0 = time.monotonic()
        e1, e2, e3, e4 = chassis.get_encoders()
        dt = (time.monotonic() - t0) * 1000
        print(f"  M1={e1} M2={e2} M3={e3} M4={e4}  delay:{dt:.1f}ms")

        print("Strafe right 0.5s")
        chassis.set_speeds(-80, 80, 80, -80)
        time.sleep(0.5)

        print("Rotation 0.5s")
        chassis.set_speeds(-80, 80, -80, 80)
        time.sleep(0.5)

        print("Stop")
        chassis.stop()
        print("[DONE]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

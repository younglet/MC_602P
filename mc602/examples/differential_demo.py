"""
differential_demo.py — 2-wheel differential drive
"""
import sys, os, time
grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, Motors, SerialNotFoundError, ConnectionError


def main():
    bot = MC602.connect()
    mm = Motors(bot, ports=(1, 2))  # M1, M2 only
    with bot:
        print(f"{bot._port_name}, N=2 differential")

        # Forward: M1=+50, M2=+50
        mm.set_speeds(50, 50)
        time.sleep(1)
        mm.stop()

        # Turn left: M1=-30, M2=+30 (or reversed depending on motor orientation)
        mm.set_speeds(-30, 30)
        time.sleep(0.5)
        mm.stop()

        # Spin in place: M1=+50, M2=-50
        mm.set_speeds(50, -50)
        time.sleep(0.5)
        mm.stop()

        e1, e2 = mm.get_encoders()
        print(f"enc: e1={e1} e2={e2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

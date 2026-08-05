"""
mc602.services.mecanum — Chassis 服务底层 RPC 客户端 (SVC 0x04)

与下位机 firmware/devices/chassis.c 对应。运动学/里程计在固件 200Hz
控制环中执行, 上位机只做参数配置与指令下发。

wire 定点: 线性 cm×100→i32, 角度 rad×1000→i32, 速度 cm/s 整数→u16,
          PID K×1000→u16, 容差 cm×10→u16, 容差 deg×10→u16。
"""

from __future__ import annotations

from ..comm.packet import Op

# 状态机 (与 chassis.h 一致)
CH_IDLE = 0
CH_RUNNING = 1
CH_ARRIVED = 2
CH_ABORTED = 3
CH_STALLED = 4
CH_TIMED_OUT = 5
CH_ERROR = 6
CH_EMERGENCY = 7

STATUS_NAMES = {
    CH_IDLE: "IDLE",
    CH_RUNNING: "RUNNING",
    CH_ARRIVED: "ARRIVED",
    CH_ABORTED: "ABORTED",
    CH_STALLED: "STALLED",
    CH_TIMED_OUT: "TIMED_OUT",
    CH_ERROR: "ERROR",
    CH_EMERGENCY: "EMERGENCY",
}


class ChassisService:
    """CHASSIS 服务 (0x04) — Mecanum 底盘外环控制器（底层 RPC 客户端）"""

    SVC = 0x04

    # GET/SET properties
    PROP_POSE = 0x01     # i32×3 (x*100, y*100, θ*1000)
    PROP_STATUS = 0x02   # u8×2 (state, sub_code)
    PROP_TWIST = 0x03    # i16×3 (vx*100, vy*100, ω*1000)
    PROP_STATS = 0x06    # u32×3 (distance_cm×100, arrived_count, runtime_s)
    PROP_GEOMETRY = 0x10 # u16×3+u16+u16+u16 (track*10, base*10, radius*10, ppr, roller*1000)
    PROP_KP_RHO = 0x20   # u16 ×1000
    PROP_KP_ALPHA = 0x21
    PROP_KP_BETA = 0x22
    PROP_KI_RHO = 0x23
    PROP_KI_ALPHA = 0x24
    PROP_KI_BETA = 0x25
    PROP_TOL_POS = 0x26  # u16 cm×10
    PROP_TOL_ANG = 0x27  # u16 deg×10
    PROP_MAX_V = 0x28    # u16 cm/s
    PROP_MAX_W = 0x29    # u16 deg/s
    PROP_TIMEOUT = 0x30  # u16 ms
    PROP_DIRECT_MODE = 0x32     # u8 rw 0=上位机控制 1=固件直读摇杆
    PROP_DIRECT_DEADZONE = 0x33 # u8 rw 死区 %
    PROP_DIRECT_MAX_V = 0x34    # u16 rw 满量程线速度 cm/s
    PROP_DIRECT_MAX_W = 0x35    # u16 rw 满量程角速度 deg/s
    PROP_DIRECT_INVERT = 0x36   # u8 rw 方向反转位图
    PROP_DIRECT_GAIN = 0x37     # u8 rw 摇杆曲线 (GOTO 移动超时)

    # CALL commands
    CALL_GOTO = 0x80     # i32×3 + u8 max_speed
    CALL_ABORT = 0x81
    CALL_SET_TWIST = 0x82  # i16×3
    CALL_RESET_ODOM = 0x83
    CALL_EMERGENCY = 0x84
    CALL_CLEAR_ERROR = 0x85
    CALL_RESET_STATS = 0x86
    CALL_SET_DIRECT = 0x87   # [u8 enable] 固件直读摇杆

    def __init__(self, bot):
        self._bot = bot

    # ---------- 几何 ----------

    def set_geometry(self, track: float = 30.0, wheel_base: float = 28.0,
                     wheel_radius: float = 3.0, encoder_ppr: int = 2048,
                     roller_adjust: float = 1.052) -> None:
        """推送底盘几何参数到固件 (创建 MecanumChassis 时调用)。
        track/wheel_base/wheel_radius: cm, encoder_ppr: 每圈脉冲,
        roller_adjust: 辊子角度校准系数。"""
        if track <= 0 or wheel_base <= 0 or wheel_radius <= 0 or encoder_ppr <= 0:
            raise ValueError("几何参数必须为正数")
        v = bytearray()
        v += int(track * 10).to_bytes(2, "little")
        v += int(wheel_base * 10).to_bytes(2, "little")
        v += int(wheel_radius * 10).to_bytes(2, "little")
        v += int(encoder_ppr).to_bytes(2, "little")
        v += int(roller_adjust * 1000).to_bytes(2, "little")
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_GEOMETRY,
            value=bytes(v), timeout=1.0, retry=2, retry_delay=0.1,
        )

    def get_geometry(self) -> dict:
        r = self._bot._request(Op.GET, self.SVC, 0, self.PROP_GEOMETRY)
        v = r.value
        return {
            "track": int.from_bytes(v[0:2], "little") / 10.0,
            "wheel_base": int.from_bytes(v[2:4], "little") / 10.0,
            "wheel_radius": int.from_bytes(v[4:6], "little") / 10.0,
            "encoder_ppr": int.from_bytes(v[6:8], "little"),
            "roller_adjust": int.from_bytes(v[8:10], "little") / 1000.0,
        }

    # ---------- 控制 ----------

    def move(self, vx: float = 0.0, vy: float = 0.0,
             omega: float = 0.0) -> None:
        """车身速度控制 (cm/s, rad/s)。固件逆运动学 → 4 轮。"""
        vx = max(-100.0, min(100.0, vx))
        vy = max(-100.0, min(100.0, vy))
        omega = max(-6.0, min(6.0, omega))
        args = (int(vx * 100).to_bytes(2, "little", signed=True)
                + int(vy * 100).to_bytes(2, "little", signed=True)
                + int(omega * 1000).to_bytes(2, "little", signed=True))
        self._bot._request(
            Op.CALL, self.SVC, 0, self.CALL_SET_TWIST,
            value=args, timeout=1.0, retry=2, retry_delay=0.1,
        )

    def goto(self, x: float, y: float, theta: float = 0.0,
             max_speed: int = 80) -> None:
        """外环: 运动到目标位姿 (cm, rad)。极坐标 P 控制在下位机。"""
        max_speed = max(5, min(100, max_speed))
        args = (int(x * 100).to_bytes(4, "little", signed=True)
                + int(y * 100).to_bytes(4, "little", signed=True)
                + int(theta * 1000).to_bytes(4, "little", signed=True)
                + bytes([max_speed]))
        self._bot._request(
            Op.CALL, self.SVC, 0, self.CALL_GOTO,
            value=args, timeout=1.0, retry=2, retry_delay=0.1,
        )

    def abort(self) -> None:
        self._bot._request(Op.CALL, self.SVC, 0, self.CALL_ABORT)

    def emergency_stop(self) -> None:
        self._bot._request(Op.CALL, self.SVC, 0, self.CALL_EMERGENCY)

    def reset_odom(self) -> None:
        """里程计归零 (位置/角度)。"""
        self._bot._request(Op.CALL, self.SVC, 0, self.CALL_RESET_ODOM)

    def clear_error(self) -> None:
        self._bot._request(Op.CALL, self.SVC, 0, self.CALL_CLEAR_ERROR)

    def reset_stats(self) -> None:
        self._bot._request(Op.CALL, self.SVC, 0, self.CALL_RESET_STATS)

    # ---------- 状态 ----------

    def get_pose(self) -> dict:
        r = self._bot._request(Op.GET, self.SVC, 0, self.PROP_POSE)
        v = r.value
        return {
            "x": int.from_bytes(v[0:4], "little", signed=True) / 100.0,
            "y": int.from_bytes(v[4:8], "little", signed=True) / 100.0,
            "theta": int.from_bytes(v[8:12], "little", signed=True) / 1000.0,
        }

    def get_status(self) -> dict:
        r = self._bot._request(Op.GET, self.SVC, 0, self.PROP_STATUS)
        return {"state": r.value[0], "sub_code": r.value[1]}

    def get_stats(self) -> dict:
        r = self._bot._request(Op.GET, self.SVC, 0, self.PROP_STATS)
        v = r.value
        return {
            "distance_cm": int.from_bytes(v[0:4], "little") / 100.0,
            "arrived_count": int.from_bytes(v[4:8], "little"),
            "runtime_s": int.from_bytes(v[8:12], "little"),
        }

    # ---------- 参数 ----------

    def set_pid(self, kp_rho: float = 1.5, kp_alpha: float = 2.5,
                kp_beta: float = 0.8) -> None:
        """极坐标 P-controller 参数。"""
        for prop, k in ((self.PROP_KP_RHO, kp_rho),
                        (self.PROP_KP_ALPHA, kp_alpha),
                        (self.PROP_KP_BETA, kp_beta)):
            self._bot._request(
                Op.SET, self.SVC, 0, prop,
                value=int(k * 1000).to_bytes(2, "little"),
            )

    def set_tolerance(self, pos_cm: float = 2.0, ang_deg: float = 3.0) -> None:
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_TOL_POS,
            value=int(pos_cm * 10).to_bytes(2, "little"),
        )
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_TOL_ANG,
            value=int(ang_deg * 10).to_bytes(2, "little"),
        )

    def set_max_vel(self, v_cm_s: float = 40.0, w_deg_s: float = 90.0) -> None:
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_MAX_V,
            value=int(v_cm_s).to_bytes(2, "little"),
        )
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_MAX_W,
            value=int(w_deg_s).to_bytes(2, "little"),
        )

    def set_timeout(self, ms: int = 10000) -> None:
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_TIMEOUT,
            value=int(ms).to_bytes(2, "little"),
        )

    # ---------- 固件直读摇杆 (BTPad 模式) ----------

    def set_direct(self, enable: bool) -> None:
        """固件直读蓝牙摇杆控制 (BTPad 模式)。
        启用后摇杆在固件 200Hz 闭环内直接驱动底盘,
        摇杆归中/手柄断开自动停车。"""
        self._bot._request(
            Op.CALL, self.SVC, 0, self.CALL_SET_DIRECT,
            value=bytes([1 if enable else 0]),
            timeout=1.0, retry=2, retry_delay=0.1,
        )

    def set_direct_params(self, deadzone: int = 15, max_v: float = 60.0,
                          max_w: float = 46.0, invert: int = 0,
                          gain: int = 0) -> None:
        """固件直读摇杆参数: 死区%/满量程速度/方向反转/曲线。"""
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_DIRECT_DEADZONE,
            value=int(max(0, min(50, deadzone))).to_bytes(2, "little"),
        )
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_DIRECT_MAX_V,
            value=int(max_v).to_bytes(2, "little"),
        )
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_DIRECT_MAX_W,
            value=int(max_w).to_bytes(2, "little"),
        )
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_DIRECT_INVERT,
            value=int(invert & 0x07).to_bytes(2, "little"),
        )
        self._bot._request(
            Op.SET, self.SVC, 0, self.PROP_DIRECT_GAIN,
            value=int(max(0, min(3, gain))).to_bytes(2, "little"),
        )


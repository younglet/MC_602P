/**
 * services.c — Service 注册与分发 (Motor + System 业务实现)
 *
 * Phase 2: PID 闭环控制 — 速度闭环 + 位置闭环
 *
 * 本文件只实现 Service:
 *   - 0xFE System    (电压/版本/重启)
 *   - 0x01 Motor     (PID 闭环, 6 路电机, 调 PID/Limit/Mode)
 *
 * 配套 PC 端 Python SDK: new_whalesbot/host/whalesbot/drivers/motor.py
 *   m = Motor(bot, port=1, kp=120, kd=10)
 *   m.speed = 50            # 调速
 *   m.move_to(3000).wait()  # 位置闭环
 *
 * 协议: COBS + CRC8 + Service/Property (via dispatcher.c)
 */

#include "services.h"
#include "dispatcher.h"
#include "motor_pid.h"
#include "chassis.h"
#include <string.h>

/* ====================================================================
 * 常量
 * ==================================================================== */

#define MOTOR_MAX 6

/* 485 总线独占标志 (定义在 step_driver.c, 自研扩展) */
extern volatile int step_bus_busy;

/* ====================================================================
 * PID 控制循环 (5ms 周期, 200Hz)
 * ==================================================================== */

static MotorPID motor_pid[MOTOR_MAX];

/* ====================================================================
 * 电机目标共享表 — 单一 set_motor 写线程 (pid_control_loop)
 *
 * 架构原则: 一个资源 = 一个写线程。
 * MotorService / Chassis 等业务线程只写目标表 (motor_apply),
 * 不直接调 SDK set_motor —— 否则多线程抢同一硬件 (历史 bug:
 * 底盘 200Hz 环与 PID 环交替写 set_motor → 电机目标被互相覆盖)。
 * ==================================================================== */

static volatile int g_motor_target[MOTOR_MAX];

void motor_apply(int port, int speed)
{
    if (port < 1 || port > MOTOR_MAX) return;
    if (speed >  100) speed =  100;
    if (speed < -100) speed = -100;
    g_motor_target[port - 1] = speed;
}

/**
 * PID 控制线程 — 每 5ms 运行一次。
 * 对每个电机：读 target → set_motor() (交给 SDK 闭环 PID)
 * 注: SDK 内置 PID 已是原厂调教, 我们只负责转发 target.
 *     原计划用 set_motor_open + 我们自己 PID 会双层套叠, 且 unit mismatch,
 *     现改为: 我们只记录 target, 定时调 set_motor 喂给 SDK 的 PID.
 */
static void pid_control_loop(void)
{
    while (1) {
        /* 唯一调 set_motor 的地方: 无条件把共享目标表喂给 SDK
         * (OFF 电机目标为 0, 保持停车; 5ms 喂一次避免 SDK 停转保护) */
        for (int i = 0; i < MOTOR_MAX; i++) {
            set_motor(i + 1, g_motor_target[i]);
        }
        wait(0.005);  /* 5ms → 200Hz 轮询 (避免 SDK 1s 不喂停转保护) */
    }
}

/* ====================================================================
 * Service: System (0xFE)
 * ==================================================================== */

static uint16_t sys_watchdog_ms = 3000;

static uint8_t system_handler(uint8_t op, uint8_t inst, uint8_t prop,
                              const uint8_t *in_data, uint8_t in_len,
                              uint8_t *out_data, uint8_t *out_len)
{
    (void)inst;

    switch (op) {
    case OP_GET:
        switch (prop) {
        case 0x01: { /* voltage (u16 mV) */
            int32_t mv = getBatt_AVG();
            out_data[0] = (uint8_t)(mv & 0xFF);
            out_data[1] = (uint8_t)((mv >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        }
        case 0x02: { /* version (str) */
            const char *ver = "MC602P FW v1.0";
            uint8_t slen = (uint8_t)strlen(ver);
            out_data[0] = slen;
            memcpy(out_data + 1, ver, slen);
            *out_len = 1 + slen;
            return STATUS_OK;
        }
        case 0x03: { /* uptime (u32 s) */
            uint32_t uptime = (uint32_t)seconds();
            out_data[0] = (uint8_t)(uptime & 0xFF);
            out_data[1] = (uint8_t)((uptime >> 8) & 0xFF);
            out_data[2] = (uint8_t)((uptime >> 16) & 0xFF);
            out_data[3] = (uint8_t)((uptime >> 24) & 0xFF);
            *out_len = 4;
            return STATUS_OK;
        }
        case 0x04: { /* watchdog (u16 ms) */
            out_data[0] = (uint8_t)(sys_watchdog_ms & 0xFF);
            out_data[1] = (uint8_t)((sys_watchdog_ms >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        }
        case 0x0A: { /* rx_stats (u32×3: valid, crc_err, ring_overflow) */
            extern volatile uint32_t g_rx_stats_valid;
            extern volatile uint32_t g_rx_stats_crc;
            extern volatile uint32_t g_rx_stats_overflow;
            uint32_t st[3] = { g_rx_stats_valid, g_rx_stats_crc,
                               g_rx_stats_overflow };
            for (int i = 0; i < 3; i++) {
                out_data[i * 4 + 0] = (uint8_t)(st[i] & 0xFF);
                out_data[i * 4 + 1] = (uint8_t)((st[i] >> 8) & 0xFF);
                out_data[i * 4 + 2] = (uint8_t)((st[i] >> 16) & 0xFF);
                out_data[i * 4 + 3] = (uint8_t)((st[i] >> 24) & 0xFF);
            }
            *out_len = 12;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    case OP_SET:
        switch (prop) {
        case 0x04: /* watchdog (u16) */
            if (in_len >= 2) {
                sys_watchdog_ms = (uint16_t)in_data[0]
                                | ((uint16_t)in_data[1] << 8);
            }
            *out_len = 0;
            return STATUS_OK;
        default:
            return STATUS_READ_ONLY;
        }

    case OP_CALL:
        switch (prop) {
        case 0x80: /* reboot */
            *out_len = 0;
            Program_Run(0x08000000);  // 跳到 bootloader, 不返回
            return STATUS_OK;  // unreachable
        case 0x81: /* bootloader (实际跳到 GUI, 方便 pydownload.py 重新烧录) */
            *out_len = 0;
            Program_Run(0x08040000);  // 跳到 GUI, 不返回
            return STATUS_OK;  // unreachable
        default:
            return STATUS_NOT_FOUND;
        }

    default:
        return STATUS_NOT_FOUND;
    }
}

/* ====================================================================
 * Service: Motor (0x01) — PID 闭环
 *
 * Props:
 *   0x01 speed           i8  rw  目标速度 (-100~100)
 *   0x02 encoder         i32 r   编码器脉冲累计
 *   0x03 current         u16 r   电流 (mA) — 占位返回 0
 *   0x04 status          u8  r   0=停止 1=运行 2=堵转 3=PID到位 4=PID超时
 *   0x05 pid_kp          u16 rw  比例系数 ×1000
 *   0x06 pid_ki          u16 rw  积分系数 ×1000
 *   0x07 pid_kd          u16 rw  微分系数 ×1000
 *   0x08 control_mode    u8  rw  0=开环 1=PID速度 2=PID位置
 *   0x09 target_position i32 rw  位置模式目标（编码器脉冲）
 *   0x0A max_speed       u8  rw  位置模式最大转速 (0-100, 默认80)
 *   0x0B move_timeout    u16 rw  位置移动超时 (ms, 0=永不超时, 默认3000)
 *   0x0C stall_timeout   u16 rw  堵转判定超时 (ms, 0=禁用, 默认500)
 * Commands:
 *   0x80 stop
 *   0x81 reset_encoder
 *   0x82 move_to(position:i32, speed:u8)
 * ==================================================================== */

static uint8_t motor_handler(uint8_t op, uint8_t inst, uint8_t prop,
                             const uint8_t *in_data, uint8_t in_len,
                             uint8_t *out_data, uint8_t *out_len)
{
    uint8_t port = inst;
    if (port < 1 || port > MOTOR_MAX) {
        return STATUS_RANGE_ERR;
    }
    uint8_t idx = port - 1;
    MotorPID *pid = &motor_pid[idx];

    switch (op) {
    case OP_GET:
        switch (prop) {
        case 0x01: /* speed (i8) */
            out_data[0] = (uint8_t)pid->target_speed;
            *out_len = 1;
            return STATUS_OK;
        case 0x02: { /* encoder (i32) */
            int32_t enc = motor_encoder(port);
            out_data[0] = (uint8_t)(enc & 0xFF);
            out_data[1] = (uint8_t)((enc >> 8) & 0xFF);
            out_data[2] = (uint8_t)((enc >> 16) & 0xFF);
            out_data[3] = (uint8_t)((enc >> 24) & 0xFF);
            *out_len = 4;
            return STATUS_OK;
        }
        case 0x03: /* current (u16) — 占位 */
            out_data[0] = 0;
            out_data[1] = 0;
            *out_len = 2;
            return STATUS_OK;
        case 0x04: /* status (u8) */
            if (pid->mode == PID_MODE_OFF) {
                out_data[0] = 0;  /* 停止 */
            } else if (pid->stalled) {
                out_data[0] = 2;  /* 堵转 */
            } else if (pid->mode == PID_MODE_POSITION && pid->at_target) {
                out_data[0] = 3;  /* PID 到位 */
            } else if (pid->timed_out) {
                out_data[0] = 4;  /* PID 超时 */
            } else {
                out_data[0] = 1;  /* 运行中 */
            }
            *out_len = 1;
            return STATUS_OK;
        case 0x05: /* pid_kp (u16) */
            out_data[0] = (uint8_t)(pid->kp & 0xFF);
            out_data[1] = (uint8_t)((pid->kp >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        case 0x06: /* pid_ki (u16) */
            out_data[0] = (uint8_t)(pid->ki & 0xFF);
            out_data[1] = (uint8_t)((pid->ki >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        case 0x07: /* pid_kd (u16) */
            out_data[0] = (uint8_t)(pid->kd & 0xFF);
            out_data[1] = (uint8_t)((pid->kd >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        case 0x08: /* control_mode (u8) */
            out_data[0] = pid->mode;
            *out_len = 1;
            return STATUS_OK;
        case 0x09: { /* target_position (i32) */
            int32_t tp = pid->target_position;
            out_data[0] = (uint8_t)(tp & 0xFF);
            out_data[1] = (uint8_t)((tp >> 8) & 0xFF);
            out_data[2] = (uint8_t)((tp >> 16) & 0xFF);
            out_data[3] = (uint8_t)((tp >> 24) & 0xFF);
            *out_len = 4;
            return STATUS_OK;
        }
        case 0x0A: /* max_speed (u8) */
            out_data[0] = (uint8_t)pid->max_speed;
            *out_len = 1;
            return STATUS_OK;
        case 0x0B: /* move_timeout (u16) */
            out_data[0] = (uint8_t)(pid->move_timeout & 0xFF);
            out_data[1] = (uint8_t)((pid->move_timeout >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        case 0x0C: /* stall_timeout (u16) */
            out_data[0] = (uint8_t)(pid->stall_timeout & 0xFF);
            out_data[1] = (uint8_t)((pid->stall_timeout >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        default:
            return STATUS_NOT_FOUND;
        }

    case OP_SET:
        switch (prop) {
        case 0x01: { /* speed (i8) — PID 速度模式 */
            if (in_len >= 1) {
                int8_t spd = (int8_t)in_data[0];
                if (spd < -100) spd = -100;
                if (spd >  100) spd =  100;
                if (spd == 0) {
                    pid_stop(pid);
                    motor_apply(port, 0);
                } else {
                    pid_set_speed(pid, spd);
                    motor_apply(port, spd);
                }
            }
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x05: /* pid_kp */
            if (in_len >= 2)
                pid->kp = (uint16_t)in_data[0]
                        | ((uint16_t)in_data[1] << 8);
            *out_len = 0;
            return STATUS_OK;
        case 0x06: /* pid_ki */
            if (in_len >= 2)
                pid->ki = (uint16_t)in_data[0]
                        | ((uint16_t)in_data[1] << 8);
            *out_len = 0;
            return STATUS_OK;
        case 0x07: /* pid_kd */
            if (in_len >= 2)
                pid->kd = (uint16_t)in_data[0]
                        | ((uint16_t)in_data[1] << 8);
            *out_len = 0;
            return STATUS_OK;
        case 0x08: /* control_mode (u8) */
            if (in_len >= 1) {
                uint8_t mode = in_data[0];
                if (mode == PID_MODE_OFF) {
                    pid_stop(pid);
                    motor_apply(port, 0);
                }
                /* SPEED/POSITION 模式由 set_speed/set_position 自动切换 */
            }
            *out_len = 0;
            return STATUS_OK;
        case 0x09: { /* target_position (i32) — 位置模式 */
            if (in_len >= 4) {
                int32_t pos = (int32_t)in_data[0]
                            | ((int32_t)in_data[1] << 8)
                            | ((int32_t)in_data[2] << 16)
                            | ((int32_t)in_data[3] << 24);
                pid_set_position(pid, pos, pid->max_speed);
            }
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x0A: /* max_speed (u8) */
            if (in_len >= 1) {
                int8_t v = (int8_t)in_data[0];
                if (v < 5)   v = 5;
                if (v > 100) v = 100;
                pid->max_speed = v;
            }
            *out_len = 0;
            return STATUS_OK;
        case 0x0B: /* move_timeout (u16) */
            if (in_len >= 2) {
                pid->move_timeout = (uint16_t)in_data[0]
                                  | ((uint16_t)in_data[1] << 8);
            }
            *out_len = 0;
            return STATUS_OK;
        case 0x0C: /* stall_timeout (u16) */
            if (in_len >= 2) {
                pid->stall_timeout = (uint16_t)in_data[0]
                                   | ((uint16_t)in_data[1] << 8);
            }
            *out_len = 0;
            return STATUS_OK;
        default:
            return STATUS_READ_ONLY;
        }

    case OP_CALL:
        switch (prop) {
        case 0x80: /* stop */
            pid_stop(pid);
            motor_apply(port, 0);
            *out_len = 0;
            return STATUS_OK;
        case 0x81: /* reset_encoder */
            reset_motor_encoder(port);
            *out_len = 0;
            return STATUS_OK;
        case 0x82: { /* move_to(position:i32, speed:u8) */
            if (in_len >= 5) {
                int32_t pos = (int32_t)in_data[0]
                            | ((int32_t)in_data[1] << 8)
                            | ((int32_t)in_data[2] << 16)
                            | ((int32_t)in_data[3] << 24);
                int8_t spd = (int8_t)in_data[4];
                if (spd < 5) spd = 80;  /* 默认 80 */
                pid_set_position(pid, pos, spd);
            }
            *out_len = 0;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    default:
        return STATUS_NOT_FOUND;
    }
}

/* ====================================================================
 * Service: BT Remote (0x03) — 蓝牙手柄状态
 *
 * 读取蓝牙遥控器的摇杆值、按键、连接状态。
 * inst 固定为 0。
 *
 * Props:
 *   0x01 ALL  6×u8  R   [stick1:i8, stick2:i8, stick3:i8, stick4:i8, keys:u8, status:u8]
 *   0x02 NAME str   R   蓝牙设备名
 * ==================================================================== */

static uint8_t btremote_handler(uint8_t op, uint8_t inst, uint8_t prop,
                                 const uint8_t *in_data, uint8_t in_len,
                                 uint8_t *out_data, uint8_t *out_len)
{
    (void)inst;
    (void)in_data;
    (void)in_len;

    switch (op) {
    case OP_GET:
        switch (prop) {
        case 0x01: { /* ALL: 4 sticks + keys + status, 11 bytes */
            /* 摇杆值范围因手柄而异 (0-100 或 0-255 或 0-1023).
             * 用 u16le 传输原值, 上位机自适应范围.
             * 顺序: st1:u16 st2:u16 st3:u16 st4:u16 keys:u16 status:u8 */
            for (int i = 0; i < 4; i++) {
                int v = get_bt_remote_control(i + 1);  /* BTSTICK1=1 */
                uint16_t uv = (uint16_t)(v < 0 ? 0 : v);
                out_data[i * 2]     = (uint8_t)(uv & 0xFF);
                out_data[i * 2 + 1] = (uint8_t)((uv >> 8) & 0xFF);
            }
            /* 按键: BTKEY=0, u16le (bit 0-15 全保留) */
            int keys = get_bt_remote_control(0);
            uint16_t uk = (uint16_t)(keys > 0 ? keys : 0);
            out_data[8] = (uint8_t)(uk & 0xFF);
            out_data[9] = (uint8_t)((uk >> 8) & 0xFF);
            /* 连接状态 */
            out_data[10] = (uint8_t)(getbtstatus() ? 1 : 0);
            *out_len = 11;
            return STATUS_OK;
        }
        case 0x02: { /* NAME */
            char *name = getBtName();
            uint8_t slen = 0;
            if (name) {
                slen = (uint8_t)strlen(name);
                if (slen > 32) slen = 32;
                memcpy(out_data + 1, name, slen);
            }
            out_data[0] = slen;
            *out_len = 1 + slen;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }
    default:
        return STATUS_NOT_FOUND;
    }
}

/* ====================================================================
 * Service: Mecanum Group (0x02) — 4 路麦克纳姆轮组控
 *
 * 一次指令控制 M1~M4 全部四路, 避免逐路调用的串口延迟和时序不同步.
 * inst 固定为 0 (组操作).
 *
 * Props:
 *   0x01 speeds     4×i8  W   [M1_speed, M2_speed, M3_speed, M4_speed]
 *   0x02 encoders   4×i32 R   [M1_enc, M2_enc, M3_enc, M4_enc] 每路 i32le
 *   0x03 statuses   4×u8  R   [M1_st, M2_st, M3_st, M4_st]
 * Commands:
 *   0x80 stop_all           停全部 4 路
 * ==================================================================== */

static uint8_t mecanum_group_handler(uint8_t op, uint8_t inst, uint8_t prop,
                                     const uint8_t *in_data, uint8_t in_len,
                                     uint8_t *out_data, uint8_t *out_len)
{
    (void)inst;  /* group操作, inst 固定为 0 */

    switch (op) {
    case OP_GET:
        switch (prop) {
        case 0x02: { /* encoders: 4 × i32le */
            for (int i = 0; i < 4; i++) {
                int32_t enc = motor_encoder(i + 1);
                out_data[i * 4 + 0] = (uint8_t)(enc & 0xFF);
                out_data[i * 4 + 1] = (uint8_t)((enc >> 8) & 0xFF);
                out_data[i * 4 + 2] = (uint8_t)((enc >> 16) & 0xFF);
                out_data[i * 4 + 3] = (uint8_t)((enc >> 24) & 0xFF);
            }
            *out_len = 16;
            return STATUS_OK;
        }
        case 0x03: { /* statuses: 4 × u8 */
            for (int i = 0; i < 4; i++) {
                MotorPID *pid = &motor_pid[i];
                if (pid->mode == PID_MODE_OFF) {
                    out_data[i] = 0;
                } else if (pid->stalled) {
                    out_data[i] = 2;
                } else if (pid->mode == PID_MODE_POSITION && pid->at_target) {
                    out_data[i] = 3;
                } else if (pid->timed_out) {
                    out_data[i] = 4;
                } else {
                    out_data[i] = 1;
                }
            }
            *out_len = 4;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    case OP_SET:
        switch (prop) {
        case 0x01: { /* speeds: 4 × i8 */
            if (in_len < 4) return STATUS_RANGE_ERR;
            for (int i = 0; i < 4; i++) {
                int8_t spd = (int8_t)in_data[i];
                MotorPID *pid = &motor_pid[i];
                if (spd < -100) spd = -100;
                if (spd >  100) spd =  100;
                if (spd == 0) {
                    pid_stop(pid);
                    motor_apply(i + 1, 0);
                } else {
                    pid_set_speed(pid, spd);
                    motor_apply(i + 1, spd);
                }
            }
            *out_len = 0;
            return STATUS_OK;
        }
        default:
            return STATUS_READ_ONLY;
        }

    case OP_CALL:
        switch (prop) {
        case 0x80: { /* stop_all */
            for (int i = 0; i < 4; i++) {
                pid_stop(&motor_pid[i]);
                motor_apply(i + 1, 0);
            }
            *out_len = 0;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    default:
        return STATUS_NOT_FOUND;
    }
}

/* ====================================================================
 * Service: Stepper (0x30) — 485 总线步进电机
 *
 * 底层: SDK step_driver (step_driver.c) — 自带 100Hz 线程:
 *   - 3 通道梯形加减速 + 速度写寄存器 (一帧广播 3 通道)
 *   - 距离反馈解析 (cmd 0x90/0x91/0x92)
 *   - |speed| < 50 视为 0 (低速死区, SDK 行为)
 *
 * inst = 通道 (1~3), 对应 STP_MOT_CH1~CH3.
 *
 * Props:
 *   0x01 speed     i16 rw  目标速度 (-32000~32000)
 *   0x02 distance  i32 r   脉冲距离 (驱动器反馈)
 *   0x03 acc       u16 rw  加减速 (0~32000, 默认 1000, 越大加速越快)
 * Commands:
 *   0x80 stop      — 速度置 0 (保持力矩, 不清距离)
 *   0x81 reset     — 复位/释放 (速度 0 + Servo_Reset, 阻塞 ~100ms)
 *
 * ⚠️ reset 阻塞: 底层 set_stepmotor_reset() 忙等 100ms, 期间协议响应延迟.
 *    罕见操作 + 上位机自动重试兜底, 可接受.
 * ==================================================================== */

/* 最近一次 SET 的目标速度 (SDK 无 getter, 固件侧记录供回读) */
static int16_t step_target[3];
static uint16_t step_acc[3] = {1000, 1000, 1000};  /* 与 SDK 默认 SPD_ACC 一致 */

static uint8_t stepper_handler(uint8_t op, uint8_t inst, uint8_t prop,
                               const uint8_t *in_data, uint8_t in_len,
                               uint8_t *out_data, uint8_t *out_len)
{
    if (inst < STP_MOT_CH1 || inst > STP_MOT_CH3) {
        return STATUS_RANGE_ERR;
    }
    int idx = inst - 1;

    switch (op) {
    case OP_GET:
        switch (prop) {
        case 0x01: { /* speed (i16) — 最近一次目标速度 */
            int16_t spd = step_target[idx];
            out_data[0] = (uint8_t)(spd & 0xFF);
            out_data[1] = (uint8_t)((spd >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        }
        case 0x02: { /* distance (i32) */
            int d = get_stepmotor_distance(inst);
            out_data[0] = (uint8_t)(d & 0xFF);
            out_data[1] = (uint8_t)((d >> 8) & 0xFF);
            out_data[2] = (uint8_t)((d >> 16) & 0xFF);
            out_data[3] = (uint8_t)((d >> 24) & 0xFF);
            *out_len = 4;
            return STATUS_OK;
        }
        case 0x03: { /* acc (u16) — 最近一次设置的加减速 */
            out_data[0] = (uint8_t)(step_acc[idx] & 0xFF);
            out_data[1] = (uint8_t)((step_acc[idx] >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    case OP_SET:
        switch (prop) {
        case 0x01: { /* speed (i16) */
            if (in_len < 2) return STATUS_RANGE_ERR;
            int spd = (int)(int16_t)((uint16_t)in_data[0]
                                   | ((uint16_t)in_data[1] << 8));
            set_stepmotor(inst, spd);
            step_target[idx] = (int16_t)spd;
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x03: { /* acc (u16) */
            if (in_len < 2) return STATUS_RANGE_ERR;
            uint16_t acc = (uint16_t)in_data[0] | ((uint16_t)in_data[1] << 8);
            set_stepmotor_acc(inst, acc);
            step_acc[idx] = acc;
            *out_len = 0;
            return STATUS_OK;
        }
        default:
            return STATUS_READ_ONLY;
        }

    case OP_CALL:
        switch (prop) {
        case 0x80: /* stop */
            set_stepmotor(inst, 0);
            step_target[idx] = 0;
            *out_len = 0;
            return STATUS_OK;
        case 0x81: /* reset (阻塞 ~100ms) */
            set_stepmotor_reset();
            step_target[idx] = 0;
            *out_len = 0;
            return STATUS_OK;
        default:
            return STATUS_NOT_FOUND;
        }

    default:
        return STATUS_NOT_FOUND;
    }
}

/* ====================================================================
 * Service: ServoBus (0x20) — 485 总线舵机
 *
 * 底层: SDK step_driver 的 set_step_servoa() — 经 StepMotorThread 统一
 * 发送 (与步进电机共用 485 总线和 RX 回调, 官方共存方案)。
 * ⚠️ 其余 485 舵机 API (set_servo_angle / ReadServoaAngle / 力矩) 会
 * 抢占 setUartPort485_RxHandle 与步进线程冲突, 故不启用。
 *
 * inst = 舵机 ID (S1~S18 = 1~18)
 * Commands:
 *   0x80 set_angle  [i16 angle(-150~150)][u8 speed(1~100)] 阻塞 ≤10ms
 *   0x81 change_id  [u8 now_id][u8 new_id(1~3)]  仅支持总线上单个舵机
 *   0x82 read_angle → i32  读舵机实际角度 (独占总线, 阻塞 ≤10ms)
 *   0x83 ping      → u8   在线检测 (独占总线)
 *   0x84 read_version → u16 舵机固件版本 (独占总线)
 *   0x87 scan      [u8 max_id] → u8×N 在线 ID 列表 (独占总线, 阻塞 ~N×5ms)
 * ==================================================================== */

static bool servo_bus_started = false;
static int16_t servo_bus_angle[SERVO_IDMAX];  /* 最近一次目标角度 (SDK 无同步读回) */

static uint8_t servobus_handler(uint8_t op, uint8_t inst, uint8_t prop,
                                const uint8_t *in_data, uint8_t in_len,
                                uint8_t *out_data, uint8_t *out_len)
{
    if (inst < 1 || inst > SERVO_IDMAX) {
        /* inst=0 仅允许总线级操作 (scan) */
        if (!(inst == 0 && op == OP_CALL && prop == 0x87)) {
            return STATUS_RANGE_ERR;
        }
    }
    int idx = inst - 1;

    switch (op) {
    case OP_GET:
        switch (prop) {
        case 0x01: { /* angle (i16) — 最近一次目标角度 */
            int16_t a = servo_bus_angle[idx];
            out_data[0] = (uint8_t)(a & 0xFF);
            out_data[1] = (uint8_t)((a >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    case OP_CALL:
        switch (prop) {
        case 0x80: { /* set_angle: [i16 angle][u8 speed] */
            if (in_len < 3) return STATUS_RANGE_ERR;
            int16_t angle = (int16_t)((uint16_t)in_data[0]
                                    | ((uint16_t)in_data[1] << 8));
            uint8_t speed = in_data[2];
            if (speed < 1)   speed = 40;
            if (speed > 100) speed = 100;
            if (angle < -150) angle = -150;
            if (angle >  150) angle =  150;

            /* set_step_servoa 依赖 StepMotorThread 消费 sid 队列,
             * 首次使用时确保步进线程已启动 (速度 0 不影响电机) */
            if (!servo_bus_started) {
                set_stepmotor(1, 0);
                servo_bus_started = true;
            }
            set_step_servoa(inst, speed, angle);  /* 阻塞 ≤10ms */
            servo_bus_angle[idx] = angle;
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x81: { /* change_id: [u8 now_id][u8 new_id] 目标限 1~3 */
            if (in_len < 2) return STATUS_RANGE_ERR;
            uint8_t now_id = in_data[0];
            uint8_t new_id = in_data[1];
            if (now_id < 1 || now_id > SERVO_IDMAX) return STATUS_RANGE_ERR;
            if (new_id < 1 || new_id > 3) return STATUS_RANGE_ERR;

            /* 独占总线: 让步进线程暂停, 避免抢 485 RX 回调 */
            step_bus_busy = 1;
            /* SDK 要求: 总线上只有 1 个舵机时才能正确操作 */
            servo_id_change(now_id, new_id);
            step_bus_busy = 0;
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x82: { /* read_angle — 读舵机实际角度 (独占总线) */
            step_bus_busy = 1;
            int a = ReadServoaAngle(inst);
            step_bus_busy = 0;
            out_data[0] = (uint8_t)(a & 0xFF);
            out_data[1] = (uint8_t)((a >> 8) & 0xFF);
            out_data[2] = (uint8_t)((a >> 16) & 0xFF);
            out_data[3] = (uint8_t)((a >> 24) & 0xFF);
            *out_len = 4;
            return STATUS_OK;
        }
        case 0x83: { /* ping — 舵机在线检测 (独占总线) */
            step_bus_busy = 1;
            int r = Servo_Ping(inst);
            step_bus_busy = 0;
            out_data[0] = (uint8_t)(r ? 1 : 0);
            *out_len = 1;
            return STATUS_OK;
        }
        case 0x84: { /* read_version — 舵机固件版本 (独占总线) */
            step_bus_busy = 1;
            int v = ReadServoaVerion(inst);
            step_bus_busy = 0;
            out_data[0] = (uint8_t)(v & 0xFF);
            out_data[1] = (uint8_t)((v >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        }
        case 0x87: { /* scan: [u8 max_id] → u8×N 在线 ID 列表 */
            uint8_t max_id = SERVO_IDMAX;
            if (in_len >= 1) {
                max_id = in_data[0];
                if (max_id < 1) max_id = 1;
                if (max_id > SERVO_IDMAX) max_id = SERVO_IDMAX;
            }
            uint8_t n = 0;
            for (uint8_t id = 1; id <= max_id; id++) {
                step_bus_busy = 1;
                int r = Servo_Ping(id);
                step_bus_busy = 0;
                if (r) {
                    out_data[n++] = id;
                }
            }
            *out_len = n;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    default:
        return STATUS_NOT_FOUND;
    }
}

/* ====================================================================
 * Service: ServoPWM (0x21) — PWM 舵机
 *
 * 底层: SDK SetServo() — 独立定时器输出, 7 路 (P7~P13)。
 *
 * inst = 1~7 → D1~D7 (P7~P13)
 * Props:
 *   0x01 angle u16 r  最近一次目标角度 (0~180)
 *   0x02 duty  u16 rw  通用 PWM 占空比 (0~1000 = 0~100.0%, 40Hz)
 * Commands:
 *   0x80 set_angle  [u16 angle(0~180)][u8 speed(10~100)]
 * ==================================================================== */

static const int pwm_port_map[7] = {D1, D2, D3, D4, D5, D6, D7};
static int16_t servo_pwm_angle[7];  /* 最近一次目标角度 */
static uint16_t servo_pwm_duty[7];  /* 最近一次占空比 (0~1000) */

/* 每个口的定时器/通道 (SDK ServoInit 配置, 周期 ARR+1=1500, 40Hz) */
static TIM_TypeDef *const pwm_tim_map[7] = {
    TIM1, TIM1, TIM1, TIM1, TIM3, TIM3, TIM12
};
static const uint8_t pwm_ch_map[7] = {1, 2, 3, 4, 2, 1, 1};

static void pwm_set_ccr(TIM_TypeDef *tim, uint8_t ch, uint32_t ccr)
{
    switch (ch) {
    case 1: TIM_SetCompare1(tim, ccr); break;
    case 2: TIM_SetCompare2(tim, ccr); break;
    case 3: TIM_SetCompare3(tim, ccr); break;
    case 4: TIM_SetCompare4(tim, ccr); break;
    default: break;
    }
}

static uint8_t servopwm_handler(uint8_t op, uint8_t inst, uint8_t prop,
                                const uint8_t *in_data, uint8_t in_len,
                                uint8_t *out_data, uint8_t *out_len)
{
    if (inst < 1 || inst > 7) {
        return STATUS_RANGE_ERR;
    }
    int idx = inst - 1;

    switch (op) {
    case OP_GET:
        switch (prop) {
        case 0x01: { /* angle (i16) — 最近一次目标角度 */
            int16_t a = servo_pwm_angle[idx];
            out_data[0] = (uint8_t)(a & 0xFF);
            out_data[1] = (uint8_t)((a >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        }
        case 0x02: { /* duty (u16) — 最近一次占空比 */
            uint16_t d = servo_pwm_duty[idx];
            out_data[0] = (uint8_t)(d & 0xFF);
            out_data[1] = (uint8_t)((d >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    case OP_SET:
        switch (prop) {
        case 0x02: { /* duty (u16 0~1000 = 0~100.0%) */
            if (in_len < 2) return STATUS_RANGE_ERR;
            uint16_t duty = (uint16_t)in_data[0] | ((uint16_t)in_data[1] << 8);
            if (duty > 1000) duty = 1000;
            TIM_TypeDef *tim = pwm_tim_map[idx];
            uint32_t period = tim->ARR + 1;
            uint32_t ccr = (uint32_t)period * duty / 1000;
            pwm_set_ccr(tim, pwm_ch_map[idx], ccr);
            servo_pwm_duty[idx] = duty;
            *out_len = 0;
            return STATUS_OK;
        }
        default:
            return STATUS_READ_ONLY;
        }

    case OP_CALL:
        switch (prop) {
        case 0x80: { /* set_angle: [u16 angle][u8 speed] */
            if (in_len < 3) return STATUS_RANGE_ERR;
            int angle = (int)in_data[0] | ((int)in_data[1] << 8);
            int speed = (int)in_data[2];
            if (angle < 0)   angle = 0;
            if (angle > 180) angle = 180;
            if (speed < 10)  speed = 10;
            if (speed > 100) speed = 100;
            SetServo(pwm_port_map[inst - 1], speed, angle);
            servo_pwm_angle[idx] = (int16_t)angle;
            *out_len = 0;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    default:
        return STATUS_NOT_FOUND;
    }
}

/* ====================================================================
 * Service: IO (0x50) — P1~P6 + D1~D7 数字 IO, 9 路模拟输入
 *
 * 引脚映射 (SDK digoutput.h DIG1~DIG13):
 *   P1~P6  (DIG1~6):  PD5 PD4 PC15 PD10 PA4 PB9
 *   D1~D7  (DIG7~13): PE9 PE11 PE13 PE14 PA7 PA6 PB14  ⚠️与 PWM 舵机共用
 * ⚠️ P1/P2 与 UART 复用 (SDK uart_p1/uart_p2), 配成 IO 会禁用串口功能。
 *
 * 模拟输入 (SDK getAI):
 *   inst 1~6 = A1~A6 (P1~P6: PC0 PC1 PC2 PC3 PA0 PA1)
 *   inst 7~9 = AI1~AI3 (D1~D3: PC4 PC5 PB1)
 *
 * Props:
 *   0x01 value  u8 rw  读: 输入电平 (0/1); 写: 输出电平 (0/1)
 *   0x02 mode   u8 rw  0=输入(上拉) 1=输出(推挽)
 *   0x03 analog u16 r  模拟输入 (inst 1~9)
 * Commands:
 *   0x80 toggle — 输出反转
 * ==================================================================== */

#define IO_PORT_MAX 13

static const GPIO_TypeDef *io_port_map[IO_PORT_MAX] = {
    GPIOD, GPIOD, GPIOC, GPIOD, GPIOA, GPIOB,        /* P1~P6  */
    GPIOE, GPIOE, GPIOE, GPIOE, GPIOA, GPIOA, GPIOB  /* D1~D7  */
};
static const uint16_t io_pin_map[IO_PORT_MAX] = {
    GPIO_Pin_5, GPIO_Pin_4, GPIO_Pin_15,
    GPIO_Pin_10, GPIO_Pin_4, GPIO_Pin_9,             /* P1~P6  */
    GPIO_Pin_9, GPIO_Pin_11, GPIO_Pin_13, GPIO_Pin_14,
    GPIO_Pin_7, GPIO_Pin_6, GPIO_Pin_14              /* D1~D7  */
};
static uint8_t io_mode[IO_PORT_MAX];
static uint8_t io_out[IO_PORT_MAX];

static void io_config(int idx, int mode)
{
    GPIO_InitTypeDef init;

    init.GPIO_Pin = io_pin_map[idx];
    init.GPIO_Speed = GPIO_Speed_50MHz;
    init.GPIO_Mode = (mode == 1) ? GPIO_Mode_Out_PP : GPIO_Mode_IPU;
    GPIO_Init((GPIO_TypeDef *)io_port_map[idx], &init);
    io_mode[idx] = (uint8_t)mode;
}

/* ---- ADC 模拟输入: 直接用 SDK getAI(inst), inst 1~6 = A1~A6 ---- */

static void io_init_all(void)
{
    /* DIG 口由 SDK InitDo 初始化 (原厂电气配置, 强驱动, 可直驱气泵等负载) */
    InitDo(0);
    for (int i = 0; i < IO_PORT_MAX; i++) {
        io_mode[i] = 1;   /* 默认输出语义 */
    }
}

static uint8_t io_handler(uint8_t op, uint8_t inst, uint8_t prop,
                          const uint8_t *in_data, uint8_t in_len,
                          uint8_t *out_data, uint8_t *out_len)
{
    if (inst < 1 || inst > IO_PORT_MAX) {
        /* inst=0 仅允许总线级 diag (SDK getAI 参数探测) */
        if (!(inst == 0 && op == OP_GET && prop == 0x04)) {
            return STATUS_RANGE_ERR;
        }
    }
    int idx = inst - 1;

    switch (op) {
    case OP_GET:
        switch (prop) {
        case 0x01: { /* value — 读电平 (输入模式读输入, 输出模式读输出) */
            uint8_t v;
            if (io_mode[idx] == 1) {
                v = GPIO_ReadOutputDataBit((GPIO_TypeDef *)io_port_map[idx],
                                           io_pin_map[idx]) ? 1 : 0;
            } else {
                v = GPIO_ReadInputDataBit((GPIO_TypeDef *)io_port_map[idx],
                                          io_pin_map[idx]) ? 1 : 0;
            }
            out_data[0] = v;
            *out_len = 1;
            return STATUS_OK;
        }
        case 0x02: /* mode */
            out_data[0] = io_mode[idx];
            *out_len = 1;
            return STATUS_OK;
        case 0x03: { /* analog (u16) — SDK getAI: inst 1~6 = A1~A6 */
            int v = getAI(inst);
            out_data[0] = (uint8_t)(v & 0xFF);
            out_data[1] = (uint8_t)((v >> 8) & 0xFF);
            *out_len = 2;
            return STATUS_OK;
        }
        case 0x04: { /* diag — SDK getAI 参数探测: getAI(1)~getAI(12) */
            for (int i = 0; i < 12 && i * 2 + 1 < 32; i++) {
                int v = getAI(i + 1);
                out_data[i * 2] = (uint8_t)(v & 0xFF);
                out_data[i * 2 + 1] = (uint8_t)((v >> 8) & 0xFF);
            }
            *out_len = 24;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    case OP_SET:
        switch (prop) {
        case 0x01: { /* value — 输出电平 (SDK 原生 SetDO) */
            if (in_len < 1) return STATUS_RANGE_ERR;
            uint8_t v = in_data[0] ? 1 : 0;
            SetDO(inst, v ? switch_on : switch_off);
            io_out[idx] = v;
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x02: { /* mode — 0=输入(上拉) 1=输出(推挽) */
            if (in_len < 1) return STATUS_RANGE_ERR;
            uint8_t m = in_data[0] ? 1 : 0;
            io_config(idx, m);
            *out_len = 0;
            return STATUS_OK;
        }
        default:
            return STATUS_READ_ONLY;
        }

    case OP_CALL:
        switch (prop) {
        case 0x80: { /* toggle */
            if (io_mode[idx] != 1) {
                io_config(idx, 1);
            }
            io_out[idx] ^= 1;
            SetDO(inst, io_out[idx] ? switch_on : switch_off);
            *out_len = 0;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    default:
        return STATUS_NOT_FOUND;
    }
}

/* ====================================================================
 * Service: LCD (0x60) — 屏幕显示
 *
 * 上位机写屏后自动停用心跳的 LCD 刷新 (lcd_user_active)。
 * user_main.c 的 render_lcd() 检查该标志。
 *
 * Commands:
 *   0x80 show_line   [u8 line(1~5)][str text ≤20 字符]
 *   0x81 clear       — 清屏
 *   0x82 clear_line  [u8 line(1~5)]
 *   0x83 auto        — 恢复心跳自动刷新
 * ==================================================================== */

volatile uint8_t lcd_user_active = 0;   /* user_main.c 引用 */

/* LCD 命令队列: 协议线程只写命令, 主循环执行显示 (单线程访问 LCD) */
volatile uint8_t  lcd_cmd_pending = 0;
volatile uint8_t  lcd_cmd_type   = 0;   /* 1=show_line 2=clear 3=clear_line */
volatile uint8_t  lcd_cmd_line   = 0;
char              lcd_cmd_text[21];

static uint8_t lcd_handler(uint8_t op, uint8_t inst, uint8_t prop,
                           const uint8_t *in_data, uint8_t in_len,
                           uint8_t *out_data, uint8_t *out_len)
{
    (void)inst;

    switch (op) {
    case OP_CALL:
        switch (prop) {
        case 0x80: { /* show_line */
            if (in_len < 2) return STATUS_RANGE_ERR;
            uint8_t line = in_data[0];
            if (line < 1 || line > 5) return STATUS_RANGE_ERR;
            uint8_t n = in_len - 1;
            if (n > 20) n = 20;
            memset(lcd_cmd_text, 0, sizeof(lcd_cmd_text));
            memcpy(lcd_cmd_text, in_data + 1, n);
            lcd_cmd_line = line;
            lcd_cmd_type = 1;
            lcd_cmd_pending = 1;
            lcd_user_active = 1;   /* 心跳停止刷新 */
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x81: /* clear */
            lcd_cmd_type = 2;
            lcd_cmd_pending = 1;
            lcd_user_active = 1;
            *out_len = 0;
            return STATUS_OK;
        case 0x82: { /* clear_line */
            if (in_len < 1) return STATUS_RANGE_ERR;
            uint8_t line = in_data[0];
            if (line < 1 || line > 5) return STATUS_RANGE_ERR;
            lcd_cmd_line = line;
            lcd_cmd_type = 3;
            lcd_cmd_pending = 1;
            lcd_user_active = 1;
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x83: /* auto — 恢复心跳刷新 (重画标题行) */
            lcd_cmd_type = 4;
            lcd_cmd_pending = 1;
            lcd_user_active = 0;
            *out_len = 0;
            return STATUS_OK;
        default:
            return STATUS_NOT_FOUND;
        }

    default:
        return STATUS_NOT_FOUND;
    }
}

/* 主循环调用: 执行挂起的 LCD 命令 (返回 1 表示已处理) */
int lcd_service_poll(void)
{
    if (!lcd_cmd_pending) return 0;
    lcd_cmd_pending = 0;

    if (lcd_cmd_type == 4) {
        /* 恢复心跳模式: 重画标题/分隔线 (3/4/5 行由 render_lcd 自动更新) */
        show(1, "%s", "MC602P FW v1.0");
        show(2, "%s", "------------------");
        LCD_Ram2LCD();
        return 1;
    }

    /* 首次用户命令: 清空心跳残留 (5 行 × 20 空格覆盖缓冲, 再整体刷屏) */
    for (int l = 1; l <= 5; l++) {
        show(l, "%s", "                    ");
    }

    switch (lcd_cmd_type) {
    case 1: /* show_line */
        show(lcd_cmd_line, "%s", lcd_cmd_text);
        break;
    case 2: /* clear */
        break;
    case 3: /* clear_line */
        show(lcd_cmd_line, "%s", "                    ");
        break;
    default:
        break;
    }
    LCD_Ram2LCD();
    return 1;
}

/* ====================================================================
 * 初始化
 * ==================================================================== */

void rx_process_start(void)
{
    /* 初始化 PID 实例 */
    for (int i = 0; i < MOTOR_MAX; i++) {
        pid_init(&motor_pid[i]);
    }

    /* 注册 Service (System + Motor + MecanumGroup + BTRemote + Stepper + Servo + Chassis) */
    proto_service_register(0xFE, "System",  system_handler);
    proto_service_register(0x01, "Motor",   motor_handler);
    proto_service_register(0x02, "Mecanum", mecanum_group_handler);
    proto_service_register(0x03, "BTRemote", btremote_handler);
    proto_service_register(0x30, "Stepper", stepper_handler);
    proto_service_register(0x20, "ServoBus", servobus_handler);
    proto_service_register(0x21, "ServoPWM", servopwm_handler);
    proto_service_register(0x04, "Chassis", chassis_handler);
    proto_service_register(0x50, "IO", io_handler);
    proto_service_register(0x60, "LCD", lcd_handler);

    /* PWM 舵机: 初始化定时器 + 打开舵机电源 */
    ServoInit();
    SERVO_PWR_ON();

    /* P1~P6 数字 IO */
    io_init_all();

    /* 启动 PID 控制线程 (200Hz, 5ms 周期) */
    ThreadStart(pid_control_loop);

    /* 底盘外环控制器 (200Hz) */
    chassis_init();
    chassis_start();

    /* 启动协议引擎 (USART1, COBS+CRC8) */
    RxFunc rx_handle_pc = protocol_config(UartPC_Sendbytes);
    setUartPC_RxHandle(rx_handle_pc);
}

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
#include <string.h>

/* ====================================================================
 * 常量
 * ==================================================================== */

#define MOTOR_MAX 6

/* ====================================================================
 * PID 控制循环 (5ms 周期, 200Hz)
 * ==================================================================== */

static MotorPID motor_pid[MOTOR_MAX];

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
        for (int i = 0; i < MOTOR_MAX; i++) {
            MotorPID *pid = &motor_pid[i];
            if (pid->mode == PID_MODE_OFF) continue;

            /* passthrough: 直接用 target 喂 SDK PID, 不做本地 PID 计算.
             * 这样避免双层套叠 (我们 PID + SDK PID) 以及 unit mismatch.
             * SDK 的内置 PID 是原厂调教, 性能 CV≈10%. */
            set_motor(i + 1, pid->target_speed);
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
            const char *ver = "MC602P v1.1";
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
                    set_motor(port, 0);
                } else {
                    pid_set_speed(pid, spd);
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
                    set_motor(port, 0);
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
            set_motor(port, 0);
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
                    set_motor(i + 1, 0);
                } else {
                    pid_set_speed(pid, spd);
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
                set_motor(i + 1, 0);
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
 * 初始化
 * ==================================================================== */

void rx_process_start(void)
{
    /* 初始化 PID 实例 */
    for (int i = 0; i < MOTOR_MAX; i++) {
        pid_init(&motor_pid[i]);
    }

    /* 注册 Service (System + Motor + MecanumGroup) */
    proto_service_register(0xFE, "System",  system_handler);
    proto_service_register(0x01, "Motor",   motor_handler);
    proto_service_register(0x02, "Mecanum", mecanum_group_handler);

    /* 启动 PID 控制线程 (200Hz, 5ms 周期) */
    ThreadStart(pid_control_loop);

    /* 启动协议引擎 (USART1, COBS+CRC8) */
    RxFunc rx_handle_pc = protocol_config(UartPC_Sendbytes);
    setUartPC_RxHandle(rx_handle_pc);
}

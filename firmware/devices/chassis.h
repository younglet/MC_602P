/**
 * chassis.h — Mecanum 底盘外环控制器 (SVC 0x04)
 *
 * 架构:
 *   - 状态: 当前位姿 (用 cos/sin 增量形式避免 atan2), 目标位姿, PID, 容差
 *   - 200 Hz 控制环: 读 4 编码器 → 增量 odometry → 极坐标 P-controller
 *                    → 逆运动学 → set_motor × 4 (喂 SDK 速度闭环)
 *   - 几何参数由 host 通过 SET_GEOMETRY 推送
 *
 * 数据格式约定:
 *   - 内部: float (Cortex-M3 软浮点开销可忽略, 200Hz × ~100 ops ≈ 0.1% CPU)
 *   - 协议 wire: 定点 (避免协议层解析浮点的兼容性问题)
 *       线性 cm   × 100    → i32
 *       角度 rad   × 1000   → i32
 *       PID K      × 1000   → u16
 *       容差 cm    × 10     → u16
 *       容差 deg   × 10     → u16
 *       速度 cm/s  整数     → u16
 *       角速 deg/s 整数     → u16
 *       距离 m     整数     → u32
 *
 * 协议 (SVC 0x04):
 *   GET/SET PROPs:
 *     0x01 POSE             i32×3  (x*100, y*100, θ*1000)
 *     0x02 STATUS           u8×2   (state, sub_code)
 *     0x03 TWIST_BODY       i16×3  (vx*100, vy*100, ω*1000)
 *     0x06 STATS            u32×3  (distance_cm, arrived_count, runtime_s)
 *     0x10 GEOMETRY         u16×3+u16+u16+u16 (track*10, base*10, radius*10, ppr, roller*1000)
 *     0x20-0x25 PID_*_K*    u16    (×1000)
 *     0x26 TOLERANCE_POS    u16    (cm*10)
 *     0x27 TOLERANCE_ANG    u16    (deg*10)
 *     0x28 MAX_VEL_LIN      u16    (cm/s)
 *     0x29 MAX_VEL_ANG      u16    (deg/s)
 *     0x30 TIMEOUT          u16    (ms)
 *   CALL:
 *     0x80 GOTO_POSE        i32×3 + u8  (x*100, y*100, θ*1000, max_speed)
 *     0x81 ABORT            ()
 *     0x82 SET_TWIST        i16×3  (vx*100, vy*100, ω*1000)
 *     0x83 RESET_ODOM       ()
 *     0x84 EMERGENCY_STOP   ()
 *     0x85 CLEAR_ERROR      ()
 *     0x86 RESET_STATS      ()
 */

#ifndef __CHASSIS_H__
#define __CHASSIS_H__

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ===== 状态机 ===== */
#define CH_IDLE         0
#define CH_RUNNING      1
#define CH_ARRIVED      2
#define CH_ABORTED      3
#define CH_STALLED      4
#define CH_TIMED_OUT    5
#define CH_ERROR        6
#define CH_EMERGENCY    7

/* ===== 模式 ===== */
#define CH_MODE_OFF         0   /* 不跑外环, 完全停车 */
#define CH_MODE_GOTO        1   /* 外环: 去目标点 */
#define CH_MODE_TWIST       2   /* 外环 off, host 直接给速度 (透传) */

/* ===== 错误子码 (sub_code) ===== */
#define CH_ERR_NONE         0
#define CH_ERR_GEOMETRY     1   /* 几何未配置 */

/* ===== 默认值 (内部 float) ===== */
#define CH_DEF_TRACK        30.0f    /* cm */
#define CH_DEF_WHEEL_BASE   28.0f    /* cm */
#define CH_DEF_WHEEL_RADIUS 3.0f     /* cm */
#define CH_DEF_ENCODER_PPR  2048
#define CH_DEF_ROLLER_ADJ   1.052f

/* 极坐标 P-controller 默认 */
#define CH_DEF_KP_RHO       1.5f
#define CH_DEF_KP_ALPHA     2.5f
#define CH_DEF_KP_BETA      0.8f
#define CH_DEF_KI_RHO       0.0f
#define CH_DEF_KI_ALPHA     0.0f
#define CH_DEF_KI_BETA      0.0f
#define CH_DEF_KD_RHO       0.0f
#define CH_DEF_KD_ALPHA     0.0f
#define CH_DEF_KD_BETA      0.0f

/* 容差/速度默认 */
#define CH_DEF_POS_TOL      2.0f     /* cm */
#define CH_DEF_ANG_TOL      0.052f   /* rad (~3 deg) */
#define CH_DEF_MAX_V        40.0f    /* cm/s */
#define CH_DEF_MAX_W        1.57f    /* rad/s (~90 deg/s) */
#define CH_DEF_TIMEOUT_MS   10000

/* ===== 控制环周期 (5ms = 200Hz) ===== */
#define CH_DT               0.005f

/* ===== 全局底盘状态 ===== */
typedef struct {
    /* 模式 / 状态 */
    uint8_t mode;
    uint8_t state;
    uint8_t sub_code;
    uint8_t last_error;

    /* 几何 (cm) */
    float track;
    float wheel_base;
    float wheel_radius;
    int32_t encoder_ppr;
    float roller_adj;

    /* 派生 */
    float tan_r;            /* tan(π/4 × roller_adj) */
    float wc;               /* (track/2)*tan_r + (wheel_base/2) */
    float enc_to_dist;      /* 单脉冲对应距离 (cm) */

    /* 当前位姿 (cm, 用 cos/sin 增量表示) */
    float x;
    float y;
    float cos_t;            /* cos(θ), 初值 1.0 */
    float sin_t;            /* sin(θ), 初值 0.0 */
    float theta;            /* rad, 用于上报 */
    uint32_t norm_counter;  /* cos²+sin² 归一化计数 */

    /* 目标位姿 (cm, rad) */
    float target_x;
    float target_y;
    float target_theta;

    /* 目标车身速度 (TWIST 模式, cm/s, rad/s) */
    float target_vx;
    float target_vy;
    float target_w;

    /* 上次编码器 (odometry baseline) */
    int32_t last_enc[4];
    uint8_t has_baseline;

    /* PID (极坐标 P-controller) */
    float kp_rho, kp_alpha, kp_beta;
    float ki_rho, ki_alpha, ki_beta;
    float kd_rho, kd_alpha, kd_beta;

    /* 积分累积 */
    float i_rho, i_alpha, i_beta;
    float prev_rho, prev_alpha, prev_beta;

    /* 容差 */
    float pos_tol;
    float ang_tol;

    /* 速度上限 */
    float max_v;
    float max_w;
    uint8_t max_speed_cmd;  /* 喂 set_motor 的上限, 5~100 */

    /* 超时 */
    uint32_t timeout_ms;
    uint32_t move_start_ms;

    /* 统计 */
    uint32_t distance_cm_x100;     /* 总里程 (cm ×100) */
    uint32_t arrived_count;
    uint32_t start_time_s;
} ChassisState;

/* ===== 全局访问 ===== */
ChassisState* chassis_get_state(void);

/* ===== 初始化 ===== */
void chassis_init(void);

/* ===== Service handler (注册到 dispatcher) ===== */
uint8_t chassis_handler(uint8_t op, uint8_t inst, uint8_t prop,
                         const uint8_t *in_data, uint8_t in_len,
                         uint8_t *out_data, uint8_t *out_len);

#ifdef __cplusplus
}
#endif

#endif /* __CHASSIS_H__ */
/**
 * pid.h — 增量式 PID 控制器（嵌入式友好，无浮点依赖）
 *
 * 用于电机的速度闭环和位置闭环控制。
 * 定时器中断中调用 pid_update()，输出直接送给 set_motor()。
 */

#ifndef EXTERNLIB_PID_H_
#define EXTERNLIB_PID_H_

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ====================================================================
 * PID 模式
 * ==================================================================== */

#define PID_MODE_OFF      0   /* 关闭 PID，直通 set_motor */
#define PID_MODE_SPEED    1   /* 速度闭环：setpoint = 目标速度(-100~100) */
#define PID_MODE_POSITION 2   /* 位置闭环：setpoint = 目标编码器脉冲数 */

/* ====================================================================
 * PID 状态（每个电机一个实例）
 * ==================================================================== */

typedef struct {
    /* 用户可调参数（×1000 定点，如 200 = 0.2） */
    uint16_t kp;      /* 比例系数 ×1000 */
    uint16_t ki;      /* 积分系数 ×1000 */
    uint16_t kd;      /* 微分系数 ×1000 */

    /* 控制参数 */
    uint8_t  mode;            /* PID_MODE_OFF / SPEED / POSITION */
    int32_t  target_position; /* 位置模式目标（编码器脉冲） */
    int8_t   target_speed;    /* 速度模式目标（-100~100） */
    int8_t   max_speed;       /* 位置模式最大转速（绝对值） */

    /* 内部状态（自动计算） */
    int32_t  prev_encoder;
    int32_t  integral;
    int16_t  prev_error;
    int8_t   output;          /* 最新 PID 输出（-100~100），直接喂 set_motor */

    /* 到位判定 */
    uint16_t tolerance;       /* 位置容差（编码器脉冲） */
    uint16_t move_timeout;    /* 位置移动超时 (ms)，0=永不超时 */
    uint8_t  at_target;       /* 1=已到达目标 */
    uint8_t  timed_out;       /* 1=移动超时 */
    uint8_t  stalled;         /* 1=堵转 */
    float    move_start_time; /* 位置移动开始时间 */
    float    last_move_time;  /* 编码器最后变化时间 */
    int32_t  last_encoder;    /* 上次编码器值 */
    uint16_t stall_timeout;   /* 堵转判定超时 (ms)，默认 500 */
} MotorPID;

/* ====================================================================
 * API
 * ==================================================================== */

/** 初始化 PID 实例为默认参数。 */
void pid_init(MotorPID *pid);

/**
 * 执行一次 PID 计算（由定时器线程调用，周期 5-10ms）。
 *
 * @param pid       PID 实例
 * @param encoder   当前编码器值
 * @return          输出速度（-100~100），可直接喂 set_motor()
 */
int8_t pid_update(MotorPID *pid, int32_t encoder);

/**
 * 设置目标速度（速度闭环模式）。
 * 自动切换到 PID_MODE_SPEED。
 */
void pid_set_speed(MotorPID *pid, int8_t speed);

/**
 * 设置目标位置（位置闭环模式）。
 * 自动切换到 PID_MODE_POSITION。
 *
 * @param pid        PID 实例
 * @param position   目标编码器脉冲数
 * @param max_speed  最大转速（绝对值，默认 80）
 */
void pid_set_position(MotorPID *pid, int32_t position, int8_t max_speed);

/** 紧急停止。 */
void pid_stop(MotorPID *pid);

#ifdef __cplusplus
}
#endif

#endif /* EXTERNLIB_PID_H_ */

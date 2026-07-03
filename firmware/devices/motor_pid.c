/**
 * pid.c — PID 控制器实现
 *
 * 使用增量式 PID + 积分限幅 + 输出限幅。
 * 定点运算（×1000），避免浮点开销。
 */

#include "motor_pid.h"
#include "whalesbot.h"   /* for seconds() */
#include <string.h>

/* ====================================================================
 * 默认参数（vision.md §8 推荐值）
 * ==================================================================== */

#define DEFAULT_KP        200     /* 0.200 ×1000 */
#define DEFAULT_KI        1       /* 0.001 ×1000 */
#define DEFAULT_KD        4       /* 0.004 ×1000 */
#define DEFAULT_MAX_SPEED 80
#define DEFAULT_TOLERANCE 80      /* 编码器脉冲 */
#define DEFAULT_MOVE_TIMEOUT 3000 /* 位置移动默认超时 3 秒 */
#define DEFAULT_STALL_TIMEOUT 1000 /* 堵转判定 1 秒 */

/* 积分限幅（防止 windup） */
#define INTEGRAL_MAX      50000
#define INTEGRAL_MIN     -50000

/* 输出限幅 */
#define OUTPUT_MAX        100
#define OUTPUT_MIN       -100

/* ====================================================================
 * 工具宏
 * ==================================================================== */

#define LIMIT(v, lo, hi)  (((v) > (hi)) ? (hi) : (((v) < (lo)) ? (lo) : (v)))

/* ====================================================================
 * 实现
 * ==================================================================== */

void pid_init(MotorPID *pid)
{
    memset(pid, 0, sizeof(MotorPID));
    pid->kp        = DEFAULT_KP;
    pid->ki        = DEFAULT_KI;
    pid->kd        = DEFAULT_KD;
    pid->mode      = PID_MODE_OFF;
    pid->max_speed = DEFAULT_MAX_SPEED;
    pid->tolerance = DEFAULT_TOLERANCE;
    pid->move_timeout = DEFAULT_MOVE_TIMEOUT;
    pid->stall_timeout = DEFAULT_STALL_TIMEOUT;
    pid->last_encoder = 0;
    pid->last_move_time = 0;
}

int8_t pid_update(MotorPID *pid, int32_t encoder)
{
    if (pid->mode == PID_MODE_OFF) {
        pid->output = 0;
        return 0;
    }

    int32_t setpoint;
    int32_t error;

    /* ---- 计算误差 ---- */
    if (pid->mode == PID_MODE_POSITION) {
        setpoint = pid->target_position;
        error = setpoint - encoder;
    } else {
        /* PID_MODE_SPEED: setpoint 是速度，encoder 差分得实际速度 */
        setpoint = pid->target_speed;
        /* 用编码器差分估算实际速度（脉冲/周期） */
        int32_t delta = encoder - pid->prev_encoder;
        pid->prev_encoder = encoder;
        error = setpoint - delta;  /* 速度误差 */
    }

    /* ---- 到位判定（位置模式） ---- */
    if (pid->mode == PID_MODE_POSITION) {
        int32_t abs_err = (error < 0) ? -error : error;
        pid->at_target = (abs_err <= (int32_t)pid->tolerance) ? 1 : 0;
        /* 超时判定 */
        if (!pid->at_target && pid->move_timeout > 0) {
            uint32_t elapsed = (uint32_t)((seconds() - pid->move_start_time) * 1000.0f);
            if (elapsed > pid->move_timeout) {
                pid->timed_out = 1;
            }
        }
    }

    /* ---- 堵转判定（任意模式） ---- */
    if (pid->mode != PID_MODE_OFF && pid->stall_timeout > 0) {
        if (encoder != pid->last_encoder) {
            pid->last_encoder = encoder;
            pid->last_move_time = seconds();
            pid->stalled = 0;
        } else {
            uint32_t stall_ms = (uint32_t)((seconds() - pid->last_move_time) * 1000.0f);
            if (stall_ms > pid->stall_timeout) {
                pid->stalled = 1;
                pid->mode = PID_MODE_OFF;  /* 堵转后停车，等新指令 */
            }
        }
    } else {
        pid->at_target = 0;
    }

    /* ---- PID 计算（定点 ×1000） ---- */

    /* 比例项 */
    int32_t p_term = ((int32_t)pid->kp * error) / 1000;

    /* 积分项（带限幅） */
    pid->integral += error;
    pid->integral = LIMIT(pid->integral, INTEGRAL_MIN, INTEGRAL_MAX);
    int32_t i_term = ((int32_t)pid->ki * pid->integral) / 1000;

    /* 微分项（误差差分，避免微分冲击） */
    int32_t d_term = ((int32_t)pid->kd * (error - pid->prev_error)) / 1000;
    pid->prev_error = (int16_t)error;

    /* 合成输出 */
    int32_t output = p_term + i_term + d_term;

    /* 位置模式下限制最大转速 */
    if (pid->mode == PID_MODE_POSITION) {
        int32_t limit = (int32_t)pid->max_speed;
        output = LIMIT(output, -limit, limit);
    } else {
        output = LIMIT(output, OUTPUT_MIN, OUTPUT_MAX);
    }

    pid->output = (int8_t)output;
    return pid->output;
}

void pid_set_speed(MotorPID *pid, int8_t speed)
{
    pid->mode = PID_MODE_SPEED;
    pid->target_speed = speed;
    /* 切换模式时清除积分和差分历史 */
    pid->integral = 0;
    pid->prev_error = 0;
    pid->stalled = 0;
    pid->last_move_time = seconds();
}

void pid_set_position(MotorPID *pid, int32_t position, int8_t max_speed)
{
    pid->mode = PID_MODE_POSITION;
    pid->target_position = position;
    if (max_speed > 0) {
        pid->max_speed = max_speed;
    }
    pid->integral = 0;
    pid->prev_error = 0;
    pid->at_target = 0;
    pid->timed_out = 0;
    pid->move_start_time = seconds();  /* 记录开始时间 */
}

void pid_stop(MotorPID *pid)
{
    pid->mode = PID_MODE_OFF;
    pid->output = 0;
    pid->integral = 0;
    pid->prev_error = 0;
    pid->at_target = 0;
}

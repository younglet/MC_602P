/**
 * chassis.c — Mecanum 底盘外环控制器 (SVC 0x04)
 *
 * 200Hz 控制环: 读 4 编码器 → 增量里程计 → 极坐标 P-controller
 * → 逆运动学 → set_motor × 4 (喂 SDK 速度闭环)。
 *
 * 几何参数由 host 通过 SET_GEOMETRY 推送 (创建时指定轴距/轮距/轮径)。
 *
 * 协议详见 chassis.h。运动学模型与上位机旧 motion/mecanum.py 一致
 * (物理 roller 角模型, baidu_smartcar 参数)。
 */

#include "chassis.h"
#include "dispatcher.h"
#include "services.h"   /* motor_encoder / set_motor 由本模块外部提供 */
#include <math.h>
#include <string.h>

extern int motor_encoder(int port);
extern void set_motor(int port, int speed);

/* ====================================================================
 * 全局状态
 * ==================================================================== */

static ChassisState g_ch;

ChassisState *chassis_get_state(void)
{
    return &g_ch;
}

/* ====================================================================
 * 数学工具
 * ==================================================================== */

static float wrap_pi(float a)
{
    while (a > (float)M_PI) a -= 2.0f * (float)M_PI;
    while (a <= -(float)M_PI) a += 2.0f * (float)M_PI;
    return a;
}

static float clampf(float v, float lo, float hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

/* ====================================================================
 * 初始化
 * ==================================================================== */

void chassis_init(void)
{
    memset(&g_ch, 0, sizeof(g_ch));

    /* 几何 (默认值, host 可 SET_GEOMETRY 覆盖) */
    g_ch.track        = CH_DEF_TRACK;
    g_ch.wheel_base   = CH_DEF_WHEEL_BASE;
    g_ch.wheel_radius = CH_DEF_WHEEL_RADIUS;
    g_ch.encoder_ppr  = CH_DEF_ENCODER_PPR;
    g_ch.roller_adj   = CH_DEF_ROLLER_ADJ;

    /* 派生量 */
    g_ch.tan_r = tanf((float)M_PI / 4.0f * g_ch.roller_adj);
    g_ch.wc = (g_ch.track / 2.0f) * g_ch.tan_r + (g_ch.wheel_base / 2.0f);
    g_ch.enc_to_dist = (2.0f * (float)M_PI * g_ch.wheel_radius)
                     / (float)g_ch.encoder_ppr;

    /* 位姿: cos(0)=1, sin(0)=0 */
    g_ch.cos_t = 1.0f;

    /* PID */
    g_ch.kp_rho   = CH_DEF_KP_RHO;
    g_ch.kp_alpha = CH_DEF_KP_ALPHA;
    g_ch.kp_beta  = CH_DEF_KP_BETA;

    /* 容差 / 速度 */
    g_ch.pos_tol   = CH_DEF_POS_TOL;
    g_ch.ang_tol   = CH_DEF_ANG_TOL;
    g_ch.max_v     = CH_DEF_MAX_V;
    g_ch.max_w     = CH_DEF_MAX_W;
    g_ch.max_speed_cmd = 80;
    g_ch.timeout_ms = CH_DEF_TIMEOUT_MS;

    /* 固件直读摇杆默认参数 */
    g_ch.direct_mode     = 0;
    g_ch.direct_deadzone = 15;
    g_ch.direct_max_v    = 60.0f;
    g_ch.direct_max_w    = 0.8f;
    g_ch.direct_invert   = 0;
    g_ch.direct_gain     = 0;

    g_ch.state  = CH_IDLE;
    g_ch.mode   = CH_MODE_OFF;
    g_ch.start_time_s = (uint32_t)seconds();
}

/* ====================================================================
 * 逆运动学 (body cm/s, rad/s → wheel cm/s)
 * ==================================================================== */

static void chassis_inverse(float vx, float vy, float w,
                            float *w1, float *w2, float *w3, float *w4)
{
    float t  = g_ch.tan_r;
    float wc = g_ch.wc;
    *w1 =  vx + t * vy + wc * w;
    *w2 = -vx + t * vy + wc * w;
    *w3 = -vx - t * vy + wc * w;
    *w4 =  vx - t * vy + wc * w;
}

/* ====================================================================
 * 前向运动学 (wheel cm/s → body)
 * ==================================================================== */

static void chassis_forward(float w1, float w2, float w3, float w4,
                            float *vx, float *vy, float *w)
{
    float t  = g_ch.tan_r;
    float wc = g_ch.wc;
    *vx = ( w1 - w2 - w3 + w4) / 4.0f;
    *vy = ( w1 + w2 - w3 - w4) / (4.0f * t);
    *w  = ( w1 + w2 + w3 + w4) / (4.0f * wc);
}

/* ====================================================================
 * 增量里程计
 * ==================================================================== */

static void chassis_odometry(int32_t e[4])
{
    if (!g_ch.has_baseline) {
        /* 首次: 只设基准, 不算位移 (避免瞬移) */
        memcpy(g_ch.last_enc, e, sizeof(g_ch.last_enc));
        g_ch.has_baseline = 1;
        return;
    }

    float d[4];
    for (int i = 0; i < 4; i++) {
        d[i] = (float)(e[i] - g_ch.last_enc[i]) * g_ch.enc_to_dist;
        g_ch.last_enc[i] = e[i];
    }

    float vx, vy, w;
    chassis_forward(d[0], d[1], d[2], d[3], &vx, &vy, &w);

    /* 用 cos/sin 增量形式更新, 避免每帧 atan2 */
    float x_inc = vx * g_ch.cos_t - vy * g_ch.sin_t;
    float y_inc = vx * g_ch.sin_t + vy * g_ch.cos_t;
    g_ch.x += x_inc;
    g_ch.y += y_inc;

    float new_cos = g_ch.cos_t * cosf(w) - g_ch.sin_t * sinf(w);
    float new_sin = g_ch.cos_t * sinf(w) + g_ch.sin_t * cosf(w);
    g_ch.cos_t = new_cos;
    g_ch.sin_t = new_sin;
    g_ch.theta = wrap_pi(g_ch.theta + w);

    /* 定期归一化 cos²+sin² 漂移 */
    if (++g_ch.norm_counter >= 1000) {
        g_ch.norm_counter = 0;
        float n = sqrtf(g_ch.cos_t * g_ch.cos_t + g_ch.sin_t * g_ch.sin_t);
        if (n > 1e-6f) {
            g_ch.cos_t /= n;
            g_ch.sin_t /= n;
        }
    }

    /* 里程统计 (cm×100) */
    g_ch.distance_cm_x100 += (uint32_t)(sqrtf(vx * vx + vy * vy) * 100.0f);
}

/* ====================================================================
 * 极坐标 P-controller (GOTO)
 * ==================================================================== */

static void chassis_goto_controller(float *out_vx, float *out_vy, float *out_w)
{
    float dx = g_ch.target_x - g_ch.x;
    float dy = g_ch.target_y - g_ch.y;
    float rho = sqrtf(dx * dx + dy * dy);

    /* 角度误差 */
    float alpha = wrap_pi(atan2f(dy, dx) - g_ch.theta);
    float beta  = wrap_pi(g_ch.target_theta - g_ch.theta - alpha);

    /* 到达判定 */
    float dtheta = wrap_pi(g_ch.target_theta - g_ch.theta);
    if (rho < g_ch.pos_tol && fabsf(dtheta) < g_ch.ang_tol) {
        g_ch.state = CH_ARRIVED;
        g_ch.arrived_count++;
        *out_vx = 0.0f;
        *out_vy = 0.0f;
        *out_w  = 0.0f;
        return;
    }

    /* 超时判定 */
    if (g_ch.timeout_ms > 0 &&
        (uint32_t)seconds() * 1000 - g_ch.move_start_ms > g_ch.timeout_ms) {
        g_ch.state = CH_TIMED_OUT;
        *out_vx = 0.0f;
        *out_vy = 0.0f;
        *out_w  = 0.0f;
        return;
    }

    /* 极坐标控制量 (带积分/微分, 默认 0) */
    float i_rho = g_ch.i_rho + rho * CH_DT;
    float i_alpha = g_ch.i_alpha + alpha * CH_DT;
    float i_beta  = g_ch.i_beta  + beta  * CH_DT;
    g_ch.i_rho = i_rho;
    g_ch.i_alpha = i_alpha;
    g_ch.i_beta = i_beta;

    float d_rho = (rho - g_ch.prev_rho) / CH_DT;
    float d_alpha = (alpha - g_ch.prev_alpha) / CH_DT;
    float d_beta  = (beta  - g_ch.prev_beta)  / CH_DT;
    g_ch.prev_rho = rho;
    g_ch.prev_alpha = alpha;
    g_ch.prev_beta = beta;

    float v = g_ch.kp_rho * rho + g_ch.ki_rho * i_rho + g_ch.kd_rho * d_rho;
    float w = g_ch.kp_alpha * alpha + g_ch.ki_alpha * i_alpha
            + g_ch.kd_alpha * d_alpha
            + g_ch.kp_beta * beta + g_ch.ki_beta * i_beta
            + g_ch.kd_beta * d_beta;

    /* 限幅 */
    v = clampf(v, -g_ch.max_v, g_ch.max_v);
    w = clampf(w, -g_ch.max_w, g_ch.max_w);

    /* 车身系: 极坐标控制 v 沿 α 方向 → (vx, vy) */
    *out_vx = v * cosf(alpha);
    *out_vy = v * sinf(alpha);
    *out_w  = w;
}

/* ====================================================================
 * 200Hz 控制环
 * ==================================================================== */

static void chassis_control_loop(void)
{
    while (1) {
        /* 读 4 编码器 (M1~M4) */
        int32_t e[4];
        for (int i = 0; i < 4; i++) {
            e[i] = motor_encoder(i + 1);
        }

        /* 里程计 (始终更新, 无论模式) */
        chassis_odometry(e);

        float vx = 0.0f, vy = 0.0f, w = 0.0f;
        uint8_t apply = 1;

        switch (g_ch.mode) {
        case CH_MODE_GOTO:
            chassis_goto_controller(&vx, &vy, &w);
            break;
        case CH_MODE_TWIST:
            /* host 直接给速度 (透传), 已在 SET_TWIST 写入目标 */
            vx = g_ch.target_vx;
            vy = g_ch.target_vy;
            w  = g_ch.target_w;
            break;
        case CH_MODE_DIRECT: {
            /* 固件直读摇杆: BTSTICK1=前后 BTSTICK2=横移 BTSTICK4=旋转
             * 摇杆范围: 0~100 / 0~255 / 0~1023, 居中 = 满量程/2。
             * 启动校准: 前 20 帧 (100ms) 采样平均 = 中心值。 */
            static int calib_count = 0;
            static long calib_sum = 0;
            static int stick_center = 0;

            int s1 = get_bt_remote_control(BTSTICK1);
            int s2 = get_bt_remote_control(BTSTICK2);
            int s4 = get_bt_remote_control(BTSTICK4);

            /* 手柄断开 → 自动停车 */
            if (!getbtstatus()) {
                vx = 0.0f; vy = 0.0f; w = 0.0f;
                break;
            }

            if (calib_count < 20) {
                calib_sum += s1 + s2 + s4;
                calib_count++;
                stick_center = (int)(calib_sum / (calib_count * 3));
                vx = 0.0f; vy = 0.0f; w = 0.0f;   /* 校准期间不动 */
                break;
            }
            if (stick_center < 10) {
                stick_center = 100;   /* 异常兜底 */
            }

            /* 摇杆 → -1.0~+1.0 (带死区) */
            float dz = (float)g_ch.direct_deadzone / 100.0f;
            float f1 = (float)(s1 - stick_center) / (float)stick_center;
            float f2 = (float)(s2 - stick_center) / (float)stick_center;
            float f4 = (float)(s4 - stick_center) / (float)stick_center;

            if (fabsf(f1) < dz) f1 = 0.0f;
            if (fabsf(f2) < dz) f2 = 0.0f;
            if (fabsf(f4) < dz) f4 = 0.0f;

            /* 可选指数曲线: 低灵敏度区更细腻 */
            if (g_ch.direct_gain > 0) {
                float g = 1.0f + 0.3f * g_ch.direct_gain;
                float sgn1 = (f1 < 0) ? -1.0f : 1.0f;
                float sgn2 = (f2 < 0) ? -1.0f : 1.0f;
                float sgn4 = (f4 < 0) ? -1.0f : 1.0f;
                f1 = sgn1 * powf(fabsf(f1), g);
                f2 = sgn2 * powf(fabsf(f2), g);
                f4 = sgn4 * powf(fabsf(f4), g);
            }

            /* 方向反转 */
            if (g_ch.direct_invert & 0x01) f1 = -f1;
            if (g_ch.direct_invert & 0x02) f2 = -f2;
            if (g_ch.direct_invert & 0x04) f4 = -f4;

            vx = f1 * g_ch.direct_max_v;
            vy = f2 * g_ch.direct_max_v;
            w  = f4 * g_ch.direct_max_w;
            break;
        }
        default: /* OFF */
            apply = 0;
            break;
        }

        if (apply) {
            /* 逆运动学 → 电机命令 (-100~+100)
             * scale: TWIST 满量程 100%; GOTO 受 max_speed_cmd 上限限制 */
            float w1, w2, w3, w4;
            chassis_inverse(vx, vy, w, &w1, &w2, &w3, &w4);

            float scale = (g_ch.mode == CH_MODE_TWIST)
                        ? (100.0f / g_ch.max_v)
                        : ((float)g_ch.max_speed_cmd / g_ch.max_v);
            int m1 = (int)clampf(w1 * scale, -100.0f, 100.0f);
            int m2 = (int)clampf(w2 * scale, -100.0f, 100.0f);
            int m3 = (int)clampf(w3 * scale, -100.0f, 100.0f);
            int m4 = (int)clampf(w4 * scale, -100.0f, 100.0f);

            set_motor(1, m1);
            set_motor(2, m2);
            set_motor(3, m3);
            set_motor(4, m4);
        } else if (g_ch.state == CH_EMERGENCY) {
            set_motor(1, 0);
            set_motor(2, 0);
            set_motor(3, 0);
            set_motor(4, 0);
        }

        wait(CH_DT);  /* 5ms → 200Hz */
    }
}

/* ====================================================================
 * Service handler (SVC 0x04)
 * ==================================================================== */

static void wire_i32(uint8_t *out, int32_t v)
{
    out[0] = (uint8_t)(v & 0xFF);
    out[1] = (uint8_t)((v >> 8) & 0xFF);
    out[2] = (uint8_t)((v >> 16) & 0xFF);
    out[3] = (uint8_t)((v >> 24) & 0xFF);
}

static void wire_u16(uint8_t *out, uint16_t v)
{
    out[0] = (uint8_t)(v & 0xFF);
    out[1] = (uint8_t)((v >> 8) & 0xFF);
}

static int32_t rd_i32(const uint8_t *in)
{
    return (int32_t)in[0] | ((int32_t)in[1] << 8)
         | ((int32_t)in[2] << 16) | ((int32_t)in[3] << 24);
}

uint8_t chassis_handler(uint8_t op, uint8_t inst, uint8_t prop,
                         const uint8_t *in_data, uint8_t in_len,
                         uint8_t *out_data, uint8_t *out_len)
{
    (void)inst;  /* 底盘单例 */

    switch (op) {
    /* ─────────────────────────── GET ─────────────────────────── */
    case OP_GET:
        switch (prop) {
        case 0x01: { /* POSE: i32×3 (x*100, y*100, θ*1000) */
            wire_i32(out_data, (int32_t)(g_ch.x * 100.0f));
            wire_i32(out_data + 4, (int32_t)(g_ch.y * 100.0f));
            wire_i32(out_data + 8, (int32_t)(g_ch.theta * 1000.0f));
            *out_len = 12;
            return STATUS_OK;
        }
        case 0x02: { /* STATUS: u8×2 (state, sub_code) */
            out_data[0] = g_ch.state;
            out_data[1] = g_ch.sub_code;
            *out_len = 2;
            return STATUS_OK;
        }
        case 0x03: { /* TWIST_BODY: i16×3 (vx*100, vy*100, ω*1000) */
            int16_t vx = (int16_t)(g_ch.target_vx * 100.0f);
            int16_t vy = (int16_t)(g_ch.target_vy * 100.0f);
            int16_t w  = (int16_t)(g_ch.target_w  * 1000.0f);
            out_data[0] = (uint8_t)(vx & 0xFF);
            out_data[1] = (uint8_t)((vx >> 8) & 0xFF);
            out_data[2] = (uint8_t)(vy & 0xFF);
            out_data[3] = (uint8_t)((vy >> 8) & 0xFF);
            out_data[4] = (uint8_t)(w & 0xFF);
            out_data[5] = (uint8_t)((w >> 8) & 0xFF);
            *out_len = 6;
            return STATUS_OK;
        }
        case 0x06: { /* STATS: u32×3 */
            uint32_t now = (uint32_t)seconds();
            uint32_t runtime = (now > g_ch.start_time_s)
                             ? (now - g_ch.start_time_s) : 0;
            wire_i32(out_data, (int32_t)g_ch.distance_cm_x100);
            wire_i32(out_data + 4, (int32_t)g_ch.arrived_count);
            wire_i32(out_data + 8, (int32_t)runtime);
            *out_len = 12;
            return STATUS_OK;
        }
        case 0x10: { /* GEOMETRY: u16×3+u16+u16+u16 */
            wire_u16(out_data, (uint16_t)(g_ch.track * 10.0f));
            wire_u16(out_data + 2, (uint16_t)(g_ch.wheel_base * 10.0f));
            wire_u16(out_data + 4, (uint16_t)(g_ch.wheel_radius * 10.0f));
            wire_u16(out_data + 6, (uint16_t)g_ch.encoder_ppr);
            wire_u16(out_data + 8, (uint16_t)(g_ch.roller_adj * 1000.0f));
            *out_len = 10;
            return STATUS_OK;
        }
        case 0x20: /* PID_*_K* (u16 ×1000) */
        case 0x21:
        case 0x22:
        case 0x23:
        case 0x24:
        case 0x25:
        case 0x26: /* TOLERANCE_POS (u16 cm×10) */
        case 0x27: /* TOLERANCE_ANG (u16 deg×10) */
        case 0x28: /* MAX_VEL_LIN (u16 cm/s) */
        case 0x29: /* MAX_VEL_ANG (u16 deg/s) */
        case 0x30: /* TIMEOUT (u16 ms) */
        case 0x32: /* DIRECT_MODE (u8) */
        case 0x33: /* DIRECT_DEADZONE (u8) */
        case 0x34: /* DIRECT_MAX_V (u16) */
        case 0x35: /* DIRECT_MAX_W (u16) */
        case 0x36: /* DIRECT_INVERT (u8) */
        case 0x37: /* DIRECT_GAIN (u8) */
        {
            float *f = NULL;
            switch (prop) {
            case 0x20: f = &g_ch.kp_rho;   break;
            case 0x21: f = &g_ch.kp_alpha; break;
            case 0x22: f = &g_ch.kp_beta;  break;
            case 0x23: f = &g_ch.ki_rho;   break;
            case 0x24: f = &g_ch.ki_alpha; break;
            case 0x25: f = &g_ch.ki_beta;  break;
            default: break;
            }
            if (f) {
                wire_u16(out_data, (uint16_t)(*f * 1000.0f));
            } else if (prop == 0x26) {
                wire_u16(out_data, (uint16_t)(g_ch.pos_tol * 10.0f));
            } else if (prop == 0x27) {
                wire_u16(out_data, (uint16_t)(g_ch.ang_tol * 180.0f / (float)M_PI * 10.0f));
            } else if (prop == 0x28) {
                wire_u16(out_data, (uint16_t)g_ch.max_v);
            } else if (prop == 0x29) {
                wire_u16(out_data, (uint16_t)(g_ch.max_w * 180.0f / (float)M_PI));
            } else if (prop == 0x30) {
                wire_u16(out_data, (uint16_t)g_ch.timeout_ms);
            } else if (prop == 0x32) {
                out_data[0] = g_ch.direct_mode;
                *out_len = 1;
                return STATUS_OK;
            } else if (prop == 0x33) {
                out_data[0] = g_ch.direct_deadzone;
                *out_len = 1;
                return STATUS_OK;
            } else if (prop == 0x34) {
                wire_u16(out_data, (uint16_t)g_ch.direct_max_v);
            } else if (prop == 0x35) {
                wire_u16(out_data, (uint16_t)(g_ch.direct_max_w * 180.0f / (float)M_PI));
            } else if (prop == 0x36) {
                out_data[0] = g_ch.direct_invert;
                *out_len = 1;
                return STATUS_OK;
            } else if (prop == 0x37) {
                out_data[0] = g_ch.direct_gain;
                *out_len = 1;
                return STATUS_OK;
            } else {
                return STATUS_NOT_FOUND;
            }
            *out_len = 2;
            return STATUS_OK;
        }
        default:
            return STATUS_NOT_FOUND;
        }

    /* ─────────────────────────── SET ─────────────────────────── */
    case OP_SET:
        switch (prop) {
        case 0x10: { /* GEOMETRY: u16×3+u16+u16+u16 */
            if (in_len < 10) return STATUS_RANGE_ERR;
            g_ch.track        = (float)(in_data[0] | (in_data[1] << 8)) / 10.0f;
            g_ch.wheel_base   = (float)(in_data[2] | (in_data[3] << 8)) / 10.0f;
            g_ch.wheel_radius = (float)(in_data[4] | (in_data[5] << 8)) / 10.0f;
            g_ch.encoder_ppr  = (int32_t)(in_data[6] | (in_data[7] << 8));
            g_ch.roller_adj   = (float)(in_data[8] | (in_data[9] << 8)) / 1000.0f;

            if (g_ch.track <= 0 || g_ch.wheel_base <= 0 ||
                g_ch.wheel_radius <= 0 || g_ch.encoder_ppr <= 0) {
                g_ch.sub_code = CH_ERR_GEOMETRY;
                g_ch.state = CH_ERROR;
                return STATUS_RANGE_ERR;
            }

            g_ch.tan_r = tanf((float)M_PI / 4.0f * g_ch.roller_adj);
            g_ch.wc = (g_ch.track / 2.0f) * g_ch.tan_r + (g_ch.wheel_base / 2.0f);
            g_ch.enc_to_dist = (2.0f * (float)M_PI * g_ch.wheel_radius)
                             / (float)g_ch.encoder_ppr;
            g_ch.sub_code = CH_ERR_NONE;
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x20: /* PID 参数 */
        case 0x21:
        case 0x22:
        case 0x23:
        case 0x24:
        case 0x25:
        case 0x26:
        case 0x27:
        case 0x28:
        case 0x29:
        case 0x30:
        case 0x32:
        case 0x33:
        case 0x34:
        case 0x35:
        case 0x36:
        case 0x37:
        {
            if (in_len < 2) return STATUS_RANGE_ERR;
            uint16_t v = (uint16_t)(in_data[0] | (in_data[1] << 8));
            switch (prop) {
            case 0x20: g_ch.kp_rho   = v / 1000.0f; break;
            case 0x21: g_ch.kp_alpha = v / 1000.0f; break;
            case 0x22: g_ch.kp_beta  = v / 1000.0f; break;
            case 0x23: g_ch.ki_rho   = v / 1000.0f; break;
            case 0x24: g_ch.ki_alpha = v / 1000.0f; break;
            case 0x25: g_ch.ki_beta  = v / 1000.0f; break;
            case 0x26: g_ch.pos_tol  = v / 10.0f;   break;
            case 0x27: g_ch.ang_tol  = v * (float)M_PI / 180.0f / 10.0f; break;
            case 0x28: g_ch.max_v    = (float)v;    break;
            case 0x29: g_ch.max_w    = v * (float)M_PI / 180.0f; break;
            case 0x30: g_ch.timeout_ms = v;         break;
            case 0x32: g_ch.direct_mode = (uint8_t)v; break;
            case 0x33: g_ch.direct_deadzone = (uint8_t)v; break;
            case 0x34: g_ch.direct_max_v = (float)v; break;
            case 0x35: g_ch.direct_max_w = v * (float)M_PI / 180.0f; break;
            case 0x36: g_ch.direct_invert = (uint8_t)v; break;
            case 0x37: g_ch.direct_gain = (uint8_t)v; break;
            }
            *out_len = 0;
            return STATUS_OK;
        }
        default:
            return STATUS_READ_ONLY;
        }

    /* ─────────────────────────── CALL ─────────────────────────── */
    case OP_CALL:
        switch (prop) {
        case 0x80: { /* GOTO_POSE: i32×3 + u8 max_speed */
            if (in_len < 13) return STATUS_RANGE_ERR;
            g_ch.target_x = (float)rd_i32(in_data) / 100.0f;
            g_ch.target_y = (float)rd_i32(in_data + 4) / 100.0f;
            g_ch.target_theta = (float)rd_i32(in_data + 8) / 1000.0f;
            uint8_t spd = in_data[12];
            if (spd >= 5 && spd <= 100) g_ch.max_speed_cmd = spd;

            g_ch.i_rho = g_ch.i_alpha = g_ch.i_beta = 0.0f;
            g_ch.prev_rho = g_ch.prev_alpha = g_ch.prev_beta = 0.0f;
            g_ch.move_start_ms = (uint32_t)seconds() * 1000;
            g_ch.state = CH_RUNNING;
            g_ch.mode = CH_MODE_GOTO;
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x81: /* ABORT */
            g_ch.mode = CH_MODE_OFF;
            g_ch.state = CH_ABORTED;
            set_motor(1, 0);
            set_motor(2, 0);
            set_motor(3, 0);
            set_motor(4, 0);
            *out_len = 0;
            return STATUS_OK;
        case 0x82: { /* SET_TWIST: i16×3 (vx*100, vy*100, ω*1000) */
            if (in_len < 6) return STATUS_RANGE_ERR;
            g_ch.target_vx = (float)(int16_t)(in_data[0] | (in_data[1] << 8)) / 100.0f;
            g_ch.target_vy = (float)(int16_t)(in_data[2] | (in_data[3] << 8)) / 100.0f;
            g_ch.target_w  = (float)(int16_t)(in_data[4] | (in_data[5] << 8)) / 1000.0f;
            g_ch.state = CH_RUNNING;
            g_ch.mode = CH_MODE_TWIST;
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x87: { /* SET_DIRECT: [u8 enable] 固件直读摇杆 */
            if (in_len < 1) return STATUS_RANGE_ERR;
            if (in_data[0]) {
                g_ch.state = CH_RUNNING;
                g_ch.mode = CH_MODE_DIRECT;
            } else {
                g_ch.mode = CH_MODE_OFF;
                g_ch.state = CH_IDLE;
                set_motor(1, 0);
                set_motor(2, 0);
                set_motor(3, 0);
                set_motor(4, 0);
            }
            *out_len = 0;
            return STATUS_OK;
        }
        case 0x83: /* RESET_ODOM */
            g_ch.x = 0.0f;
            g_ch.y = 0.0f;
            g_ch.theta = 0.0f;
            g_ch.cos_t = 1.0f;
            g_ch.sin_t = 0.0f;
            g_ch.has_baseline = 0;   /* 下次控制环重设编码器基准 */
            *out_len = 0;
            return STATUS_OK;
        case 0x84: /* EMERGENCY_STOP */
            g_ch.mode = CH_MODE_OFF;
            g_ch.state = CH_EMERGENCY;
            set_motor(1, 0);
            set_motor(2, 0);
            set_motor(3, 0);
            set_motor(4, 0);
            *out_len = 0;
            return STATUS_OK;
        case 0x85: /* CLEAR_ERROR */
            g_ch.state = CH_IDLE;
            g_ch.sub_code = CH_ERR_NONE;
            *out_len = 0;
            return STATUS_OK;
        case 0x86: /* RESET_STATS */
            g_ch.distance_cm_x100 = 0;
            g_ch.arrived_count = 0;
            g_ch.start_time_s = (uint32_t)seconds();
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
 * 启动控制环 (由 services.c 调用)
 * ==================================================================== */

void chassis_start(void)
{
    ThreadStart(chassis_control_loop);
}

/**
 * system_service.c — 系统心跳服务完整实现
 *
 * 特性:
 *   - 1Hz 心跳线程, 主动通知
 *   - 看门狗 (PC 失联自动停车)
 *   - 健康监控 (低电压/过压/堆不足)
 *   - LED 心跳指示
 *   - 紧急停车 (一键停所有电机)
 *   - 软复位
 */

#include "system_monitor.h"
#include "whalesbot.h"      /* wait, seconds, getBatt_AVG, off_motor, SetLED, NVIC_SystemReset */
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

/* FreeRTOS 堆查询 */
#include "FreeRTOS.h"
#include "portable.h"

/* ====================================================================
 * UART 输出助手 (走 USB 串口, 不走 LCD)
 * 注意: printf() 在这个 SDK 里映射到 Printf() -> LCD, 不能用!
 * ==================================================================== */

static void log_uart(const char* fmt, ...)
{
    char buf[128];
    va_list args;
    va_start(args, fmt);
    int n = vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    if (n > 0) UartPC_Sendbytes((uint8_t*)buf, n);
}

/* ====================================================================
 * 内部结构
 * ==================================================================== */

struct SystemService {
    /* 标识 */
    char          device_name[16];
    uint32_t      firmware_version;

    /* 心跳 */
    uint8_t       heartbeat_enabled;
    uint32_t      heartbeat_interval_ms;
    HeartbeatCallback heartbeat_callback;
    void*         heartbeat_user_context;

    /* 健康 */
    uint8_t       last_health_flags;
    HealthCallback health_change_callback;
    void*         health_change_user_context;
    HealthCallback low_battery_callback;
    void*         low_battery_user_context;
    HealthCallback critical_battery_callback;
    void*         critical_battery_user_context;

    /* 看门狗 */
    uint8_t       watchdog_enabled;
    uint32_t      watchdog_timeout_ms;
    uint32_t      watchdog_last_feed_ms;
    uint8_t       watchdog_timed_out;   /* 0/1 */

    /* LED 心跳 (已移除, 保留字段避免破坏 .o 兼容) */
    uint8_t       led_indicator_enabled;
    uint8_t       led_state;
    uint8_t       heartbeat_x;
    uint8_t       heartbeat_y;

    /* 状态 */
    SystemStatus  status;
};

/* 单例引用 (后台线程用) */
static SystemService* g_active_service = NULL;

/* ====================================================================
 * 工具
 * ==================================================================== */

static uint32_t now_ms(void) { return (uint32_t)(seconds() * 1000.0f); }

/* ====================================================================
 * 生命周期
 * ==================================================================== */

SystemService* system_service_create(const char* device_name,
                                     uint32_t firmware_version)
{
    SystemService* svc = (SystemService*)malloc(sizeof(SystemService));
    if (!svc) return NULL;
    memset(svc, 0, sizeof(SystemService));

    if (device_name) {
        strncpy(svc->device_name, device_name, sizeof(svc->device_name) - 1);
    }
    svc->firmware_version = firmware_version;
    svc->status.firmware_version = firmware_version;
    strncpy(svc->status.device_name, device_name, sizeof(svc->status.device_name) - 1);

    return svc;
}

void system_service_destroy(SystemService* service)
{
    if (!service) return;
    if (g_active_service == service) g_active_service = NULL;
    free(service);
}

/* ====================================================================
 * 健康标志计算
 * ==================================================================== */

static void refresh_status(SystemService* s)
{
    s->status.uptime_seconds = (uint32_t)seconds();

    /* 电压 */
    int raw_mv = getBatt_AVG();
    if (raw_mv < 0) raw_mv = 0;
    s->status.voltage_millivolts = (uint16_t)raw_mv;

    int v = s->status.voltage_millivolts;

    /* 自动识别 2S/3S, 计算百分比 */
    if (v < SYSTEM_VOLTAGE_2S_MIN_MILLIVOLTS) {
        s->status.battery_percentage = 0;
    } else if (v < SYSTEM_VOLTAGE_2S_MAX_MILLIVOLTS) {
        /* 2S 范围: 6.0V - 8.4V */
        s->status.battery_percentage = (uint8_t)((v - SYSTEM_VOLTAGE_2S_MIN_MILLIVOLTS) * 100
                                                  / (SYSTEM_VOLTAGE_2S_MAX_MILLIVOLTS - SYSTEM_VOLTAGE_2S_MIN_MILLIVOLTS));
    } else if (v < SYSTEM_VOLTAGE_3S_MAX_MILLIVOLTS) {
        /* 3S 范围: 9.0V - 12.6V */
        s->status.battery_percentage = (uint8_t)((v - SYSTEM_VOLTAGE_3S_MIN_MILLIVOLTS) * 100
                                                  / (SYSTEM_VOLTAGE_3S_MAX_MILLIVOLTS - SYSTEM_VOLTAGE_3S_MIN_MILLIVOLTS));
    } else {
        s->status.battery_percentage = 100;
    }

    /* 空闲堆 (FreeRTOS) */
    s->status.free_heap_bytes = (uint32_t)xPortGetFreeHeapSize();

    /* 计算健康标志 */
    uint8_t h = SYSTEM_HEALTH_OK;
    if (v >= SYSTEM_VOLTAGE_2S_MAX_MILLIVOLTS && v < SYSTEM_VOLTAGE_3S_MIN_MILLIVOLTS) {
        /* 2S/3S 之间的不可能电压 - 传感器异常 */
        h |= SYSTEM_HEALTH_OVER_VOLTAGE;  /* 复用这个 flag 表示异常 */
    }
    if (v < SYSTEM_VOLTAGE_2S_MIN_MILLIVOLTS) h |= SYSTEM_HEALTH_CRITICAL_BATTERY;
    else if (v < SYSTEM_VOLTAGE_2S_MAX_MILLIVOLTS - 300) h |= SYSTEM_HEALTH_LOW_BATTERY;  /* < 8.1V for 2S */
    if (s->status.free_heap_bytes < SYSTEM_HEAP_LOW_WARNING_BYTES) h |= SYSTEM_HEALTH_LOW_HEAP;
    if (s->watchdog_enabled) h |= SYSTEM_HEALTH_WATCHDOG_FED;
    if (s->watchdog_timed_out) h |= SYSTEM_HEALTH_WATCHDOG_TIMED_OUT;

    s->status.health_flags = h;
}

static void notify_health_change(SystemService* s, uint8_t old_flags)
{
    uint8_t new_flags = s->status.health_flags;

    /* 没变就不通知 */
    if (new_flags == old_flags) return;

    /* 通用健康变更 */
    if (s->health_change_callback) {
        s->health_change_callback(s->health_change_user_context, &s->status, new_flags);
    }

    /* 低电压事件 (上升沿: 刚进入低电压状态) */
    bool was_low    = (old_flags & SYSTEM_HEALTH_LOW_BATTERY)     != 0;
    bool is_low     = (new_flags & SYSTEM_HEALTH_LOW_BATTERY)     != 0;
    bool was_crit   = (old_flags & SYSTEM_HEALTH_CRITICAL_BATTERY)!= 0;
    bool is_crit    = (new_flags & SYSTEM_HEALTH_CRITICAL_BATTERY)!= 0;

    if (!was_low && is_low && s->low_battery_callback) {
        s->low_battery_callback(s->low_battery_user_context, &s->status, new_flags);
    }
    if (!was_crit && is_crit && s->critical_battery_callback) {
        s->critical_battery_callback(s->critical_battery_user_context, &s->status, new_flags);
    }
}

/* ====================================================================
 * 心跳线程
 * ==================================================================== */

static void heartbeat_thread(void* arg)
{
    (void)arg;
    uint32_t last_tick = 0;
    uint32_t led_off_tick = 0;

    while (1) {
        if (!g_active_service) { wait(0.1); continue; }
        SystemService* s = g_active_service;
        uint32_t now = now_ms();

        /* 每 10ms 跑一次, 但只按 interval 触发主回调 */
        if (s->heartbeat_enabled && (now - last_tick) >= s->heartbeat_interval_ms) {
            last_tick = now;

            uint8_t old_health = s->status.health_flags;
            refresh_status(s);
            notify_health_change(s, old_health);

            /* 心跳回调 */
            if (s->heartbeat_callback) {
                s->heartbeat_callback(s->heartbeat_user_context, &s->status);
            }
        }

        /* (心跳指示 +/x 切换已被 user_main 里的 show() 替代, 移除) */

        /* 看门狗检查 */
        if (s->watchdog_enabled && !s->watchdog_timed_out) {
            if ((now - s->watchdog_last_feed_ms) > s->watchdog_timeout_ms) {
                s->watchdog_timed_out = 1;
                s->status.health_flags |= SYSTEM_HEALTH_WATCHDOG_TIMED_OUT;
                log_uart("[watchdog] TIMEOUT! emergency stop!\r\n");
                system_service_emergency_stop_all(s);
            }
        }

        wait(0.01);  /* 10ms 循环 */
    }
}

/* ====================================================================
 * 心跳控制
 * ==================================================================== */

void system_service_start_heartbeat(SystemService* service,
                                    uint32_t interval_milliseconds,
                                    HeartbeatCallback callback,
                                    void* user_context)
{
    if (!service) return;
    service->heartbeat_interval_ms = interval_milliseconds;
    service->heartbeat_callback = callback;
    service->heartbeat_user_context = user_context;
    service->heartbeat_enabled = 1;

    if (g_active_service == NULL) {
        g_active_service = service;
        /* 启动 LED 端口 (不指定硬件, 默认) */
        InitLED(602);
        ThreadStart(heartbeat_thread);
    }
}

void system_service_stop_heartbeat(SystemService* service)
{
    if (!service) return;
    service->heartbeat_enabled = 0;
}

/* ====================================================================
 * 健康事件订阅
 * ==================================================================== */

void system_service_on_health_change(SystemService* service,
                                     HealthCallback callback,
                                     void* user_context)
{
    if (!service) return;
    service->health_change_callback = callback;
    service->health_change_user_context = user_context;
}

void system_service_on_low_battery(SystemService* service,
                                   HealthCallback callback,
                                   void* user_context)
{
    if (!service) return;
    service->low_battery_callback = callback;
    service->low_battery_user_context = user_context;
}

void system_service_on_critical_battery(SystemService* service,
                                        HealthCallback callback,
                                        void* user_context)
{
    if (!service) return;
    service->critical_battery_callback = callback;
    service->critical_battery_user_context = user_context;
}

/* ====================================================================
 * 看门狗
 * ==================================================================== */

void system_service_enable_watchdog(SystemService* service,
                                    uint32_t timeout_milliseconds)
{
    if (!service) return;
    service->watchdog_enabled = 1;
    service->watchdog_timeout_ms = timeout_milliseconds;
    service->watchdog_last_feed_ms = now_ms();
    service->watchdog_timed_out = 0;
    log_uart("[watchdog] enabled, timeout=%u ms\r\n", timeout_milliseconds);
}

void system_service_disable_watchdog(SystemService* service)
{
    if (!service) return;
    service->watchdog_enabled = 0;
    service->watchdog_timed_out = 0;
}

void system_service_feed_watchdog(SystemService* service)
{
    if (!service) return;
    if (service->watchdog_timed_out) return;  /* 已超时, 不再喂 */
    service->watchdog_last_feed_ms = now_ms();
}

bool system_service_watchdog_is_timed_out(SystemService* service)
{
    return service && service->watchdog_timed_out;
}

/* ====================================================================
 * (之前的心跳指示 +/x 切换功能已被 show() 替代, 移除)
 * ==================================================================== */

/* ====================================================================
 * 状态查询
 * ==================================================================== */

const SystemStatus* system_service_get_status(SystemService* service)
{
    if (!service) return NULL;
    refresh_status(service);
    return &service->status;
}

uint8_t system_service_get_health_flags(SystemService* service)
{
    if (!service) return SYSTEM_HEALTH_OK;
    refresh_status(service);
    return service->status.health_flags;
}

/* ====================================================================
 * 紧急控制
 * ==================================================================== */

void system_service_emergency_stop_all(SystemService* service)
{
    (void)service;
    /* 关掉所有电机 */
    off_motor(MotorAll);
    stop_move();
    log_uart("[system] EMERGENCY STOP executed\r\n");
    /* LED 全红指示 (如果可用) */
    SetLED(2, 1);  /* LED_R = 亮 */
}

void system_service_request_reboot(SystemService* service)
{
    (void)service;
    log_uart("[system] rebooting...\r\n");
    wait(0.05);
    NVIC_SystemReset();
    while (1) { wait(1.0); }
}

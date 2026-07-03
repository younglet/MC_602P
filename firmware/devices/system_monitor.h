/**
 * system_service.h — 系统心跳服务 (完整版)
 *
 * 提供:
 *   - 1Hz 心跳事件 (回调通知)
 *   - 系统状态 (电压/电量/运行时间/空闲堆)
 *   - 看门狗: PC 失联 N 秒后自动安全停止
 *   - 健康监控: 低电压/过压事件回调
 *   - LED 心跳指示 (板载 LED 每秒闪一下)
 *   - 软复位
 *
 * 用法:
 *   static void on_heartbeat(void* ctx, const SystemStatus* st) {
 *       printf("up=%u V=%u\n", st->uptime_seconds, st->voltage_millivolts);
 *   }
 *
 *   static void on_low_battery(void* ctx, const SystemStatus* st) {
 *       printf("LOW BATTERY!\n");
 *   }
 *
 *   SystemService* sys = system_service_create("smart_car", 102);
 *   system_service_start_heartbeat(sys, 1000, on_heartbeat, NULL);
 *   system_service_on_low_battery(sys, on_low_battery, NULL);
 *   system_service_enable_watchdog(sys, 3000);   // 3 秒失联停车
 *   system_service_enable_led_indicator(sys, 1); // LED 心跳
 *
 *   while (1) {
 *       system_service_feed_watchdog(sys);       // 喂狗 (正常情况下 PC 持续喂)
 *       wait(0.1);
 *   }
 */

#ifndef SYSTEM_SERVICE_H
#define SYSTEM_SERVICE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ====================================================================
 * 常量
 * ==================================================================== */

/* 默认电压阈值 (mV) - 适用 2S/3S 锂电池 (自动识别) */
#define SYSTEM_VOLTAGE_2S_MAX_MILLIVOLTS    8400   /* 2S 满电 */
#define SYSTEM_VOLTAGE_2S_MIN_MILLIVOLTS    6000   /* 2S 放空 */
#define SYSTEM_VOLTAGE_3S_MAX_MILLIVOLTS    12600  /* 3S 满电 */
#define SYSTEM_VOLTAGE_3S_MIN_MILLIVOLTS    9000   /* 3S 放空 */

/* 默认堆警戒线 (字节) */
#define SYSTEM_HEAP_LOW_WARNING_BYTES       (4 * 1024)

/* ====================================================================
 * 类型
 * ==================================================================== */

typedef struct SystemService SystemService;

/* 系统状态 */
typedef struct {
    uint32_t firmware_version;          /* 固件版本号 */
    char     device_name[16];           /* 设备名 */
    uint16_t voltage_millivolts;        /* 电池电压 (mV) */
    uint8_t  battery_percentage;        /* 电量 0-100 */
    uint32_t uptime_seconds;            /* 启动后秒数 */
    uint32_t free_heap_bytes;           /* 空闲堆字节数 (FreeRTOS) */
    uint8_t  health_flags;              /* 见 SYSTEM_HEALTH_* */
} SystemStatus;

/* 健康标志 (位掩码) */
#define SYSTEM_HEALTH_OK              0x00
#define SYSTEM_HEALTH_LOW_BATTERY     (1 << 0)   /* 低电压 */
#define SYSTEM_HEALTH_CRITICAL_BATTERY (1 << 1)  /* 极低电压, 应立即停车 */
#define SYSTEM_HEALTH_OVER_VOLTAGE    (1 << 2)   /* 过压 */
#define SYSTEM_HEALTH_LOW_HEAP        (1 << 3)   /* 堆不足 */
#define SYSTEM_HEALTH_WATCHDOG_FED    (1 << 4)   /* 看门狗最近被喂过 */
#define SYSTEM_HEALTH_WATCHDOG_TIMED_OUT (1 << 5)/* 看门狗超时 (已触发停车) */

/* 回调类型 */
typedef void (*HeartbeatCallback)(void* user_context,
                                  const SystemStatus* status);

typedef void (*HealthCallback)(void* user_context,
                               const SystemStatus* status,
                               uint8_t new_health_flags);

/* ====================================================================
 * 生命周期
 * ==================================================================== */

SystemService* system_service_create(const char* device_name,
                                     uint32_t firmware_version);

void system_service_destroy(SystemService* service);

/* ====================================================================
 * 心跳
 * ==================================================================== */

void system_service_start_heartbeat(SystemService* service,
                                    uint32_t interval_milliseconds,
                                    HeartbeatCallback callback,
                                    void* user_context);

void system_service_stop_heartbeat(SystemService* service);

/* ====================================================================
 * 健康事件
 * ==================================================================== */

void system_service_on_health_change(SystemService* service,
                                     HealthCallback callback,
                                     void* user_context);

void system_service_on_low_battery(SystemService* service,
                                   HealthCallback callback,
                                   void* user_context);

void system_service_on_critical_battery(SystemService* service,
                                        HealthCallback callback,
                                        void* user_context);

/* ====================================================================
 * 看门狗
 *
 * 启用后, PC 必须定期调用 system_service_feed_watchdog() 喂狗.
 * 如果超过 timeout_milliseconds 没喂, 自动调用 emergency_stop_all().
 * ==================================================================== */

void system_service_enable_watchdog(SystemService* service,
                                    uint32_t timeout_milliseconds);

void system_service_disable_watchdog(SystemService* service);

void system_service_feed_watchdog(SystemService* service);

bool system_service_watchdog_is_timed_out(SystemService* service);

/* ====================================================================
 * 心跳指示
 *
 * 之前有 +/x 切换的 LCD 指示功能, 已被 show() 替代, 移除.
 * ==================================================================== */

/* ====================================================================
 * 状态查询
 * ==================================================================== */

const SystemStatus* system_service_get_status(SystemService* service);

uint8_t system_service_get_health_flags(SystemService* service);

/* ====================================================================
 * 紧急控制
 * ==================================================================== */

void system_service_emergency_stop_all(SystemService* service);

void system_service_request_reboot(SystemService* service);

#ifdef __cplusplus
}
#endif

#endif /* SYSTEM_SERVICE_H */

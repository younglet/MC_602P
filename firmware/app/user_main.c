/**
 * user_main.c — 协议引擎 + 心跳 + LCD (心跳不写串口)
 *
 * 之前卡死的原因: heartbeat callback 调 UartPC_Sendbytes() 写串口,
 * 跟协议线程的响应帧竞争同一个 UART TX buffer, 导致协议帧被截断,
 * PC 端收到残帧/CRC 错, 永远等不到自己发的请求的响应.
 *
 * 修法: 心跳 callback 只更新 g_heartbeat_counter, 串口输出靠 LCD 显示.
 * 状态/电压/版本/启动时间等, PC 端通过 bot.system.* 主动查.
 *
 * PING 慢帧 (1ms/byte) → NVIC_SystemReset → BootLoader
 */

#include "whalesbot.h"
#include "system_monitor.h"
#include "services.h"
#include <stdio.h>
#include <string.h>

extern uint8_t get_ping_status(void);

static SystemService* g_sys = NULL;
static volatile uint32_t g_heartbeat_counter = 0;
static volatile uint32_t g_spinner_index     = 0;

/* ====================================================================
 * 心跳 / 健康回调 (关键: 都不写串口, 不与协议帧抢 UART)
 * ==================================================================== */

static void on_heartbeat(void* ctx, const SystemStatus* status)
{
    (void)ctx;
    g_heartbeat_counter++;
    /* 注意: 不调 uart_print / UartPC_Sendbytes, 否则会和协议响应帧抢 UART
     * 状态已存在 g_sys->status, PC 端可主动查 bot.system.uptime / voltage */
}

static void on_health_change(void* ctx, const SystemStatus* status, uint8_t flags)
{
    (void)ctx; (void)status; (void)flags;
    /* 同样不写串口 */
}

static void on_low_battery(void* ctx, const SystemStatus* status, uint8_t flags)
{
    (void)ctx; (void)status; (void)flags;
}

static void on_critical_battery(void* ctx, const SystemStatus* status, uint8_t flags)
{
    (void)ctx; (void)status; (void)flags;
    /* 严重低电压: 停所有电机, 但仍不写串口 */
    system_service_emergency_stop_all((SystemService*)ctx);
}

/* ====================================================================
 * LCD 渲染 (500ms 一次, 也不碰串口)
 * ==================================================================== */

static uint32_t now_ms(void) { return (uint32_t)(seconds() * 1000.0f); }

/* LCD service 占用标志: 上位机写屏后置 1, 心跳不再刷新屏幕 */
extern volatile uint8_t lcd_user_active;
/* LCD 命令由主循环执行 (协议线程只写队列) */
extern int lcd_service_poll(void);

static void render_lcd(void)
{
    if (lcd_user_active) return;   /* 屏幕已交给上位机 */
    if (!g_sys) return;
    const SystemStatus* st = system_service_get_status(g_sys);
    if (!st) return;

    char line_v[24], line_b[24], line_r[24];
    char indicator = (g_spinner_index & 1) ? 'O' : 'o';
    snprintf(line_v, sizeof(line_v), "V:%u.%02uV bat:%u%%",
             st->voltage_millivolts / 1000,
             (st->voltage_millivolts % 1000) / 10,
             st->battery_percentage);
    snprintf(line_b, sizeof(line_b), "beat:%c %u", indicator, g_heartbeat_counter);
    snprintf(line_r, sizeof(line_r), "free:%uB", st->free_heap_bytes);

    show(3, "%s", line_v);
    show(4, "%s", line_b);
    show(5, "%s", line_r);
    LCD_Ram2LCD();
}

/* ====================================================================
 * 入口
 * ==================================================================== */

void user_main(void)
{
    /* 1. 协议引擎 */
    rx_process_start();

    /* 2. LCD 头部 */
    LCD_ClearBuffer();
    show(1, "MC602P FW v1.0");
    show(2, "------------------");
    show(3, "V:0.00V bat:0%");
    show(4, "beat:o 0");
    show(5, "free:0B");
    LCD_Ram2LCD();

    /* 3. 心跳 (1Hz) — 注意: 回调里不写串口 */
    g_sys = system_service_create("smart_car", 102);
    if (g_sys) {
        system_service_start_heartbeat(g_sys, 1000, on_heartbeat, NULL);
        system_service_on_health_change(g_sys, on_health_change, NULL);
        system_service_on_low_battery(g_sys, on_low_battery, NULL);
        system_service_on_critical_battery(g_sys, on_critical_battery, g_sys);
    }

    /* 4. 主循环: PING 检查 + LCD 刷新 */
    uint32_t last_lcd = 0;
    while (1) {
        if (get_ping_status()) {
            /* 慢 PING → 自动复位到 BootLoader, 方便 pydownload.py 烧录 */
            wait(0.005);
            NVIC_SystemReset();
            while (1) { wait(1.0); }
        }

        uint32_t now = now_ms();
        if (lcd_service_poll()) {
            last_lcd = now;   /* 用户命令刚刷屏, 跳过本轮心跳渲染 */
        } else if (now - last_lcd >= 500) {
            last_lcd = now;
            g_spinner_index++;
            render_lcd();
        }
        wait(0.05);
    }
}

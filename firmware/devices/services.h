/**
 * services.h — Service 注册入口 (Motor + System)
 */

#ifndef __SERVICES_H__
#define __SERVICES_H__

#include "whalesbot.h"
#include "dispatcher.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 初始化协议引擎并注册所有 Service。
 * 由 main 在硬件初始化后调用。
 */
void rx_process_start(void);

/**
 * 电机目标写入 (任意线程可调)。
 *
 * 架构: 所有业务线程 (MotorService / Chassis) 只写共享目标表,
 * 唯一调 SDK set_motor 的线程是 pid_control_loop (200Hz)。
 * 遵守"一个资源 = 一个写线程"原则, 避免多线程抢 set_motor。
 *
 * @param port  1~MOTOR_MAX
 * @param speed -100~100 (自动限幅)
 */
void motor_apply(int port, int speed);

#ifdef __cplusplus
}
#endif

#endif /* __SERVICES_H__ */

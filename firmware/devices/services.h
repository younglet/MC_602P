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

#ifdef __cplusplus
}
#endif

#endif /* __SERVICES_H__ */

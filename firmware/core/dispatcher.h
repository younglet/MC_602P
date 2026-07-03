/**
 * dispatcher.h — 协议引擎公共 API (COBS + CRC8 + Service/Property 路由)
 *
 * 取代旧 77 68 协议，使用 vision.md §7 的分层架构：
 *   Transport: COBS 帧定界 + CRC-8
 *   Protocol:  DISCOVER / GET / SET / NOTIFY / CALL / ERROR
 *   Service:   服务注册与分发
 */

#ifndef __PROTOCOL_WB_H__
#define __PROTOCOL_WB_H__

#include <stdint.h>
#include "whalesbot.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ====================================================================
 * 操作码 (Protocol Layer)
 * ==================================================================== */

#define OP_DISCOVER  0x00
#define OP_GET       0x01
#define OP_SET       0x02
#define OP_NOTIFY    0x03
#define OP_CALL      0x04
#define OP_ERROR     0x7F

/* ====================================================================
 * 状态码
 * ==================================================================== */

#define STATUS_OK         0x00
#define STATUS_NOT_FOUND  0x01
#define STATUS_READ_ONLY  0x02
#define STATUS_RANGE_ERR  0x03
#define STATUS_TIMEOUT    0x04
#define STATUS_HW_ERR     0x05

/* ====================================================================
 * 帧常量
 * ==================================================================== */

#define FRAME_DELIMITER  0x00
#define RX_BUF_SIZE      256
#define TX_BUF_SIZE      256
#define MAX_PAYLOAD      254

/* ====================================================================
 * Service 注册
 * ==================================================================== */

#define MAX_SERVICES  32

/**
 * Service 处理函数类型。
 * @param op         操作码 (GET/SET/CALL)
 * @param inst       实例编号（如端口号 1-4）
 * @param prop       属性/命令 ID
 * @param in_data    输入数据（SET/CALL 的值）
 * @param in_len     输入数据长度
 * @param out_data   输出缓冲区（GET 的返回值 / CALL 的返回值）
 * @param out_len    输出数据长度（由 handler 填写）
 * @return           状态码 (STATUS_OK 等)
 */
typedef uint8_t (*ProtoHandler)(uint8_t op, uint8_t inst, uint8_t prop,
                                const uint8_t *in_data, uint8_t in_len,
                                uint8_t *out_data, uint8_t *out_len);

/**
 * 注册一个 Service。
 * @param svc_id   Service ID (如 0x01=Motor, 0xFE=System)
 * @param name     服务名称（用于 DISCOVER，可为 NULL）
 * @param handler  处理函数
 */
void proto_service_register(uint8_t svc_id, const char *name,
                            ProtoHandler handler);

/* ====================================================================
 * 协议引擎生命周期
 * ==================================================================== */

typedef void (*TxFunc)(uint8_t *data, int len);
typedef void (*RxFunc)(int byte);

/**
 * 初始化协议引擎。
 * @param TxHandle  串口发送函数 (UartPC_Sendbytes)
 * @return          接收回调函数 (用于 setUartPC_RxHandle)
 */
RxFunc protocol_config(TxFunc TxHandle);

/* ====================================================================
 * NOTIFY 推送（MCU 主动上报）
 * ==================================================================== */

/**
 * 向主机推送一条 NOTIFY。
 * @param svc    Service ID
 * @param inst   实例编号
 * @param prop   属性 ID
 * @param data   数据
 * @param len    数据长度
 */
void proto_notify(uint8_t svc, uint8_t inst, uint8_t prop,
                  const uint8_t *data, uint8_t len);

/* ====================================================================
 * 兼容旧 API（过渡期）
 * ==================================================================== */

uint8_t get_ping_status(void);

#ifdef __cplusplus
}
#endif

#endif /* __PROTOCOL_WB_H__ */

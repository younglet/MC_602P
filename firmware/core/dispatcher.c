/**
 * dispatcher.c — 协议引擎核心 (frame_send + process_payload + rx_handle)
 *
 * Transport: COBS 帧定界 + CRC-8
 * Protocol:  DISCOVER / GET / SET / NOTIFY / CALL / ERROR
 * Service:   服务注册表 + 分发
 *
 * 上位机帧格式:
 *   [COBS(payload)] [0x00] [CRC8]
 *
 * Payload 格式:
 *   请求: [seq:u8] [op:u8] [svc:u8] [inst:u8] [prop:u8] [value...]
 *   响应: [seq:u8] [op:u8] [svc:u8] [inst:u8] [prop:u8] [status:u8] [value...]
 */

#include "dispatcher.h"
#include "cobs.h"
#include "crc8.h"
#include <string.h>

/* ====================================================================
 * Service 注册表
 * ==================================================================== */

typedef struct {
    uint8_t       svc_id;
    const char   *name;       /* DISCOVER 时返回，可为 NULL */
    ProtoHandler  handler;
} ServiceEntry;

static ServiceEntry service_table[MAX_SERVICES];
static uint8_t      service_count = 0;

void proto_service_register(uint8_t svc_id, const char *name,
                            ProtoHandler handler)
{
    if (service_count >= MAX_SERVICES) return;
    service_table[service_count].svc_id  = svc_id;
    service_table[service_count].name    = name;
    service_table[service_count].handler = handler;
    service_count++;
}

/* 查找 service */
static ServiceEntry *find_service(uint8_t svc_id)
{
    for (uint8_t i = 0; i < service_count; i++) {
        if (service_table[i].svc_id == svc_id) {
            return &service_table[i];
        }
    }
    return NULL;
}

/* ====================================================================
 * RX/TX 缓冲区
 * ==================================================================== */

/* ====================================================================
 * RX/TX 缓冲区
 * ==================================================================== */

/* 环形缓冲: ISR 只入环 (极简 ~10 指令), 状态机/解码全在 rx_handle 线程。
 * 1Mbps = 125 字节/ms, rx_handle 每 1ms poll, 256 深度足够。
 * 单生产者(ISR)单消费者(rx_handle), 无锁。
 * 历史: 旧实现 ISR 里做 PING 匹配+帧收集, 处理耗时偶发 >1µs/字节
 * (STM32F103 USART 无 FIFO) → 硬件 ORE 溢出丢字节 → 协议偶发超时。 */
#define RX_RING_SIZE 512
static volatile uint8_t  rx_ring[RX_RING_SIZE];
static volatile uint16_t rx_ring_head = 0;
static volatile uint16_t rx_ring_tail = 0;
static volatile uint8_t  rx_ring_overflow = 0;  /* 溢出兜底标志 */

/* RX 统计 (诊断用, System 0x0A GET) */
volatile uint32_t g_rx_stats_valid = 0;    /* 有效帧 */
volatile uint32_t g_rx_stats_crc = 0;      /* CRC 错帧 */
volatile uint32_t g_rx_stats_overflow = 0; /* ring 溢出 */

static uint8_t rx_buf[RX_BUF_SIZE];   /* 当前帧 (仅 rx_handle 线程访问) */
static uint8_t payload_buf[MAX_PAYLOAD]; /* 解码后的 payload */
static uint8_t tx_payload[MAX_PAYLOAD]; /* 响应 payload */

static void (*uart_send)(uint8_t *data, int length);

/* ====================================================================
 * 帧构建
 * ==================================================================== */

/** 打包并发送 payload。 */
static void frame_send(const uint8_t *payload, uint8_t len)
{
    /* COBS 编码 */
    static uint8_t cobs_buf[MAX_PAYLOAD + 2];  /* 静态分配，避免栈溢出 */
    size_t cobs_len = cobs_encode(payload, len, cobs_buf);

    /* CRC8 在编码前计算（覆盖 payload） */
    uint8_t csum = crc8_compute(payload, len);

    /* 组装: COBS + [0x00] + CRC8 */
    cobs_buf[cobs_len] = FRAME_DELIMITER;
    cobs_buf[cobs_len + 1] = csum;

    uart_send(cobs_buf, (int)(cobs_len + 2));
}

/* ====================================================================
 * 协议处理
 * ==================================================================== */

/** 处理一条已解码的 payload（在 rx_handle 线程中调用）。 */
static void process_payload(const uint8_t *payload, uint8_t len)
{
    /* 最小长度: seq + op + svc + inst + prop = 5 */
    if (len < 5) return;

    uint8_t seq  = payload[0];
    uint8_t op   = payload[1];
    uint8_t svc  = payload[2];
    uint8_t inst = payload[3];
    uint8_t prop = payload[4];

    const uint8_t *value     = payload + 5;
    uint8_t        value_len = len - 5;

    /* 构建响应的 payload 缓冲区 */
    uint8_t resp_idx = 0;
    uint8_t resp_status = STATUS_OK;

    /* 响应头部: [seq, op, svc, inst, prop] — 先占位，最后填 status */
    tx_payload[0] = seq;
    tx_payload[1] = op;
    tx_payload[2] = svc;
    tx_payload[3] = inst;
    tx_payload[4] = prop;
    resp_idx = 5;

    /* 预留 status 位置 */
    uint8_t status_pos = resp_idx;
    resp_idx++;  /* 先占位，后面填入 */

    uint8_t *resp_data = tx_payload + resp_idx;
    uint8_t  resp_len  = 0;

    /* ----------------------------------------------------------------
     * DISCOVER: 返回所有已注册 service 的 ID
     * ---------------------------------------------------------------- */
    if (op == OP_DISCOVER) {
        for (uint8_t i = 0; i < service_count; i++) {
            if (resp_idx + 1 > MAX_PAYLOAD) break;
            tx_payload[resp_idx++] = service_table[i].svc_id;
        }
        resp_status = STATUS_OK;
    }

    /* ----------------------------------------------------------------
     * GET / SET / CALL: 查找 service 并调用 handler
     * ---------------------------------------------------------------- */
    else if (op == OP_GET || op == OP_SET || op == OP_CALL) {
        ServiceEntry *svc_entry = find_service(svc);
        if (svc_entry == NULL || svc_entry->handler == NULL) {
            resp_status = STATUS_NOT_FOUND;
        } else {
            resp_status = svc_entry->handler(
                op, inst, prop,
                value, value_len,
                resp_data, &resp_len
            );
            resp_idx += resp_len;
        }
    }

    /* 不支持的操作码 */
    else {
        resp_status = STATUS_NOT_FOUND;
    }

    /* 填入 status */
    tx_payload[status_pos] = resp_status;

    /* 发送响应 */
    frame_send(tx_payload, resp_idx);
}

/* ====================================================================
 * 接收状态机 (rx_handle 线程内, 非中断)
 * ==================================================================== */

static uint8_t flag_handle = 0;
static uint16_t rx_idx = 0;
static float time_last = 0;
static uint8_t ping_flag = 0;
static uint8_t ping_idx = 0;
static uint8_t ping_status = 0;

/* PING 数据（bootloader 握手，保留兼容）
 * 注意：只有收到 0x55 头部后才进入 PING 检测模式，
 * 避免 COBS 帧中的 0x00 被误判为 PING 数据的一部分。 */
#define PING_LENGTH 8
static const uint8_t PING_DATA[PING_LENGTH] = {
    0x55, 0xaa, 0x00, 0x01, 0x08, 0x00, 0x00, 0xf7
};

uint8_t get_ping_status(void)
{
    return ping_status;
}

/* 逐字节接收状态机 (原 UART ISR 逻辑, 移入线程避免 1µs 硬实时) */
static void rx_feed_byte(uint8_t byte)
{
    /* 100ms 超时自动复位接收状态 */
    if (seconds() - time_last > 0.1) {
        rx_idx = 0;
        ping_flag = 0;
        ping_idx = 0;
    }
    time_last = seconds();

    /* PING 检测：收到 0x55 或已在 PING 序列中才继续匹配
     * ⚠️ 匹配过程中的字节不能 return 吞掉 —— 数据帧里的 0x55
     * (如 SET 0x29 的 value=85=0x55) 必须照常进入数据接收,
     * 否则帧缺字节 → CRC 错 → 请求被丢弃 (表现为随机超时)。 */
    if (ping_flag || byte == 0x55) {
        if (byte == PING_DATA[ping_idx]) {
            ping_flag = 1;
            ping_idx++;
            if (ping_idx == PING_LENGTH) {
                ping_status = 1;
                ping_flag = 0;
                ping_idx = 0;
                /* 复位由主循环消费 ping_status 触发 */
            }
        } else {
            /* 不匹配，退出 PING 模式 */
            ping_flag = 0;
            ping_idx = 0;
        }
    }

    /* 数据接收 (PING 序列字节也照常进入, 形成无效帧被 CRC 丢弃) */
    if (rx_idx < RX_BUF_SIZE) {
        rx_buf[rx_idx++] = byte;

        /* 检测到帧分隔符 0x00 */
        if (byte == FRAME_DELIMITER) {
            flag_handle = 1;
            /* 收到正常 COBS 帧后清零 PING 状态，防止误触发复位。
             * ⚠️ 但 PING 帧第 3/6/7 字节本身就是 0x00 (PING_DATA[2/5/6]),
             * 此时 ping_idx 已 ≥3, 若也清零则 PING 永远匹配不完。
             * 规则: ping_idx < 3 (仅匹配到 0x55 0xaa) 才清零 ——
             * COBS 编码区不含 0x00, 合法数据帧的 0x00 必然在首 3 字节内。 */
            if (ping_idx < 3) {
                ping_flag = 0;
                ping_idx = 0;
            }
        }
    } else {
        /* 缓冲区溢出，重置 */
        rx_idx = 0;
    }
}

/* ====================================================================
 * 接收线程
 * ==================================================================== */

static void rx_handle(void)
{
    while (1) {
        /* 消费环形缓冲 (ISR 只入环), 逐帧立即处理:
         * 分隔符一到就处理该帧, 否则多帧累积时后帧被 rx_idx 清零截断
         * (历史 bug: 一帧残头 + CRC 错, 实测每轮连发丢 1 帧)。
         * process_payload 耗时期间 ring 继续收 (512 深度 ≈ 4ms 缓冲)。 */
        while (rx_ring_head != rx_ring_tail) {
            uint8_t byte = rx_ring[rx_ring_tail];
            rx_ring_tail = (uint16_t)((rx_ring_tail + 1) & (RX_RING_SIZE - 1));
            rx_feed_byte(byte);

            if (flag_handle == 1) {
                size_t payload_len = 0;
                int valid = 0;

                /* 查找分隔符 0x00 */
                int delim_pos = -1;
                for (uint16_t i = 0; i < rx_idx; i++) {
                    if (rx_buf[i] == FRAME_DELIMITER) {
                        delim_pos = (int)i;
                        break;
                    }
                }

                /* CRC 字节 (分隔符后 1 字节) 未到齐 → 继续消费 ring,
                 * 分隔符刚处理完时 CRC 通常还在 ring 里。 */
                if (delim_pos < 0 || delim_pos + 1 >= (int)rx_idx) {
                    continue;
                }

                /* COBS 解码 (写入 payload_buf) */
                payload_len = cobs_decode(rx_buf, (size_t)delim_pos,
                                          payload_buf);
                if (payload_len > 0 || delim_pos <= 1) {
                    /* CRC8 校验 */
                    uint8_t expected_crc = rx_buf[delim_pos + 1];
                    uint8_t actual_crc   = crc8_compute(payload_buf, payload_len);
                    if (expected_crc == actual_crc) {
                        valid = 1;
                    }
                }

                /* 清状态, 后续字节属于新帧 */
                flag_handle = 0;
                rx_idx = 0;

                if (valid) {
                    g_rx_stats_valid++;
                } else if (delim_pos >= 0) {
                    g_rx_stats_crc++;   /* 有帧结构但校验失败 */
                }

                if (valid) {
                    process_payload(payload_buf, (uint8_t)payload_len);
                }
            }
        }
        wait(0.001);
    }
}

/* ====================================================================
 * 串口中断回调 (极简: 只入环形缓冲)
 * ==================================================================== */

static void Uart_RevCallback(int revdata)
{
    uint16_t next = (uint16_t)((rx_ring_head + 1) & (RX_RING_SIZE - 1));
    if (next == rx_ring_tail) {
        rx_ring_overflow = 1;   /* 环形缓冲满: 丢字节 (正常不应发生) */
        g_rx_stats_overflow++;
        return;
    }
    rx_ring[rx_ring_head] = (uint8_t)revdata;
    rx_ring_head = next;
}

/* ====================================================================
 * 协议初始化
 * ==================================================================== */

RxFunc protocol_config(TxFunc TxHandle)
{
    uart_send = TxHandle;

    /* 启动接收线程 */
    ThreadStart(rx_handle);

    return Uart_RevCallback;
}

/* ====================================================================
 * NOTIFY 推送
 * ==================================================================== */

void proto_notify(uint8_t svc, uint8_t inst, uint8_t prop,
                  const uint8_t *data, uint8_t len)
{
    /* 构建 NOTIFY payload:
     * [seq=0] [NOTIFY] [svc] [inst] [prop] [status=OK] [data...] */
    uint8_t buf[MAX_PAYLOAD];
    uint8_t idx = 0;

    buf[idx++] = 0;          /* seq=0 表示主动推送 */
    buf[idx++] = OP_NOTIFY;
    buf[idx++] = svc;
    buf[idx++] = inst;
    buf[idx++] = prop;
    buf[idx++] = STATUS_OK;

    if (data != NULL && len > 0 && idx + len <= MAX_PAYLOAD) {
        memcpy(buf + idx, data, len);
        idx += len;
    }

    frame_send(buf, idx);
}

/**
 * cobs.h — Consistent Overhead Byte Stuffing (COBS)
 *
 * 保证编码后的数据不含 0x00，从而用 0x00 作帧分隔符。
 * 编码最大开销 +1 字节（254 字节数据 → 255 字节编码）。
 */

#ifndef EXTERNLIB_COBS_H_
#define EXTERNLIB_COBS_H_

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * COBS 编码。
 * @param src   原始数据
 * @param len   原始数据长度
 * @param dst   输出缓冲区（需至少 len + len/254 + 2 字节）
 * @return      编码后长度；0 表示输入为空
 */
size_t cobs_encode(const uint8_t *src, size_t len, uint8_t *dst);

/**
 * COBS 解码。
 * @param src   COBS 编码数据（不含尾 0x00 分隔符）
 * @param len   编码数据长度
 * @param dst   输出缓冲区（需至少 len 字节）
 * @return      解码后长度；0 表示输入为空
 */
size_t cobs_decode(const uint8_t *src, size_t len, uint8_t *dst);

#ifdef __cplusplus
}
#endif

#endif /* EXTERNLIB_COBS_H_ */

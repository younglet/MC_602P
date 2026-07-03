/**
 * crc8.h — CRC-8-Dallas/Maxim (poly=0x31, init=0x00)
 */

#ifndef EXTERNLIB_CRC8_H_
#define EXTERNLIB_CRC8_H_

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 计算 CRC-8-Dallas/Maxim。
 * @param data  输入数据
 * @param len   数据长度
 * @return      8-bit CRC 值
 */
uint8_t crc8_compute(const uint8_t *data, size_t len);

#ifdef __cplusplus
}
#endif

#endif /* EXTERNLIB_CRC8_H_ */

/**
 * cobs.c — COBS 编解码实现
 */

#include "cobs.h"

size_t cobs_encode(const uint8_t *src, size_t len, uint8_t *dst)
{
    if (len == 0 || src == NULL) {
        dst[0] = 0x01;
        return 1;
    }

    size_t code_idx = 0;
    uint8_t code = 1;
    size_t write_idx = 1;

    for (size_t i = 0; i < len; i++) {
        if (src[i] == 0x00) {
            dst[code_idx] = code;
            code_idx = write_idx;
            code = 1;
            write_idx++;
        } else {
            dst[write_idx++] = src[i];
            code++;
            if (code == 0xFF) {
                dst[code_idx] = code;
                code_idx = write_idx;
                code = 1;
                write_idx++;
            }
        }
    }

    dst[code_idx] = code;
    return write_idx;
}

size_t cobs_decode(const uint8_t *src, size_t len, uint8_t *dst)
{
    if (len == 0 || src == NULL) {
        return 0;
    }

    size_t read_idx = 0;
    size_t write_idx = 0;

    while (read_idx < len) {
        uint8_t code = src[read_idx];
        if (code == 0x00) {
            return 0;  /* 编码数据中不应出现 0x00 */
        }

        read_idx++;
        for (uint8_t i = 0; i < code - 1; i++) {
            if (read_idx >= len) break;
            dst[write_idx++] = src[read_idx++];
        }

        /* 若 code < 0xFF 且还有更多数据，追加 0x00 */
        if (code < 0xFF && read_idx < len) {
            dst[write_idx++] = 0x00;
        }
    }

    return write_idx;
}

/*
 * bt_run.h
 *
 *  Created on: 2023年5月4日
 *      Author: Administrator
 *      说明：蓝牙解释在线运行功能
 */

#ifndef CONTROL_BTRUN_H_
#define CONTROL_BTRUN_H_

#ifdef CONTROL_BTRUN_H_




//蓝牙解释执行处理流程
void BT_RunProcess(void);

//蓝牙接收协议中，将77 68协议数据复制给此函数，由线程BT_RunProcess实际处理数据
void BtRun_Newdata(uint8_t *newdata);



#endif
#endif
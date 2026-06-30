/*
 * battery.h
 *
 *  Created on: 2023年1月6日
 *      Author: Administrator
 *      说明：电池
 */

#ifndef CONTROL_BATTERY_H_
#define CONTROL_BATTERY_H_

#ifdef CONTROL_BATTERY_H_


//获取电池电压，单位mv
int getBatt(void);

//获取电池电压，单位mv,平滑滤波后的数据
int getBatt_AVG(void);

//获取电池电压百分比
int getBattPercentage(void);


//初始化电池检测功能
void InitBatt(void);

//设置电池自动关机时间
//10min/30min/60min
int SetAutoPowerOff(void);

//获取当前自动关机设置
int getAutoPowerOff(void);

//取消自动关机逻辑
void SetAutoPowerDisable(void);

//2S电池在100%和0%时的电压阈值
#define BATT_2S_ADC_100     8300
#define BATT_2S_ADC_0       7000

//S电池在100%和0%时的电压阈值
#define BATT_3S_ADC_100     12600
#define BATT_3S_ADC_0       10200
#define BATT_3S_ADC_CLOSE   9000

//电池种类是锂离子电池8.4V
#define BATT_LIPO8V4_TYPE    2
#define BATT_LIPO12V6_TYPE   3

//获取电池种类
int getBatt_type(void);

//设置电池种类
int SetBatt_type(void);

//判断电池是否错误
int IsBattError(void);

//电池电压低于此数值，则强制停止电机
#define BATT_ADC_MOTOLOW          (BATT_2S_ADC_0-500)//6300
#define BATT_ADC_MOTOHIGH         (BATT_2S_ADC_0-300)

#endif
#endif


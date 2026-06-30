/*
 * mc602_sensor.c
 *
 *  Created on: 2022年12月22日
 *      Author: Administrator
 *      说明：MC601遗留传感器兼容函数
 */


#include "main.h"

#ifndef CONTROL_MC602_SENSOR_H_
#define CONTROL_MC602_SENSOR_H_
#ifdef  CONTROL_MC602_SENSOR_H_






//摇杆传感器摇杆定义
#define    JOY_X                       1
#define    JOY_Y                       2



//摇杆传感器
//Port端口号：P1~P6,Joystick：1=x轴 ，2=y轴
int jointed_arm(int Port,int Joystick);

//传感器端口连接的4向按钮
int key_button(int Port,int Key);

//红外遥控传感器读取函数
int infrared_receiver(int Port);

//限位开关是否被按下，按下返回true。无动作返回false
int limit_switch(int Port);


//WS2812灯光控制，此代码只能在GCC零等空间正常，非零等空间存在时序问题，无法正常点灯
#ifdef GCC_CODE
//设置WS2182灯条
#define WS2812_MAX 62//灯珠总个数
#define set_rgb_led_module set_rgb_led_strip

//设置WS2182灯条,Port：D1~D7端口,LED灯珠1~9个灯珠
void set_rgb_led_strip(int Port,int LED,int r,int g,int b);
//复位WS2812灯条
void rgb_led_Reset(void);

#endif



#endif
#endif
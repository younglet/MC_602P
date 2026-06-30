/*
 * main.h
 *
 *  Created on: Sep 30, 2022
 *      Author: Administrator
 */
#ifndef MAIN_H_
#define MAIN_H_


/*
2024-06-06: V101 1.修复灯带“全部”点亮功能
				 2.修复D5,D6端口舵机通道不对应的情况
				 3.修复扩展4按钮板key_button判断按钮释放按下不稳定的情况
				 4.修复老版本901舵机接收错位的处理，使得错位舵机也可通信成功
				 5.增加电池电量2S,3S的设置的切换，使得控制器使用3S电池时，可正常显示百分比，通过“关于->Bat:2s/3s X.XV"可手工设置电池种类
				 6.增加开机自动运行程序功能，通过“关于->Autorun"可设置自动运行程序
				 7.开机LOGO图片更换
	2024-11-5    1.修复颜色传感器分量端口总是P1的错误
	2025-03-05   1.修复巡线库地面检测时，不能正确存储识别结果的BUG
				 2.增加P5,P6端口自动识别5灰度，自动切换的功能
				 3.优化黑白检测的界面操作逻辑
				 2025-04-07
				 1.增加大容量版本编译LD文件
				 2.优化电机保护逻辑（保护后，再次启动时，先低速判断是否卡住)，增加反向设置电机解除保护逻辑
				 3.解决步进电机功能启动时，485总线上设置舵机的冲突问题
	2025-05-19 
				 1.修复AI摄像头左掉头等返回结果编译出错的问题
2025-07-16 ver102     1.新增K210全功能固件的对接函数AI_read_value_v2，并保持老固件的兼容
2025-07-30            1.优化步进电机和舵机同时使用的延时和丢包情况
					  2.优化舵机设置角度函数，使得设置角度和速度通过同一包指令发送
					  3.增加点读笔支持
					  4.驱动卡中超过1秒不设置电机功率则停止电机
					  5.修改拍照后无法再次实时显示视频流的情况
					  6.增加K210模块扫码二维码对应函数
*/





//根据用于选择库的编译项和特性
//#define BOOT_CODE         //此代码作为BOOT升级和启动功能
//#define GUI_CODE          //此代码作为界面操作功能
#define GCC_CODE            //此代码作为用户的GCC编译



//此数据放置于Appware_InfoFlash字段，地址：0x0x080x01e4
#define VER				102//100//软件版本号
#define NAME0           'M'
#define NAME1           'C'
#define NAME2           '6'
#define NAME3           '0'
#define NAME4           '2'
#define NAME5           'P'


#ifdef BOOT_CODE
	#define SYSCLK_FREQ_180MHz   180000000//MC602产品，完全使用内部RC,168M主频
#else
	//GUI 和GCC使用168Mhz
	#define SYSCLK_FREQ_180MHz   180000000//MC602产品，完全使用内部RC,168M主频
#endif


//芯片型号，勿删
#define STM32F10X_HD
//系统头文件，勿删
//C语言基本函数
#include "stdint.h"
#include "string.h"
#include "stdio.h"
#include "stdlib.h"
#include "stdarg.h"
#include "stdbool.h"
#include "math.h"
//硬件相关函数,勿删
#include "stm32f10x_lib.h"




//硬件相关功能头文件，通过注释或打开，可选择相应功能是否编译到bin中
//GUI BOOT GCC共用代码
#include "digoutput.h"//DO端口
#include "program_run.h"//程序间跳转功能
#include "bps.h"//系统相关函数，杂项函数
#include "power_key.h"//按钮和电源控制管脚
#include "uart_pc.h"//和PC机通信的USB->串口
#include "internal_flash.h"//内部FLASH读写函数
#include "devicename.h"//获取硬件PCB板上跳线电阻选则的软件和硬件版本
#include "systemtimer.h"//系统定时器，SystemTick操作
//#include "lcd_128x64.h"//128x64黑白液晶
#include "spi_lcd.h"//SPI液晶
#include "lcd.h"//针对不同硬件，提供统一的LCD操作函数
#include "spi_flash.h"//外部flash读写操作
#include "usb_vbus.h"//USB插入检测，功能切换
#include "led.h"//板载LED

//BOOT功能特有代码
#ifdef BOOT_CODE
    #include "boot_updateflash.h"//BOOT更新内部FLASH，如果是用户程序，则关闭此选项
	//#include "beep_simple.h"//IO控制器的简单蜂鸣器，提供下载提示
#else
	//GCC GUI公用代码
	#include "port_AI.h"//模拟端口
	#include "port_motor.h"//电机相关
    #include "uart_pc_debug.h"//GUI或者GCC程序下，PC串口通信
	#include "battery.h"//电池电量检测和保护
	#include "thread.h"//GCC代码有多线程切换功能
	#include "beep_wav.h"//wav格式声音播放
	#include "port_i2c.h"//I2C功能
	#include "port_i2c_sensor.h"//I2C外接传感器操作
	#include "uart_p1.h"//PORT1端口上的串口
	#include "uart_p2.h"//PORT2端口上的串口
	#include "port_uart_5gray.h"//P1,P2上的5灰度传感器操作
	#include "uart_485.h"//485/ttl 舵机总线串口初始化
	#include "uart_bt.h"//蓝牙串口初始化
	#include "port_485servo.h"//485/ttl总线伺服电机操作
	#include "port_btremote.h"//遥控手柄协议解析
	#include "port_i2c_dot8x8.h"//I2C的8X8蓝色点阵操作
	#include "port_AI_sensor.h"//AI端口上对应传感器操作
	#include "port_math.h"//数学相关的接口函数
	#include "port_i2c_spl06.h"//气压传感器相关操作
	#include "port_pwmservo.h"//PWM舵机
	#include "beep_simple.h"//MC602是蜂鸣器发声
	#include "mc602_runapp.h"//MC602运行程序
	#include "mc602_sensor.h"//MC602遗留传感器兼容适配
	#include "mc602_mpu6500.h"//MC602遗留陀螺兼容适配
	#include "uart_pi.h"//PI使用的串口
#endif
#ifdef GUI_CODE//界面特有代码
	#include "gui_main.h"//用户界面操作
	#include "bt_run.h"//蓝牙解释执行相关
	#include "play_page.h"//动作页执行库
	#include "usb485.h"//usb转换为485协议转发功能
#endif
#ifdef GCC_CODE//GCC部分特有代码
	#include "whalesbot.h"//给SCRATCH编程界面使用的头文件
#endif

#endif /* MAIN_H_ */

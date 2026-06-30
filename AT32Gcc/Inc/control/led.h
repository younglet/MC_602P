/*
 * led.h
 *
 *  Created on: 2023年1月4日
 *      Author: Administrator
 * 针对不同硬件，提供统一的LCD操作方式和函数
 */

#ifndef CONTROL_LED_H_
#define CONTROL_LED_H_

#ifdef CONTROL_LED_H_





/*
MC602P硬件配置
LED_G  ->  PD7
LED_R  ->  PA12
LED_B  ->  PA11
*/
#define LED_G_PIN   GPIO_Pin_7
#define LED_G_PORT	GPIOD

#define LED_R_PIN   GPIO_Pin_12
#define LED_R_PORT	GPIOA

#define LED_B_PIN  GPIO_Pin_11
#define LED_B_PORT	GPIOA


#define LED_G  1
#define LED_R  2
#define LED_B  3



//初始化LED端口
void InitLED(int Hardware);

//设置LED状态
void SetLED(int Port,int State);

#endif
#endif
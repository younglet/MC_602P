/*
 * digouput.h
 *
 *  Created on: 2022年12月6日
 *      Author: Administrator
 *      说明：数字输出功能
 */

#ifndef CONTROL_DIGOUPUT_H_
#define CONTROL_DIGOUPUT_H_


//编译使能
#ifdef CONTROL_DIGOUPUT_H_


//端口编号
#define P1      1
#define P2      2
#define P3      3
#define P4      4
#define P5      5
#define P6      6
#define P7      7
#define P8      8
#define P9      9
#define P10     10
#define P11     11
#define P12     12
#define P13     13
#define P14     14
#define P15     15
#define P16     16
#define P17     17
#define P18     18
#define P19     19
#define P20     20

//数字输出端口
/*
MC602管脚配置
水晶头DO端口输出
DIG1  ->  PD5 X
DIG2  ->  PD4 X
DIG3  ->  PC15 X
DIG4  ->  PD10 X
DIG5  ->  PA4  X
DIG6  ->  PB9  X
排针端口输出
DIG7  ->  PE9   T1C1 SERVOPWM1 X
DIG8  ->  PE11  T1C2 SERVOPWM2 X
DIG9  ->  PE13  T1C3 SERVOPWM3 X
DIG10 ->  PE14   T1C4 SERVOPWM4 X
DIG11 ->  PA7   T3C2 SERVOPWM5 X
DIG12 ->  PA6   T3C1 SERVOPWM6 X
DIG13 ->  PB14  T12C1 SERVOPWM7 X
*/
#define DIG1_PIN    GPIO_Pin_5
#define DIG1_PORT	GPIOD

#define DIG2_PIN    GPIO_Pin_4
#define DIG2_PORT	GPIOD

#define DIG3_PIN    GPIO_Pin_15
#define DIG3_PORT	GPIOC

#define DIG4_PIN    GPIO_Pin_10
#define DIG4_PORT	GPIOD

#define DIG5_PIN    GPIO_Pin_4
#define DIG5_PORT	GPIOA

#define DIG6_PIN    GPIO_Pin_9
#define DIG6_PORT	GPIOB

#define DIG7_PIN    GPIO_Pin_9
#define DIG7_PORT	GPIOE

#define DIG8_PIN    GPIO_Pin_11
#define DIG8_PORT	GPIOE

#define DIG9_PIN    GPIO_Pin_13
#define DIG9_PORT	GPIOE

#define DIG10_PIN   GPIO_Pin_14
#define DIG10_PORT	GPIOE

#define DIG11_PIN   GPIO_Pin_7
#define DIG11_PORT	GPIOA

#define DIG12_PIN   GPIO_Pin_6
#define DIG12_PORT	GPIOA

#define DIG13_PIN   GPIO_Pin_14
#define DIG13_PORT	GPIOB


//提供外部函数快速设置GPIO的功能
extern GPIO_TypeDef *PortFast[];
extern uint16_t PinFast[];

#define FastDO_H(Port)   (PortFast[Port]->BSRR = PinFast[Port])
#define FastDO_L(Port)   (PortFast[Port]->BRR = PinFast[Port])


//初始化DO端口
void InitDo(int Hardware);

//设置DO输出
void SetDO(int Port,int State);
//DO端口开关状态定义
#define switch_on   true
#define switch_off  false
//SetDO的2个等效函数
#define set_light SetDO//设置DO口上的灯光，switch_on/switch_off
#define set_magnet SetDO//设置DO口上的电磁铁，switch_on/switch_off



//设置DO输出反转
void ToggleDO(int Port);


//根据位使能，设置DO端口状态
void setDO(int Channel, int State);


#endif /* CONTROL_DIGOUPUT_H_ */
#endif /* CONTROL_DIGOUPUT_H_ */

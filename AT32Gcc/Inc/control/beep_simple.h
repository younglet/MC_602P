/*
 * beep_simple.h
 *
 *  Created on: 2022年12月6日
 *      Author: Administrator
 *      功能说明：IO方式控制器蜂鸣器
 */

#ifndef CONTROL_BEEP_SIMPLE_H_
#define CONTROL_BEEP_SIMPLE_H_


//编译使能
#ifdef CONTROL_BEEP_SIMPLE_H_

/*
DAC OUT ->  PA5
*/
#define BEEP_PIN    GPIO_Pin_5
#define BEEP_PORT	GPIOA

//纯IO方式控制的蜂鸣器，初始化
void InitBeepSimple(void);

//蜂鸣器蜂鸣声指定的时间
#define F_C5  262
#define F_D5  294
#define F_E5  330
#define F_F5  349
#define F_G5  392
#define F_A5  440
#define F_B5  494
#define F_C6  523
//播放时间
#define T_1_64  0.015
#define T_1_32  0.031
#define T_1_16  0.062
#define T_1_8   0.125
#define T_1_4   0.25
#define T_1_2   0.5
#define T_1     1.0

#define f_none    0 
#define f_do      F_C5 
#define f_re      F_D5 
#define f_mi      F_E5 
#define f_fa      F_F5 
#define f_so      F_G5 
#define f_la      F_A5 
#define f_si      F_B5 
#define f_do_h     F_C6 

#define beep_play beep
void beep(int feq,float second);



#define TIM_BEEP		                    TIM9
#define TIM_BEEP_IRQN                       TIM1_BRK_IRQn//TIM9_IRQn
#define TIM_BEEP_IRQPreemptionPrioritn       2
#define TIM_BEEP_IRQSubPriority              2
#define TIM_BEEP_IRQHandler		             TIM1_BRK_IRQHandler

#endif
#endif

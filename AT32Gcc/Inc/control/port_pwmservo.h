/*
 * port_pwmservo.h
 *
 *  Created on: 2023年1月4日
 *      Author: Administrator
 */

#ifndef CONTROL_PORT_PWMSERVO_H_
#define CONTROL_PORT_PWMSERVO_H_

#ifdef CONTROL_PORT_PWMSERVO_H_


//最大的舵机个数
#define MAXSERVOACOUNT      P20

#define W_PWM_PSC_VAL       1200
#define W_PWM_PRD_VAL	    (1500 - 1)
//#define W_PWM_WID_VAL       1000


#define TIM_SERVO_1234                  TIM1
#define TIM_SERVO_1234_REMAP            GPIO_FullRemap_TIM1

#define TIM_SERVO_56                    TIM3

#define TIM_SERVO_7                     TIM12


//PWM舵机电源控制管脚
#define PWR_CTL_PWM_PIN    GPIO_Pin_2
#define PWR_CTL_PWM_PORT   GPIOB  




/*伺服PWM舵机连接到
SERVO_PWM1 PE9 T1C1     P7
SERVO_PWM2 PE11 T1C2    P8
SERVO_PWM3 PE13 T1C3    P9
SERVO_PWM4 PE14 T1C4    P10
SERVO_PWM5 PA7  T3C2    P11
SERVO_PWM6 PA6  T3C1    P12
SERVO_PWM7 PB14 T12C1   P13
*/
#define D1  P7
#define D2  P8
#define D3  P9
#define D4  P10
#define D5  P11
#define D6  P12
#define D7  P13



//设置PWM舵机角度,PORT:P5/P6/P7,Speed:10-100,Angle:0-180
void SetServo(int Port,int Speed,int Angle);

//伺服电机初始化
void ServoInit(void);

//打开PWM舵机电源
void SERVO_PWR_ON(void);

//关闭PWM舵机电源
void SERVO_PWR_OFF(void);







#endif
#endif

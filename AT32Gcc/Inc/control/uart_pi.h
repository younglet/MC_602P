/*
 * uart_pc.h
 *
 *  Created on: 2022年12月6日
 *      Author: Administrator
 *      说明：PC通信串口初始化和中断处理
 */

#ifndef CONTROL_UART_PI_H_
#define CONTROL_UART_PI_H_


//编译使能
#ifdef CONTROL_UART_PI_H_




/*
UART PI  ->  USART7
TXD      ->  PE8
RXD      ->  PE7
BUAD     ->  115200
*/
#define UART_PI_TXD_PIN             GPIO_Pin_8
#define UART_PI_TXD_PORT            GPIOE

#define UART_PI_RXD_PIN             GPIO_Pin_7
#define UART_PI_RXD_PORT            GPIOE
// PC串口编号
#define UART_PI                     USART7 
#define UART_PI_BUAD                115200
//PC串口IRQ通道
#define UART_PI_NVICCH              UART7_IRQn//77    /*UART7_IRQn!< uart7 interrupt*/
//PC串口中断优先级,最高
#define UART_PI_IRQ_PRIORITY        0
#define UART_PI_IRQ_SUBPRIORITY     0

#define UART_PI_PRINTBUFFERLEN      196//uart pc每次最多可打印的数据长度

//初始化UART_PC串口
void InitUart_Pi(void);


//PC串口收到1个字节的中断回调函数
void UartPiRx_CallBack(void);

//设置PC串口接收回调
void setUartPi_RxHandle(FunType RxHandle);

//设置PC串口发送回调，当发送完一个数据后，回调该函数
void setUartPi_TxHandle(FunType TxHandle);



//PC串口发送数据
void UartPi_Sendbyte(uint8_t data);


//PC串口发送数据len指定的字节数据
void UartPi_Sendbytes(uint8_t *data,int len);


//串口发送Printf
void Printf2UartPi(char *fmt,...);





#endif
#endif



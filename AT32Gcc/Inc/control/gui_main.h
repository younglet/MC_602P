/*
 * gui_main.h
 *
 *  Created on: 2022年12月22日
 *      Author: Administrator
 */

#ifndef CONTROL_GUI_MAIN_H_
#define CONTROL_GUI_MAIN_H_

#ifdef CONTROL_GUI_MAIN_H_


//参数设置
#define CH   1//中文
#define EN   2//英文

#define AUTORUN_RunA 0xA0
#define AUTORUN_RunB 0xA1
#define AUTORUN_RunC 0xA2
#define AUTORUN_RunD 0xA3
#define AUTORUN_RunE 0xA4
#define AUTORUN_RunF 0xA5
#define AUTORUN_GUI  0xAA

//En，CH;中英文选择,根据范围判断参数是否合法
int Assert_EnOrCH(int value);


//界面主操作线程
void gui_main(void);


#endif /* CONTROL_GUI_MAIN_H_ */
#endif /* CONTROL_GUI_MAIN_H_ */

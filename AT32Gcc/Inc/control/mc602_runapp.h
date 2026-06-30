/*
 * mc602_run.c
 *
 *  Created on: 2022年12月22日
 *      Author: Administrator
 *      说明：用户操作界面
 */
#include "main.h"


#ifndef CONTROL_MC602_RUN_H_
#define CONTROL_MC602_RUN_H_


#ifdef CONTROL_MC602_RUN_H_




#define MC602_APP_COUNT  6//602控制器存储程序个数

// 获取602控制器程序名称
char *getFileName_MC602(int index);

//每个602控制器程序大小
#define MC602_APP_LEN      100*1024 //100K
//MC602总共6个程序，地址如下
#define MC602_APP1_ADDRESS (FLASH_BASE + (384*1024))//0x08060000
#define MC602_APP2_ADDRESS (FLASH_BASE + (512*1024))//0x08080000
#define MC602_APP3_ADDRESS (FLASH_BASE + (612*1024))//0x08099000
#define MC602_APP4_ADDRESS (FLASH_BASE + (712*1024))//0x080B2000
#define MC602_APP5_ADDRESS (FLASH_BASE + (812*1024))//0x080CB000
#define MC602_APP6_ADDRESS (FLASH_BASE + (912*1024))//0x080E4000



// 加载第index个文件,将appx数据复制到gcc运行地址上
uint32_t LoadBin_602(int index);

//通过文件名，加载文件系统上的BIN文件，并执行
void LoadBinByName_602(char *filename);








#endif
#endif


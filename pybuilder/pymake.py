# coding=utf-8

import os
import platform
import subprocess
import time
import argparse

ver = 0.1
# 显示软件名称版本
print("Whales Robot pymake ver:" + str(ver))


'''
文件夹路径
MC902P
MC602P
'''
#CPDIR = "MC_902P\\"
CPDIR = "mc602p-firmware\\"





PRINT_LEVEL =5#5#5信息少,20信息多，小于此数字的Prinf将被显示出来


#.\AI_Module_GCC\MC_902P\AT32Gcc

#包含C源码文件的目录,以下是全编译.注意顺序不可颠倒
src_dir_list = [
    ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Src\\user\\"                          ,
    ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Src\\externlib\\"
    #".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Src\\control\\"
]
#src_dir_list_externlib =".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Src\\externlib\\"#如果全编译，则要往 src_dir_list 列表中添加此源码目录
src_dir_list_control =".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Src\\control\\"#如果全编译，则要往 src_dir_list 列表中添加此源码目录
src_dir_list_stdlib =".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\STM32_Stdlib\\STM32F10x_StdPeriph_Driver\\src\\"#如果全编译，则要往 src_dir_list 列表中添加此源码目录
src_dir_list_freertos =".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\STM32_Stdlib\\FreeRTOS\\src\\"#如果全编译，则要往 src_dir_list 列表中添加此源码目录


#C编译输出包含obj文件的目录,以下是全编译.注意顺序不可颠倒
debug_src_dir_list = [
    ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Src\\user\\"                   ,
    ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Src\\externlib\\"
    #".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Src\\control\\"
]
#debug_src_dir_list_externlib =".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Src\\externlib\\"#如果全编译，则要往 debug_src_dir_list 列表中添加此源码目录
debug_src_dir_list_control =".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Src\\control\\"#如果全编译，则要往 debug_src_dir_list 列表中添加此源码目录
debug_src_dir_list_stdlib =".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\STM32_Stdlib\\STM32F10x_StdPeriph_Driver\\src\\"#如果全编译，则要往 debug_src_dir_list 列表中添加此源码目录
debug_src_dir_list_freertos =".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\STM32_Stdlib\\FreeRTOS\\src\\"#如果全编译，则要往 debug_src_dir_list 列表中添加此源码目录


#包含obj文件的目录，提供链接器链接obj文件清单,以下是全编译.注意顺序不可颠倒
obj_dir_list = [
    ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Src\\user\\"                                               ,
    ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Src\\externlib\\"                                          ,
    ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Src\\control\\"                                            ,
    ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\STM32_Stdlib\\STM32F10x_StdPeriph_Driver\\src\\"           ,
    ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\STM32_Stdlib\\FreeRTOS\\src\\"                             ,
    ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Startup\\"                                                 ,
]








# 显示操作系统
OS_NAME = platform.system()
print("-system:" + OS_NAME)


def Errlog(msg):
    f=open("errlog","a")
    f.writelines(time.strftime('%Y-%m-%d %H:%M:%S'))
    f.writelines(msg)
    f.writelines("\n")
    f.close()

Scratchmsg=""
def PrintLog(level,msg):
    global Scratchmsg
    if msg=="":
        return
    if level <= PRINT_LEVEL:
        Scratchmsg=Scratchmsg+msg+"\n"
        print(msg)
    Errlog(msg)

#Linux文件路径符号
CMD_FILE_SPLIT_LINUX = "/"
# windows文件路径符号
CMD_FILE_SPLIT_WINDOWS = "\\"


if OS_NAME == "Linux":
    # Liux系统指令
    CMD_BUILDER_C = "../gcc-arm-none-eabi-linux/bin/arm-none-eabi-gcc"
    CMD_MAKE_BIN = "../gcc-arm-none-eabi-linux/bin/arm-none-eabi-objcopy"
    CMD_GET_SIZE = "../gcc-arm-none-eabi-linux/bin/arm-none-eabi-size"
else:
    # Windows系统指令
    CMD_BUILDER_C = ".\\AI_Module_GCC\\arm_gcc_10\\bin\\arm-none-eabi-gcc"
    CMD_MAKE_BIN = ".\\AI_Module_GCC\\arm_gcc_10\\bin\\arm-none-eabi-objcopy"
    CMD_GET_SIZE = ".\\AI_Module_GCC\\arm_gcc_10\\bin\\arm-none-eabi-size"

#C编译脚本
opt_space = " "
opt_c_file =".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\user\\main.c"#动态替换
opt_para1 = "-mcpu=cortex-m3 -std=gnu11 -g3 -DDEBUG -DSTM32 -DSTM32F1 -DSTM32F101VETx -c"
opt_inc_list = [
    " -I\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Inc\\user\""
    " -I\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Inc\\control\""
    " -I\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Inc\\externlib\""
    " -I\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Inc\""
    " -I\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\STM32_Stdlib\\CMSIS\\CM3\\DeviceSupport\\ST\\STM32F10x\""
    " -I\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\STM32_Stdlib\\STM32F10x_StdPeriph_Driver\\inc\""
    " -I\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\STM32_Stdlib\\CMSIS\\CM3\\CoreSupport\""
    " -I\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\STM32_Stdlib\\FreeRTOS\\inc\""
]
#opt_para2 = "-O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -MMD -MP"
opt_para2 = "-Ofast -ffunction-sections -fdata-sections -Wall -fstack-usage -MMD -MP"
opt_para_MF = "-MF"
opt_dep_file = ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Src\\user\\main.d"#动态替换
opt_para_MT = "-MT"
opt_obj_file = ".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Src\\user\\main.o"#动态替换
opt_para3 = "--specs=nano.specs -mfloat-abi=soft -mthumb"
opt_para_obj = "-o"

#Link脚本
link_para_o=" -o "
link_para_elf="\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\AT32Gcc.elf\""
link_para_at =" @"
link_para_list="\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\objects.list\""
link_para_0="   -mcpu=cortex-m3 -T"
link_para_linkfile="\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\linkscript\\stm32_flash.ld\" "
link_para_1="--specs=nosys.specs -Wl,-Map="
link_para_mapfile="\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\AT32Gcc.map\""
link_para_2=" -Wl,--gc-sections -static --specs=nano.specs -mfloat-abi=soft -mthumb -u _printf_float -u _scanf_float -Wl,--start-group -lc -lm -Wl,--end-group"


#生成BIN文件脚本
#arm-none-eabi-objcopy  -O binary  AT32Gcc.elf  "AT32Gcc.bin"
obj_copy_para1=" -O binary  "
obj_copy_elffile="\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\AT32Gcc.elf\""
obj_copy_binfile="\".\\AI_Module_GCC\\"+CPDIR+"AT32Gcc\\Debug\\Run.bin\""

#获取程序大小
#arm-none-eabi-size   AT32Gcc.elf


# 生成头文件Include包含清单
opt_inc = ""
for i in range(len(opt_inc_list)):
    opt_inc = opt_inc + opt_inc_list[i] + opt_space


#检查是否有ERROR
def IsComplieError(msg):
    if msg.find("error")>0:
        return True
    else:
        return False


def Complie():
    ErrorCount = 0
    #遍历所有需要编译的路径，获得的C语言代码文件名:"main.c"
    CFiles=[]
    #遍历所有需要编译的路径，获得的C语言代码路径名:"..\\AT32Gcc\\Src\\user\\main.c"
    CPath=[]
    #遍历所有需要编译C文件后的输出路径:"..\\AT32Gcc\\Debug\\Src\\user\\"
    CObjPath=[]
    #遍历需要编译的目录
    i=0
    for dir in src_dir_list:
        for root, dirs, files in os.walk(dir):
            for file in files:
                path = os.path.join(root, file)
                CFiles.append(file)
                CPath.append(path)
                CObjPath.append(debug_src_dir_list[i])
                PrintLog(10, "file:" + file + " Path:" + path + " obj:" + debug_src_dir_list[i])
        i=i+1
    for i in range(len(CPath)):
        PrintLog(5, "make:" + CFiles[i] )
        # 生成编译指令
        CMD_BUILDER = CMD_BUILDER_C + opt_space + \
                      CPath[i] + opt_space + \
                      opt_para1 + opt_space + \
                      opt_inc + opt_space + \
                      opt_para2 + opt_space + \
                      opt_para_MF + opt_space + \
                      (CObjPath[i]+CFiles[i]).replace(".c",".d") + opt_space + \
                      opt_para_MT + opt_space + \
                      (CObjPath[i]+CFiles[i]).replace(".c",".o") + opt_space + \
                      opt_para3 + opt_space + \
                      opt_para_obj + opt_space + \
                      (CObjPath[i]+CFiles[i]).replace(".c",".o") + opt_space
        PrintLog(10,CMD_BUILDER)#调试显示编译命令行
        #C编译
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        oscmd = subprocess.Popen(CMD_BUILDER,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=4096,startupinfo=startupinfo)#os.popen(CMD_BUILDER)#执行C编译
        #oscmd.wait()
        #msgstd = oscmd.stdout.readlines()
        #msgerr = oscmd.stderr.readlines()
        msg = ""
        while oscmd.poll() is None:
            msgtmp = str(oscmd.stderr.readline(),encoding='utf8')
            msg=msg+msgtmp 
            oscmd.stderr.flush() # 刷新缓存，防止缓存过多造成卡死
        PrintLog(5, msg)#显示编译结果
        #检查错误
        if IsComplieError(msg)==True:
            ErrorCount=ErrorCount+1
            return False
    if ErrorCount == 0:
        return True
    else:
        return False


def IsLinkError(msg):
    if msg.find("error")>0:
        return True
    else:
        return False

#链接
def Link():
    #先获取相应路径下的.obj文件
    LinkObj=[]
    i=0
    for dir in obj_dir_list:
        for root, dirs, files in os.walk(dir):
            i=0
            #for file in files:
            for i in range(len(files)):
                file=files[len(files)-i-1]
                path = os.path.join(root, file)
                if file.endswith(".o"):
                    LinkObj.append(path.replace(CMD_FILE_SPLIT_WINDOWS,CMD_FILE_SPLIT_LINUX))
    #生成OBJLIST文件
    try:
        f=open(link_para_list.replace("\"",""),"w+")#清空文件
        for i in range(len(LinkObj)):
            f.writelines("\"" + LinkObj[len(LinkObj)-i-1] + "\"")
            f.writelines("\n")
        f.close()
    except Exception as e:
        PrintLog(5, "objlist file read error:" + link_para_list)  # 显示编译结果
        return False
    #进行链接
    PrintLog(5, "Link...")
    CMD_BUILDER = CMD_BUILDER_C  + link_para_o +\
                  link_para_elf + \
                  link_para_at + \
                  link_para_list + \
                  link_para_0 + \
                  link_para_linkfile + \
                  link_para_1 + \
                  link_para_mapfile +\
                  link_para_2
    PrintLog(10, CMD_BUILDER)  # 调试显示连接命令
    #执行链接
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    oscmd = subprocess.Popen(CMD_BUILDER,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=4096,startupinfo=startupinfo)#os.popen(CMD_BUILDER)  #调用链接器
    msgstd = ""#oscmd.stdout.readlines()
    msgerr = oscmd.stderr.readlines()
    msg = ""
    for count in range(len(msgstd)):
        msg = msg + str(msgstd[count], encoding='utf8')
    for count in range(len(msgerr)):
        msg = msg + str(msgerr[count], encoding='utf8')
    PrintLog(5, msg)  # 显示编译结果
    if IsLinkError(msg) == True:
        return False#有错误，返回False
    return True#成功，返回True



def IsMakeBinError(msg):
    return False
#生成BIN文件
def MakeBin():
    PrintLog(5, "Make Bin...")
    CMD_BUILDER = CMD_MAKE_BIN  + \
                  obj_copy_para1 + opt_space + \
                  obj_copy_elffile + opt_space + \
                  obj_copy_binfile
    PrintLog(10, CMD_BUILDER)  # 调试显示连接命令
    #执行链接
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    oscmd = subprocess.Popen(CMD_BUILDER,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=4096,startupinfo=startupinfo)#os.popen(CMD_BUILDER)  #调用
    msgstd = oscmd.stdout.readlines()
    msgerr = oscmd.stderr.readlines()
    msg = ""
    for count in range(len(msgstd)):
        msg = msg + str(msgstd[count], encoding='utf8')
    for count in range(len(msgerr)):
        msg = msg + str(msgerr[count], encoding='utf8')
    PrintLog(5, msg)  # 显示编译结果
    if IsMakeBinError(msg) == True:
        return False#有错误，返回False
    return True#成功，返回True


#获取程序大小
def GetSize():
    PrintLog(5, "Size...")
    CMD_BUILDER = CMD_GET_SIZE     + opt_space + \
                  obj_copy_elffile + opt_space 
    PrintLog(10, CMD_BUILDER)  # 调试显示连接命令
    #执行链接
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    oscmd = subprocess.Popen(CMD_BUILDER,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=4096,startupinfo=startupinfo)#os.popen(CMD_BUILDER)  #调用
    msgstd = oscmd.stdout.readlines()
    msgerr = oscmd.stderr.readlines()
    msg = ""
    for count in range(len(msgstd)):
        msg = msg + str(msgstd[count], encoding='utf8')
    for count in range(len(msgerr)):
        msg = msg + str(msgerr[count], encoding='utf8')
    PrintLog(5, msg)  # 显示编译结果
    if IsMakeBinError(msg) == True:
        return False#有错误，返回False
    return True#成功，返回True






def main(all):
    if all == "true":#如果是全编译选项，则要添加的库函数路径
        #src_dir_list.append(src_dir_list_externlib)
        src_dir_list.append(src_dir_list_control)
        src_dir_list.append(src_dir_list_stdlib)
        src_dir_list.append(src_dir_list_freertos)
        #debug_src_dir_list.append(debug_src_dir_list_externlib)
        debug_src_dir_list.append(debug_src_dir_list_control)
        debug_src_dir_list.append(debug_src_dir_list_stdlib)
        debug_src_dir_list.append(debug_src_dir_list_freertos)
    if Complie() == False:
        PrintLog(5, "make error")  # 显示编译结果
        return False
    if Link() == False:
        PrintLog(5, "make error")  # 显示编译结果
        return False
    if MakeBin() == False:
        PrintLog(5, "make error")  # 显示编译结果
        return False
    if GetSize() == False:
        PrintLog(5, "make error")  # 显示编译结果
        return False
    #运行到此处，说明程序已经编译完成
    PrintLog(5, "make Success")  # 显示编译结果
    return True






#上位机build调用接口
#返回bResult,Scratchmsg
#bResult(bool):True/False表示是否有编译错误
#Scratchmsg：编译相关信息
def build():
    global Scratchmsg
    Scratchmsg=""#清除编译输出
    #PrintLog(5, os.getcwd())  # 显示编译结果
    #PrintLog(5, os.path.abspath(os.path.dirname(__file__)))  # 返回当前目录
    bResult=main("false")#上层调用，使用的是快速编译
    return bResult,Scratchmsg
'''
#测试build函数
result1,msg=build()
print("result1="+str(result1))
print("msg=" + msg)
'''



if __name__== "__main__" :
    parser = argparse.ArgumentParser()  # 创建ArgumentParser对象
    parser.add_argument('-all', default="false")
    args = parser.parse_args()
    main(args.all)
    #build()


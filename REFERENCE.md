# MC_602P 完整参考手册

> WhalesBot MC602P 机器人控制器 — GCC SDK 逆向分析与硬件映射
>
> 控制器芯片：AT32F403 (兼容 STM32F103ZE) | Cortex-M3 | 168MHz | FreeRTOS

---

[[_TOC_]]

---

## 1. 物理端口 ↔ 逻辑端口 ↔ GPIO 映射

### 1.1 电机接口（水晶头，6路）

每路含 PWM + DIR + 正交编码器，TIM6 中断驱动速度环 PID。

| 物理口 | 逻辑 | PWM 引脚 (TIM) | DIR 引脚 | 编码器 A | 编码器 B |
|--------|:---:|------|------|------|------|
| M1 | `PA` | PC6 (TIM8_CH1) | PE12 | PE4 | PE5 |
| M2 | `PB` | PC7 (TIM8_CH2) | PD14 | PE6 | PD3 |
| M3 | `PC` | PC8 (TIM8_CH3) | PD15 | PE0 | PE1 |
| M4 | `PD` | PC9 (TIM8_CH4) | PD0  | PA14 (SWCLK) | PA13 (SWDIO) |
| M5 | `PE` | PB6 (TIM4_CH1) | PD1  | PB15 | PB7 |
| M6 | `PF` | PB8 (TIM4_CH3) | PE10 | PD13 | PD12 |

> TIM8 → M1~M4 | TIM4 → M5~M6 | PID 闭环在 TIM6 中断，默认 P=80 I=3 D=0（×1000 定点运算）

### 1.2 数字输出 / PWM 舵机 / 模拟输入（水晶头 + 排针）

同一套 P1~P13 逻辑编号，分布在两种物理接口上。

| 逻辑 | GPIO | 物理形态 | 功能1: DO | 功能2: PWM 舵机 | 功能3: 模拟输入 |
|:---:|------|------|:---:|:---:|:---:|
| P1 | PD5 | 水晶头 | ✓ 电磁铁/灯 | — | — |
| P2 | PD4 | 水晶头 | ✓ 电磁铁/灯 | — | — |
| P3 | PC15 | 水晶头 | ✓ 电磁铁/灯 | — | — |
| P4 | PD10 | 水晶头 | ✓ 电磁铁/灯 | — | — |
| P5 | PA4 | 水晶头 | ✓ 电磁铁/灯 | — | — |
| P6 | PB9 | 水晶头 | ✓ 电磁铁/灯 | — | — |
| P7 | PE9 | **排针** | ✓ | TIM1_CH1 (舵机1) | AI1 (ADC1_CH14, PC4) |
| P8 | PE11 | **排针** | ✓ | TIM1_CH2 (舵机2) | AI2 (ADC1_CH15, PC5) |
| P9 | PE13 | **排针** | ✓ | TIM1_CH3 (舵机3) | AI3 (ADC1_CH9, PB1) |
| P10 | PE14 | **排针** | ✓ | TIM1_CH4 (舵机4) | — |
| P11 | PA7 | **排针** | ✓ | TIM3_CH2 (舵机5) | — |
| P12 | PA6 | **排针** | ✓ | TIM3_CH1 (舵机6) | — |
| P13 | PB14 | **排针** | ✓ | TIM12_CH1 (舵机7) | — |

> P7/P8/P9 是唯一的三功能口：同一个排针物理口可以出 DO / PWM 舵机 / 模拟电压输入。

### 1.3 I2C 传感器总线（排针，10 个端口）

```
P1 ────── 独立 I2C (PD2=SCL, PC12=SDA) + UART5
P2 ────── 独立 I2C (PC11=SCL, PC10=SDA) + UART4

P3~P10 ──┐  共享 I2C 总线 (PB10=SCL, PB11=SDA)
          ├── ICHA (PB12) } 2-bit 通道选择
          └── ICHB (PB13) } 最多 4 路分时复用
```

**I2C 地址表**（`getPortSensorType()` 扫描用）：

| 传感器 | I2C Addr | 说明 |
|------|:---:|------|
| K210 AI 摄像头 | `0x54` / `0x57`(v2) | 图像识别/巡线/二维码 |
| 颜色传感器 | `0x44` | RGB/HSV 颜色识别 |
| 激光 TOF | `0x48` | 测距 |
| 超声波 | `0x55` | 测距 |
| 陀螺仪 (DMP) | `0x56` | 3 轴姿态 |
| 手势识别 | `0x60` | 9 种手势 |
| 温湿度 | `0x43` | 温度+湿度 |
| 气压 SPL06 | `0x76` | 纯硬件 I2C，无 MCU 转接 |
| MPU6500 | `0x69` | 纯硬件陀螺仪 |
| 数码管 | `0x52` | 4 位 7 段 |
| 点阵屏 | `0x51` | 8×8 LED 矩阵 |
| RGB 灯 | `0x30` | 全彩 LED |
| 未识别 | `0xFE` | 返回 DUMMY |

### 1.4 内部总线一览

| 总线 | 外设 | GPIO | 速率 | 用途 |
|------|------|------|:---:|------|
| RS485 | USART3 | PD8(TX), PD9(RX), PE2(DIR) | 1Mbps | 舵机链 + 步进电机 |
| 蓝牙 UART | USART2 | PA2(TX), PA3(RX) | 115200 | 板载蓝牙/遥控器 |
| USB 串口 | USART1 | PA9(TX), PA10(RX) | 1Mbps | CH340 → PC 下载/调试 |
| Pi 串口 | UART? | PB8(TX), PB7(RX) | — | 树莓派通信预留 |
| SPI Flash | SPI1 | PA15(NSS), PB3(SCK), PB4(MISO), PB5(MOSI) | — | 外部 NOR Flash |
| SPI LCD | SPI1(复用) | +PE3(RST), PE11(RS) | — | LCD 与 Flash 分时复用 |

---

## 2. SDK 模块速查

### 2.1 电机驱动

| API | 参数 | 说明 |
|------|------|------|
| `set_motor(port, speed)` | M1~M6, -100~100 | **PID 速度闭环**（默认方式） |
| `set_motor_open(port, speed)` | M1~M6, -100~100 | 开环 PWM（无编码器反馈） |
| `set_motor_angle(port, speed, angle)` | M1~M6 | 角度闭环控制 |
| `set_motor_free(port)` | M1~M6 | 释放电机 |
| `off_motor(port)` | M1~M6 / MotorAll | 关闭电机 |
| `move(type, speed)` | 前进/后退/左转/右转 | 整车移动 |
| `mecanum_wheel_ctrl(speed, angle)` | 0~100, 0~360 | 麦克纳姆轮全向 |
| `mecanum_wheel_turn(dir, speed)` | 左/右 | 麦克纳姆轮自转 |
| `SetMotorPID(P, I, D)` | 默认 80,3,0 | 调节 PID 参数 |
| `getEncoder_Pos/Speed(port)` | M1~M6 | 读取编码器 |

> **PID 特性**：速度环闭环 + 堵转保护（1s 超时，2s 恢复）+ 电池电压补偿

### 2.2 舵机

| API | 说明 |
|------|------|
| `set_servo_angle(id, speed, angle)` | 485 总线舵机角度（0~1023） |
| `set_servo_rotation(id, speed)` | 连续旋转模式 |
| `set_servo_torque(id, enable)` | 力矩使能/释放 |
| `servo_id_change(oldID, newID)` | 修改舵机 ID |
| `Servo_IDscan()` | 扫描总线所有舵机 |
| `ReadServoaAngle(id)` | 读取当前角度 |
| `SetServo(port, speed, angle)` | PWM 舵机（P7~P13，7 路） |

### 2.3 传感器

| API | 传感器类型 |
|------|------|
| `get_ultrasonic_distance(port)` | 超声波测距 |
| `color_value(port)` / `color_detected(port, color)` | 颜色传感器 |
| `get_tof(port)` | TOF 激光测距 |
| `gyroscope(port, axis)` | 陀螺仪 (X/Y/Z 轴加速度/角速度) |
| `get_gesture(port)` | 手势识别 (上/下/左/右/前/后/顺/逆/挥) |
| `get_temperature(port)` / `get_humidity(port)` | 温湿度 |
| `get_pressure(port, ch)` | 气压 SPL06 |
| `get_infrared_distance(port)` | 红外测距 |
| `get_single_grayscale(port)` / `get_integrated_grayscale(port, ch)` | 灰度/五灰度 |
| `magnetic_detected(port)` / `touch_switch_pressed(port)` | 磁敏/触碰 |
| `get_sound_volume(port)` / `get_flame(port)` | 声音/火焰 |
| `get_ambient_light(port)` | 环境光 |
| `getAI(port)` | 模拟电压值 (0~4095) |

### 2.4 AI 摄像头

| API | 说明 |
|------|------|
| `get_AI_image(port)` | 图像识别：数字/箭头/水果/生肖 |
| `get_AI_voice(port)` | 语音识别：前进/后退/左转/右转... |
| `AI_read_value_v2(port, mode, para)` | K210 通用数据（AprilTag/道路/人脸/颜色/分类/QR码） |
| `AI_take_photo(port, mode, cnt)` | 拍照/显示照片 |
| `Init_lane(port, color, ...)` | AI 巡线初始化 |
| `patr_XX(speed)` / `patr_road1/2(...)` | AI 视觉巡线 |

### 2.5 显示输出

| API | 说明 |
|------|------|
| `Printf(fmt, ...)` / `show(line, fmt, ...)` | LCD 屏幕输出 |
| `LCD_ClearBuffer()` / `ClearLCD()` | 清屏 |
| `display_symbol(port, id)` | 8×8 LED 符号 |
| `display_emotion(p1, p2, emoji)` | 双屏表情 |
| `display_digital_tube(port, num)` | 数码管 |
| `set_RGB(port, R, G, B)` | RGB 灯 |
| `set_rgb_led_strip(port, id, R, G, B)` | RGB 灯带 |
| `set_light(port, on/off)` | 灯光控制 |
| `set_magnet(port, on/off)` | 电磁铁 |

### 2.6 音频

| API | 说明 |
|------|------|
| `play_sound(id)` | 播放内置音效 (58 种) |
| `beep(freq, sec)` | 蜂鸣器频率+时长 |
| `recorder(port)` / `play_record()` | 录音/播放 |
| `read_number(val)` | 语音报数 |
| `SetSoundVol(vol)` | 音量控制 |

### 2.7 系统控制

| API | 说明 |
|------|------|
| `wait(sec)` | 线程延时 (FreeRTOS，不阻塞) |
| `sleep(sec)` | 阻塞延时 |
| `seconds()` / `resettime()` | 运行计时 |
| `random_number(min, max)` | 随机数 |
| `ReadEEPROM(addr)` / `WriteEEPROM(addr, val)` | EEPROM 读写 |
| `Program_Run(addr)` / `Program_Reset()` | 程序跳转/复位 |
| `ThreadStart(func)` | 创建新线程 |
| `getBatt()` / `getBattPercentage()` | 电池电压/百分比 |
| `getKey(key)` | 按键状态 |
| `get_bt_remote_control(ch)` | 蓝牙遥控器通道 |

### 2.8 巡线算法（Goline 库）

| API | 说明 |
|------|------|
| `patrol_integrated_initialization(LM, LS, RM, RS)` | 集成灰度初始化 |
| `patrol_single_initialization(..., P1~P5)` | 单灰度初始化 |
| `patrol_ambient_detection()` | 环境采集（黑白校准） |
| `patrol_speed(speed)` | 巡线速度控制 |
| `patrol_road(type, speed, time)` | 路口巡线（左/T字/右） |
| `patrol_time(speed, time)` | 定时巡线 |
| `patrol_turn(type, LS, RS)` | 定点转弯 |
| `patrol_button()` | 按钮启动等待 |

### 2.9 动作页引擎

| API | 说明 |
|------|------|
| `play_page(page)` | 播放动作页 (1~127，每页最多 20 舵机) |
| `quit_page()` | 退出（播放退出页后停止） |
| `stop_page()` | 强制停止 |
| `play_dance()` | 播放舞蹈动作 |
| `IsPagePlaying()` | 判断播放状态 |

---

## 3. 数学函数

| API | 说明 |
|------|------|
| `math_abs(x)` / `abs(x)` | 绝对值 |
| `math_sin/cos/tan(x)` | 三角函数 |
| `math_asin/acos/atan(x)` | 反三角函数 |
| `math_sqrt(x)` | 平方根 |
| `math_ln/log/exp/pow10(x)` | 对数/指数 |
| `math_round/floor/ceiling(x)` | 取整 |
| `constrain(amt, lo, hi)` | 范围约束 |
| `math_modulus(a, b)` | 取模 |

---

## 4. 端口常量速查

```c
// 电机
M1=1  M2=2  M3=3  M4=4  M5=5  M6=6  MotorAll=0

// 端口
P1=1  P2=2  P3=3  P4=4  P5=5  P6=6
P7=7  P8=8  P9=9  P10=10  P11=11  P12=12

// 模拟输入
AI1=P7  AI2=P8  AI3=P9

// 舵机
S1=1  S2=2  ...  S18=18

// 移动方向
move_forward=1  move_backward=2  move_turnleft=3  move_turnright=4

// 颜色
color_white=1  color_yellow=2  color_purple=3  color_cyan=4
color_red=5    color_green=6   color_blue=7     color_black=8

// 线型
black_line=1  white_line=2

// 巡线路口
intersection_left=0  intersection_T=1  intersection_right=2

// 巡线转弯
turn_left=0  turn_center=1  turn_right=2

// 开关
switch_on=1  switch_off=0
```

---

## 5. 内存布局

```
0x08000000  BootLoader        52KB
0x0800D000  ★ GCC 用户程序    100KB  ← 本项目
0x08040000  GUI 界面程序      128KB
0x08060000  USB Mass Storage  128KB
0x08060000  RunA             100KB
0x08080000  RunB             100KB
0x08099000  RunC             100KB
0x080B2000  RunD             100KB
0x080CB000  RunE             100KB
0x080E4000  RunF             100KB
```

---

## 6. 程序槽位机制（RunA ~ RunF）

### 6.1 核心原理：槽位是存储器，不是执行区

**所有用户程序都链接到同一个地址 `0x0800D000` 运行**。RunA~RunF 六个槽位是 Flash **存储区**，不是独立执行区。选择程序时，固件把槽位里的代码**复制**到执行区，再跳转运行。

```
         卡带收纳盒（存储）               卡带插槽（执行）
         ──────────────                  ──────────────
0x08060000  RunA (100KB)  ──┐
0x08080000  RunB (100KB)  ──┤
0x08099000  RunC (100KB)  ──┼── 复制 ──→  0x0800D000  GCC 执行区 (100KB)
0x080B2000  RunD (100KB)  ──┤              ↑ CPU 只从这里取指令
0x080CB000  RunE (100KB)  ──┤
0x080E4000  RunF (100KB)  ──┘
```

**为什么不能原地执行？** Cortex-M3 的中断向量表必须位于 Flash 起始处，且所有用户程序用同一份 Linker Script 编译（`ORIGIN = 0x0800D000`），跳转地址、函数调用、全局变量地址全部硬编码为相对 `0x0800D000` 的偏移。换个地址直接跑必然崩溃。

### 6.2 切换流程

```
用户在 GUI 菜单选择 RunC
        │
        ▼
GUI 固件调用 LoadBin_602(2)         ← mc602_runapp.h
        │
        ├─ 1. 从 0x08099000 读取 RunC 的 BIN
        ├─ 2. 擦除 0x0800D000 起的 100KB Flash
        ├─ 3. 逐字节写入新代码到 0x0800D000
        └─ 4. Program_Run(0x0800D000)  ← 设置堆栈指针 → 跳转 Reset_Handler
```

### 6.3 命令速查

#### PC 端串口命令

```bash
# 下载到 RunC 槽位（存储，不运行）
python pybuilder/pydownload.py -file Run.bin -address 0x08099000 -run false

# 下载到执行区并立即运行（debug 模式，绕过槽位）
python pybuilder/pydownload.py -file Run.bin -address 0x0800D000 -run true

# 不下载，直接跳转运行 RunC 槽位已有程序
python pybuilder/pydownload.py -file FILENOLOAD -address 0x08099000 -run true

# 不下载，跳转回 GUI 菜单界面
python pybuilder/pydownload.py -file FILENOLOAD -address 0x08040000 -run true
```

#### C 代码调用

```c
#include "mc602_runapp.h"

LoadBin_602(0);   // 加载 RunA 并运行
LoadBin_602(5);   // 加载 RunF 并运行

Program_Run(0x08040000);   // 直接跳回 GUI 菜单（不加载程序）
Program_Reset();           // 软复位，BootLoader 重新启动
```

### 6.4 debug 模式 vs 槽位存储模式

| 模式 | `isrun` | 下载地址 | 行为 |
|------|:---:|------|------|
| **debug** | `true` | `0x0800D000` | 下载到执行区 → 立即运行。最快，适合开发调试 |
| **存入槽位** | `false` | `0x08099000` 等 | 下载到存储槽 → 不运行。下次开机从 GUI 菜单选择 |

### 6.5 BootLoader 协议支持的命令

`pydownload.py` 通过 USB 虚拟串口 (1Mbps) 与 BootLoader 通信：

| 命令 | 值 | 功能 |
|------|:---:|------|
| `CMD_PING` | `0x01` | 检测控制器型号（返回 602/902/102） |
| `CMD_WRITEBUFFER` | `0x10` | 发送 4KB 代码到 RAM 缓冲区 |
| `CMD_RAM2FLASH` | `0x20` | RAM 缓冲烧录到指定 Flash 地址 |
| `CMD_CRC` | `0x50` | CRC32 校验（断点续传，已有数据跳过） |
| `CMD_SAVEFILENAME` | `0x30` | 保存程序名到 Flash（GUI 菜单显示用） |
| `CMD_RUNCODE` | `0x40` | 跳转到指定地址执行 |

---

## 7. 编译与下载

```bash
# 增量编译（仅编译 user + externlib；SDK .o 不变）
python pybuilder/pymake.py

# 全量编译（含 STM32 标准库 + FreeRTOS + 所有 SDK 源文件）
python pybuilder/pymake.py -all true
```

编译输出：`AT32Gcc/Debug/Run.bin`

下载到控制器走 BootLoader 协议：USB 虚拟串口 1Mbps → `CMD_WRITEBUFFER`(4KB 分块) → `CMD_RAM2FLASH` → `CMD_CRC`(断点续传) → `CMD_RUNCODE`。

---

## 8. 项目文件索引

| 文件 | 说明 |
|------|------|
| [`intro.md`](intro.md) | 项目架构深度分析 |
| [`hardware_api.csv`](hardware_api.csv) | 336 个 API 完整清单 (CSV) |
| [`AT32Gcc/Src/user/user_main.c`](AT32Gcc/Src/user/user_main.c) | **用户程序入口（修改这里）** |
| [`AT32Gcc/Inc/control/main.h`](AT32Gcc/Inc/control/main.h) | 编译配置 / 版本定义 |
| [`AT32Gcc/Src/externlib/Goline.c`](AT32Gcc/Src/externlib/Goline.c) | 巡线算法源码 |
| [`AT32Gcc/Src/externlib/play_page.c`](AT32Gcc/Src/externlib/play_page.c) | 动作页引擎源码 |
| [`AT32Gcc/Src/externlib/step_driver.c`](AT32Gcc/Src/externlib/step_driver.c) | 步进电机源码 |
| [`pybuilder/pymake.py`](pybuilder/pymake.py) | 编译工具 |
| [`pybuilder/pydownload.py`](pybuilder/pydownload.py) | 下载工具 |
| [`python/whalesbot.py`](python/whalesbot.py) | Scratch API 定义 |

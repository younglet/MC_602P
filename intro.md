# MC_602P 项目完全解析

> **WhalesBot MC602P 机器人控制器 — GCC 用户固件 SDK**
>
> 最后更新：2026-06-30 | 固件版本：V102

---

## 一、项目概述

MC_602P 是鲸鱼机器人面向教育市场的**旗舰级控制器**，本项目是其 **GCC 用户程序固件**。
配合 Scratch / 流程图 / C 语言编程环境，提供从底层硬件驱动到高层算法库（巡线、动作页、AI 视觉）的完整开发框架。

| 维度 | 详情 |
|------|------|
| **MCU 芯片** | STM32F103ZE / AT32F403 兼容（Cortex-M3） |
| **主频** | 168MHz（内部 RC 振荡器） |
| **Flash** | 512KB（大容量版更多） |
| **RAM** | 94KB（AT32 额外 30KB 用作 RAM Flag） |
| **RTOS** | FreeRTOS（多线程） |
| **工具链** | `arm-none-eabi-gcc` 10.3-2021.10, `-Ofast` |

---

## 二、目录结构总览

```
MC_602P/
├── 📄 intro.md                          ← 你正在看的文件
├── 📁 AT32Gcc/                           ← STM32/AT32 固件工程
│   ├── 📄 Inc/                           # C 头文件
│   │   ├── 📄 control/                   # SDK 控制层头文件（30+）
│   │   ├── 📄 externlib/                 # 扩展库头文件
│   │   │   ├── 📄 Goline.h               # 巡线库 API
│   │   │   ├── 📄 play_dance.h           # 舞蹈动作播放 API
│   │   │   ├── 📄 play_page.h            # 动作页播放 API
│   │   │   ├── 📄 step_driver.h          # 步进电机驱动 API
│   │   │   ├── 📄 mercury.h              # 流程图兼容层
│   │   │   ├── 📄 dance_data.h           # 舞蹈动作数据
│   │   │   └── 📄 page_data.h            # 动作页数据表
│   │   └── 📄 user/
│   │       └── 📄 whalesbot.h            # 用户程序入口头文件
│   ├── 📄 Src/                           # C 源文件
│   │   ├── 📁 control/                   # SDK 层源文件（⚠️ 已删除，仅保留 .o）
│   │   ├── 📁 externlib/                 # 扩展库源文件
│   │   │   ├── 📄 Goline.c               # 巡线算法（~600行，PID + 路口检测）
│   │   │   ├── 📄 play_page.c            # 动作页播放（舵机群控，~500行）
│   │   │   ├── 📄 play_dance.c           # 舞蹈动作播放
│   │   │   ├── 📄 step_driver.c          # 步进电机驱动（485总线）
│   │   │   └── 📄 mercury.c              # 流程图兼容（空壳）
│   │   └── 📁 user/
│   │       └── 📄 user_main.c            # ★ 用户编写的程序入口
│   ├── 📁 STM32_Stdlib/                  # STM32 标准外设库 + FreeRTOS
│   │   ├── 📁 CMSIS/                     # Cortex-M3 内核支持
│   │   ├── 📁 FreeRTOS/                  # FreeRTOS 源码
│   │   └── 📁 STM32F10x_StdPeriph_Driver/# STM32 标准外设驱动
│   ├── 📁 Startup/
│   │   └── 📄 startup_stm32f10x_hd.s     # 启动汇编文件
│   ├── 📄 linkscript/
│   │   └── 📄 stm32_flash.ld             # 链接脚本（内存布局定义）
│   └── 📁 Debug/                         # 编译输出
│       ├── 📄 AT32Gcc.elf                # 链接产物
│       ├── 📄 AT32Gcc.map                # 内存映射文件
│       ├── 📄 AT32Gcc.bin                # 原始二进制
│       ├── 📄 Run.bin                    # 下载用的 BIN 文件
│       ├── 📄 objects.list               # 所有 .o 文件的链接清单
│       ├── 📄 objects.mk                  # 链接对象
│       ├── 📄 sources.mk                  # 源码子目录声明
│       └── 📄 makefile                   # 标准 Makefile（STM32CubeIDE 生成）
├── 📁 pybuilder/                         # Python 编译/下载工具链
│   ├── 📄 pymake.py                      # 增量编译系统
│   ├── 📄 pydownload.py                  # 串口下载工具（BootLoader 协议）
│   └── 📄 common.py                      # 公共路径配置
└── 📁 python/
    └── 📄 whalesbot.py                   # Scratch↔C API 接口定义（150+ 函数）
```

---

## 三、内存布局

控制器 Flash 被划分为多个功能区和 **6 个用户程序存储槽位**：

```
0x08000000 ┌─────────────────────┐
           │   BootLoader        │  52KB  系统引导 + 升级
0x0800D000 ├─────────────────────┤
           │ ★ GCC 用户程序      │  100KB  ← 本项目编译位置
0x08040000 ├─────────────────────┤
           │   GUI 界面程序      │  128KB  用户操作界面
0x08060000 ├─────────────────────┤
           │   USB Mass Storage  │  128KB  U盘模式固件
0x08060000 ├─────────────────────┤
           │   RunA 用户程序区   │  100KB  存储槽位 A
0x08080000 │   RunB 用户程序区   │  100KB  存储槽位 B
0x08099000 │   RunC 用户程序区   │  100KB  存储槽位 C
0x080B2000 │   RunD 用户程序区   │  100KB  存储槽位 D
0x080CB000 │   RunE 用户程序区   │  100KB  存储槽位 E
0x080E4000 └─────────────────────┘  100KB  存储槽位 F
```

> 链接脚本：[`AT32Gcc/linkscript/stm32_flash.ld`](AT32Gcc/linkscript/stm32_flash.ld)

---

## 四、源码架构（三层模型）

```
┌─────────────────────────────────────────────────────────┐
│  user_main.c          ★ 用户编写层（唯一需修改的文件）    │
│  调用 whalesbot.h 提供的所有 API                         │
├─────────────────────────────────────────────────────────┤
│  externlib/           扩展功能库（开放源码，可定制）       │
│  Goline.c  play_page.c  play_dance.c  step_driver.c     │
│  提供巡线、动作页、舞蹈、步进电机等高级算法              │
├─────────────────────────────────────────────────────────┤
│  Src/control/         SDK 驱动层（⚠️ 闭源 .o 文件）      │
│  30+ 模块：motor, servo, sensor, AI, bt, lcd, ...      │
│  提供所有硬件抽象和底层驱动                              │
├─────────────────────────────────────────────────────────┤
│  STM32_Stdlib/        STM32 标准库 + FreeRTOS            │
│  芯片级寄存器操作和多任务调度                            │
└─────────────────────────────────────────────────────────┘
```

### ★ 用户程序入口：[`user_main.c`](AT32Gcc/Src/user/user_main.c)

当前示例实现了一个 **麦克纳姆轮遥控车 + 云台 + 发射机构**，展示了：
- 蓝牙遥控器数据读取（`get_bt_remote_control`）
- 麦克纳姆轮运动学解算
- 舵机角度控制（`set_servo_angle`）
- 多按键状态机控制
- 电机、电磁铁、触碰开关组合的发射机构控制

### 编译模式切换

通过 [`main.h`](AT32Gcc/Inc/control/main.h) 中的宏定义切换编译模式：

| 宏 | 用途 |
|----|------|
| `#define GCC_CODE` | **用户 GCC 编译模式**（当前启用） |
| `#define GUI_CODE` | 界面操作模式 |
| `#define BOOT_CODE` | BootLoader 模式 |

---

## 五、SDK 层功能模块一览

> 📁 头文件目录：[`AT32Gcc/Inc/control/`](AT32Gcc/Inc/control/)
> 📁 编译产物目录：[`AT32Gcc/Debug/Src/control/`](AT32Gcc/Debug/Src/control/)

通过 `main.h` 的 include 树，可还原完整 SDK 功能：

### 5.1 通用模块（BOOT/GUI/GCC 共用）

| 模块文件 | 功能 |
|----------|------|
| [`program_run.h`](AT32Gcc/Inc/control/program_run.h) | 程序跳转（BOOT→GUI→GCC→USBMass）、系统复位 |
| [`power_key.h`](AT32Gcc/Inc/control/power_key.h) | 电源按键管理 |
| [`uart_pc.h`](AT32Gcc/Inc/control/uart_pc.h) | USB 虚拟串口通信 |
| [`internal_flash.h`](AT32Gcc/Inc/control/internal_flash.h) | 内部 Flash 读写 |
| [`devicename.h`](AT32Gcc/Inc/control/devicename.h) | 硬件版本识别（跳线电阻） |
| [`systemtimer.h`](AT32Gcc/Inc/control/systemtimer.h) | SystemTick 定时器 |
| [`spi_lcd.h`](AT32Gcc/Inc/control/spi_lcd.h) / [`lcd.h`](AT32Gcc/Inc/control/lcd.h) | SPI 液晶屏 |
| [`spi_flash.h`](AT32Gcc/Inc/control/spi_flash.h) | 外部 SPI Flash |
| [`usb_vbus.h`](AT32Gcc/Inc/control/usb_vbus.h) | USB 插入检测 |
| [`led.h`](AT32Gcc/Inc/control/led.h) | 板载 LED |
| [`digoutput.h`](AT32Gcc/Inc/control/digoutput.h) | 数字输出端口 |

### 5.2 GCC/GUI 共用模块

| 分类 | 模块文件 | 功能 |
|------|----------|------|
| **运动** | [`port_motor.h`](AT32Gcc/Inc/control/port_motor.h) | 直流电机控制 |
| | [`port_485servo.h`](AT32Gcc/Inc/control/port_485servo.h) | 485 总线舵机 |
| | [`port_pwmservo.h`](AT32Gcc/Inc/control/port_pwmservo.h) | PWM 舵机 |
| **传感器** | [`port_AI.h`](AT32Gcc/Inc/control/port_AI.h) | 模拟输入端口 |
| | [`port_AI_sensor.h`](AT32Gcc/Inc/control/port_AI_sensor.h) | AI 端口传感器集合 |
| | [`port_i2c_sensor.h`](AT32Gcc/Inc/control/port_i2c_sensor.h) | I2C 传感器（颜色/手势/TOF） |
| | [`port_i2c_spl06.h`](AT32Gcc/Inc/control/port_i2c_spl06.h) | SPL06 气压传感器 |
| | [`port_uart_5gray.h`](AT32Gcc/Inc/control/port_uart_5gray.h) | 五灰度巡线传感器 |
| | [`mc602_sensor.h`](AT32Gcc/Inc/control/mc602_sensor.h) | 兼容传感器适配 |
| | [`mc602_mpu6500.h`](AT32Gcc/Inc/control/mc602_mpu6500.h) | MPU6500 陀螺仪 |
| **通信** | [`uart_p1.h`](AT32Gcc/Inc/control/uart_p1.h) / [`uart_p2.h`](AT32Gcc/Inc/control/uart_p2.h) | P1/P2 端口串口 |
| | [`uart_485.h`](AT32Gcc/Inc/control/uart_485.h) | 485 舵机总线 |
| | [`uart_bt.h`](AT32Gcc/Inc/control/uart_bt.h) | 蓝牙串口 |
| | [`uart_pi.h`](AT32Gcc/Inc/control/uart_pi.h) | Raspberry Pi 通信串口 |
| **外设** | [`port_i2c.h`](AT32Gcc/Inc/control/port_i2c.h) | I2C 总线 |
| | [`port_i2c_dot8x8.h`](AT32Gcc/Inc/control/port_i2c_dot8x8.h) | 8×8 LED 点阵 |
| | [`beep_wav.h`](AT32Gcc/Inc/control/beep_wav.h) | WAV 音频播放 |
| | [`beep_simple.h`](AT32Gcc/Inc/control/beep_simple.h) | 蜂鸣器音调 |
| **AI** | [`AI_Cam.h`](AT32Gcc/Inc/control/AI_Cam.h) | AI 摄像头（K210 模块） |
| **系统** | [`thread.h`](AT32Gcc/Inc/control/thread.h) | 多线程封装 |
| | [`battery.h`](AT32Gcc/Inc/control/battery.h) | 电池检测（2S/3S） |
| | [`mc602_runapp.h`](AT32Gcc/Inc/control/mc602_runapp.h) | 程序运行管理 |
| | [`port_math.h`](AT32Gcc/Inc/control/port_math.h) | 数学扩展函数 |
| | [`port_btremote.h`](AT32Gcc/Inc/control/port_btremote.h) | 蓝牙遥控协议 |

---

## 六、扩展库详解

### 6.1 巡线算法 — [`Goline.c`](AT32Gcc/Src/externlib/Goline.c) ([`.h`](AT32Gcc/Inc/externlib/Goline.h))

约 600 行的核心巡线算法，实现 **5 灰度传感器 PID 巡线**。

**API 流程**：
```
patr_init()                     → 初始化，从 EEPROM 读取黑白阈值
patr_environmental_acquiment()  → 交互式采集黑/白线数据
patr_road(intersection, spd, t)→ 路口巡线（左/T字/右）
patr_time(spd, t)              → 定时巡线
patr_turn(type, L_spd, R_spd)  → 定点转弯
patr_button()                  → 按钮启动等待
Zx(spd, direction)             → 单帧巡线控制
```

**算法特点**：
- 中间 3 路传感器（B2/B3/B4）计算百分比偏差
- 30+ 个分段线性控制区间，精细调节差速比
- 两侧传感器（A1/A5）检测路口
- `flag2` 状态机记录偏线方向，用于失线找回
- 支持**麦克纳姆轮**巡线模式

### 6.2 动作页播放 — [`play_page.c`](AT32Gcc/Src/externlib/play_page.c) ([`.h`](AT32Gcc/Inc/externlib/play_page.h))

机器人舞蹈/动作编排的**核心引擎**。

- 支持 **128 个动作页**，每个动作页最多 20 个舵机同时控制
- 每个动作页可定义：**下一页**（自动跳转）、**退出页**（退出时播放）、**重复次数**
- 10ms 定时器驱动（TIM5），实现平滑角度增量插值
- RS485 总线协议，批量同步舵机角度和速度
- 同时支持 **上位机 HID 调试协议**（实时舵机调试）

### 6.3 步进电机 — [`step_driver.c`](AT32Gcc/Src/externlib/step_driver.c) ([`.h`](AT32Gcc/Inc/externlib/step_driver.h))

- 485 总线控制步进电机驱动器（ID=100）
- 3 路独立控制（速度范围 ±50 ~ ±32000）
- **梯形加减速**算法（`accaplay` 函数）
- 编码器位置反馈读取
- 与舵机共用 485 总线，通过时序互斥避免冲突

---

## 七、Python 工具链

### 7.1 增量编译 — [`pymake.py`](pybuilder/pymake.py)

| 功能 | 说明 |
|------|------|
| **增量编译** | 仅编译 `Src/user/` + `Src/externlib/` 源文件 |
| **全编译**（`-all true`） | 编译所有模块（标准库+FreeRTOS+SDK） |
| **链接** | 自动扫描 `Debug/` 下所有 `.o`，生成 `objects.list` |
| **输出** | `AT32Gcc.elf` → `Run.bin` + 固件大小信息 |
| **编译选项** | `-mcpu=cortex-m3 -std=gnu11 -Ofast -g3 -DDEBUG` |

### 7.2 串口下载 — [`pydownload.py`](pybuilder/pydownload.py)

完整的 **BootLoader 协议**实现，通过 USB 虚拟串口（1Mbps）与控制器通信。

```
┌──────────┐  USB 虚拟串口  1Mbps  ┌──────────────┐
│   PC     │ ◄══════════════════► │  MC602P       │
│ pydownload.py  │                │  BootLoader   │
└──────────┘                      └──────────────┘
```

**协议帧格式**（参考 [`pydownload.py`](pybuilder/pydownload.py) 中 `CMD_PC_2_M32_HEAD0/1`）：
```
[0x55] [0xAA] [Seq] [Cmd] [LenL] [LenH] [Data...] [~Checksum]
```

**核心命令**：

| 命令 | 值 | 功能 |
|------|----|------|
| `CMD_PING` | `0x01` | 检测控制器，返回型号 |
| `CMD_WRITEBUFFER` | `0x10` | 发送 4KB 代码到 RAM 缓冲 |
| `CMD_RAM2FLASH` | `0x20` | 将 4KB 缓冲烧录到 Flash |
| `CMD_CRC` | `0x50` | CRC32 校验（断点续传） |
| `CMD_SAVEFILENAME` | `0x30` | 保存程序名 |
| `CMD_RUNCODE` | `0x40` | 跳转运行指定地址程序 |

**智能下载特性**：
- 下载前 CRC32 校验，已存在的块自动跳过
- 自动识别 CH340 USB 转串口（PID=29987, VID=6790）
- 失败自动重试 5 次

### 7.3 API 定义 — [`whalesbot.py`](python/whalesbot.py)

Scratch 图形化编程对应的 **完整 Python API 定义**（150+ 函数），包含：

| 分类 | 数量 | 示例 |
|------|------|------|
| 运动控制 | 30+ | `set_motor`, `move`, `set_servo_angle`, `mecanum_wheel_ctrl` |
| 声光显示 | 25+ | `play_sound`, `display_emotion`, `set_RGB`, `buzzer_note` |
| 传感器 | 30+ | `get_infrared_distance`, `color_value`, `gyroscope`, `get_tof` |
| AI 功能 | 15+ | `get_AI_image`, `get_AI_voice`, `AI_read_value`, `Init_lane` |
| 巡线 | 15+ | `patrol_road`, `patrol_time`, `patrol_turn` |
| 数学 | 15+ | `random_number`, `math_sin`, `math_abs` |
| 逻辑/存储 | 10+ | `read_EEPROM`, `write_EEPROM`, `get_digital_input` |

所有常量定义在同文件中：端口 P1~P12、舵机 S1~S18、颜色、音符、AI 图像 ID、LED 表情/符号等。

---

## 八、构建 & 下载流程

```
开发者编写 user_main.c
        │
        ▼
┌──────────────────────────────────────────┐
│         pymake.py  build()               │
│                                          │
│  1. 增量编译 user/*.c + externlib/*.c    │
│     → .o 文件输出到 Debug/Src/           │
│  2. 扫描 Debug/ 下所有 .o（含 SDK）      │
│     → 生成 objects.list                 │
│  3. arm-none-eabi-gcc 链接              │
│     → AT32Gcc.elf                       │
│  4. arm-none-eabi-objcopy               │
│     → Run.bin                           │
└──────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│       pydownload.py  Scratch_Download()  │
│                                          │
│  1. 扫描 COM 口（匹配 PID/VID）          │
│  2. Ping → 进入 BootLoader               │
│  3. 4KB 分块下载（CRC32 断点续传）       │
│  4. 保存程序名到 Flash                   │
│  5. 跳转运行用户程序                     │
└──────────────────────────────────────────┘
```

---

## 九、固件版本历史

| 日期 | 版本 | 关键改动 |
|------|------|---------|
| 2024-06-06 | V100→V101 | 灯带修复、舵机通道修复、902 舵机兼容、2S/3S 电池切换、开机自动运行、LOGO 更换 |
| 2024-11-05 | | 颜色传感器端口总是 P1 的 BUG 修复 |
| 2025-03-05 | | 巡线检测存储 BUG 修复、P5/P6 五灰度自动识别、电机保护逻辑优化 |
| 2025-04-07 | | 大容量版本、电机反向保护解除、步进电机 485 冲突解决 |
| 2025-05-19 | | AI 摄像头左掉头编译错误修复 |
| 2025-07-16 | **V102** | K210 全功能固件对接、步进+舵机同时使用优化、点读笔支持、二维码扫描、驱动卡超时保护 |
| 当前 | V102 | 定义于 [`main.h`](AT32Gcc/Inc/control/main.h) 行 47 |

---

## 十、快速开始

### 修改用户代码

编辑 **[`AT32Gcc/Src/user/user_main.c`](AT32Gcc/Src/user/user_main.c)**，在 `user_main()` 函数中编写你的机器人逻辑。

所有 API 声明通过 [`whalesbot.h`](AT32Gcc/Inc/user/whalesbot.h) → [`main.h`](AT32Gcc/Inc/control/main.h) 引入。

### 高级定制（可选）

如需修改巡线、动作页、步进电机等算法，可编辑 [`AT32Gcc/Src/externlib/`](AT32Gcc/Src/externlib/) 下的对应 `.c` 文件。

### 编译 & 下载

通过 Scratch IDE 一键完成，或命令行手动执行：

```bash
# 编译
python pybuilder/pymake.py

# 全量重编译（包括标准库 + SDK）
python pybuilder/pymake.py -all true

# 下载并运行（RunA 槽位）
python pybuilder/pydownload.py -file "AT32Gcc/Debug/Run.bin" -address 0x0800D000 -run true
```

---

## 十一、关键文件索引

| 文件 | 角色 | 可修改 |
|------|------|:---:|
| [`user_main.c`](AT32Gcc/Src/user/user_main.c) | 用户程序入口 | ✅ |
| [`Goline.c`](AT32Gcc/Src/externlib/Goline.c) | 巡线算法实现 | ✅ |
| [`play_page.c`](AT32Gcc/Src/externlib/play_page.c) | 动作页播放引擎 | ✅ |
| [`step_driver.c`](AT32Gcc/Src/externlib/step_driver.c) | 步进电机驱动 | ✅ |
| [`main.h`](AT32Gcc/Inc/control/main.h) | 编译配置 & 版本定义 | ⚠️ |
| [`stm32_flash.ld`](AT32Gcc/linkscript/stm32_flash.ld) | 内存布局定义 | ⚠️ |
| [`pymake.py`](pybuilder/pymake.py) | 编译系统 | ⚠️ |
| [`pydownload.py`](pybuilder/pydownload.py) | 下载协议 | ⚠️ |
| [`whalesbot.py`](python/whalesbot.py) | Scratch API 定义 | ⚠️ |
| `Src/control/*.o` | SDK 闭源驱动库 | ❌ |

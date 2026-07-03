# firmware/ — MC602P 下位机 C 固件

> 6 层分层架构的 MCU 端实现
>
> 详细架构说明：[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)

---

## 1. 硬件

| 项目 | 值 |
|------|-----|
| 板子 | MC602 MC602P (3S 锂电池, 11.5V) |
| MCU | STM32F103ZE / AT32F403 (Cortex-M3, 168MHz) |
| Flash | 512KB |
| RAM | 94KB |
| USB | CH340 (VID=0x1A86, PID=0x7523) |
| LCD | 160x80 彩色 SPI LCD, 字符 8x16 |

> 板子**无绿色 LED**（`LED_G` 引脚 PD7 无效）。状态显示走 LCD 或 USB 串口。

---

## 2. 目录结构（6 层映射）

```
firmware/
├── app/                         # Layer 6 入口
│   └── user_main.c              # ★ 用户程序入口
│
├── core/                        # Layer 4: Dispatcher
│   ├── dispatcher.c             # 协议引擎（按 svc+inst 路由）
│   └── dispatcher.h
│
├── devices/                     # Layer 5+6: Device Manager + Device 业务
│   ├── services.{c,h}           # Service 注册表（Motor + System handler）
│   ├── motor_pid.{c,h}          # 独立 PID 控制器（Controller 类）
│   ├── system_monitor.{c,h}     # System Service（电压/版本/看门狗/健康）
│   ├── device_manager.{c,h}     # TODO: DeviceManager 抽象
│   ├── motor.{c,h}              # TODO: Motor 业务（含 Driver/Filter/Homing/Safety）
│   └── bsp/                     # TODO: Driver 抽象层（包闭源 SDK）
│       ├── driver_motor.{c,h}
│       └── driver_power.{c,h}
│
├── protocol/                    # Layer 3: Packet（COBS + CRC8）
│   ├── cobs.{c,h}
│   └── crc8.{c,h}
│
├── tools/                       # 编译/烧录
│   ├── build_firmware.py        # ★ 编译脚本
│   └── pydownload.py            # ★ 烧录脚本（用 PING 触发 NVIC_SystemReset）
│
├── build/                       # 编译产物（gitignore）
│   ├── Run.bin                  # ★ 烧录文件 (~67KB)
│   ├── AT32Gcc.elf
│   ├── AT32Gcc.map
│   └── obj/
│
└── README.md                    # 本文件
```

**6 层对应**：

| 6 层规范 | 路径 |
|----------|------|
| Layer 1: Python SDK | `../host/mc602/devices/` |
| Layer 2: Transport | (闭源 SDK `UartPC_Sendbytes` + pyserial) |
| Layer 3: Packet | `protocol/cobs.{c,h}` + `protocol/crc8.{c,h}` |
| Layer 4: Dispatcher | `core/dispatcher.{c,h}` |
| Layer 5: DeviceManager | `devices/device_manager.{c,h}` (TODO) |
| Layer 6: Device | `devices/{motor_pid,services,system_monitor}.{c,h}` |

---

## 3. 工具链

### 3.1 ARM GCC 工具链

```
C:\Users\young\Desktop\whalesbot\new_whalesbot\AI_Module_GCC\arm_gcc_10\bin\
```

如路径变更，编辑 `tools/build_firmware.py` 顶部的 `TOOLCHAIN_DIR`。

### 3.2 闭源 SDK 位置

`AT32Gcc/Debug/` 下有 85+ 预编译的 .o 文件：
- `Src/control/*.o` — 闭源 SDK（电机/舵机/IO/I2C/SPI/AI/AI摄像头...）
- `Src/externlib/*.o` — 已有扩展库
- `STM32_Stdlib/STM32F10x_StdPeriph_Driver/src/*.o` — 标准外设库
- `STM32_Stdlib/FreeRTOS/src/*.o` — FreeRTOS
- `Startup/startup_stm32f10x_hd.o` — 启动文件

**绝对不要修改这些 .o**。新功能写在 `devices/` 或 `app/`。

---

## 4. 编译 & 烧录

### 4.1 编译

```bash
cd C:/Users/young/Documents/projects/MC_602P/firmware
python tools/build_firmware.py           # 只编译
python tools/build_firmware.py --deploy  # 编译 + 部署到 mc602sdk/Run.bin
python tools/build_firmware.py --clean   # 清理后重新编译
```

输出：
- `build/Run.bin` — 烧录文件
- `--deploy` 会额外复制到 `../mc602sdk/Run.bin`
- text/data/bss 大小

> 100KB slot 当前用 **~67KB (66%)**，剩余 33KB。**我们的代码只占 4-5KB**，剩下是 SDK 闭源库。

### 4.2 烧录 (推荐)

```bash
# 1) 编译 + 部署 (把 Run.bin 复制到 mc602/tools/flash/)
python tools/build_firmware.py --deploy

# 2) 烧录
python mc602/tools/flash/flash.py

# 或合成一步: 重新编译 + 烧录
python mc602/tools/flash/flash.py --rebuild
```

`mc602/tools/flash/` 是**自包含的烧录包**（含 Run.bin + flash.py + pydownload.py），可以独立打包分发。

### 4.3 烧录 (备选 - 手动)

如果不想用 `mc602/tools/flash/flash.py`，可以直接调 `firmware/tools/pydownload.py`：

```bash
python firmware/tools/pydownload.py \
    -file firmware/build/Run.bin \
    -address 0x800D000
```

完整烧录/状态机说明：[docs/FIRMWARE.md §1-5](../docs/FIRMWARE.md)

---

## 5. 协议（Layer 3 + Layer 4）

### 5.1 物理层

| 项 | 值 |
|---|---|
| 串口 | USART1 (PA9=TX, PA10=RX) |
| 波特率 | 1,000,000 (1 Mbps) |
| 字节序 | 小端 |
| USB 转串口 | CH340 |

### 5.2 帧格式

```
[COBS(payload)] [0x00 DELIM] [CRC8(payload)]

payload:
  [seq:u8] [op:u8] [svc:u8] [inst:u8] [prop:u8] [value...]
```

### 5.3 Service ID

| Service | ID | 文件 | 状态 |
|---------|----|------|------|
| System | 0xFE | `devices/system_monitor.c` | ✅ 已实现 |
| Motor | 0x01 | `devices/services.c::motor_handler` | ✅ 已实现 |
| ServoBus | 0x20 | — | ❌ TODO |
| Stepper | 0x30 | — | ❌ TODO |
| Sensor (ToF/Color/IMU) | 0x40+ | — | ❌ TODO |

完整协议参考：[docs/FIRMWARE.md §2](../docs/FIRMWARE.md)

---

## 6. LCD 屏幕布局

5 行，1-indexed（`show(0)` 写到屏外！）

```
┌────────────────────┐  ← 20 字符宽
│MC602P smartcar    │  show(1)  标题（固定）
│------------------│  show(2)  18 横线分隔
│V:11.50V bat:69%  │  show(3)  电压/电量（500ms 刷新）
│beat:O count:5     │  show(4)  心跳动画（2Hz 切换）
│free:31928B        │  show(5)  空闲堆
└────────────────────┘
```

每 500ms 整页重画 + `LCD_Ram2LCD()`。

---

## 7. 已实现的 Service

### 7.1 System Service (svc=0xFE)

| Prop | 访问 | 类型 | 含义 |
|------|------|------|------|
| 0x01 voltage | r | u16 mV | 电池电压 |
| 0x02 version | r | str | 固件版本 |
| 0x03 uptime | r | u32 s | 启动后秒数 |
| 0x04 watchdog | rw | u16 ms | 看门狗超时（0=禁用） |
| 0x80 reboot (CALL) | - | - | 跳到 BootLoader |
| 0x81 bootloader (CALL) | - | - | 跳到 GUI |

### 7.2 Motor Service (svc=0x01)

| Prop | 访问 | 类型 | 含义 |
|------|------|------|------|
| 0x01 speed | rw | i8 | 目标速度 (-100~100) |
| 0x02 encoder | r | i32 | 编码器脉冲累计 |
| 0x03 current | r | u16 | 电流 mA（占位返回 0） |
| 0x04 status | r | u8 | 0=停止 1=运行 2=堵转 3=PID到位 4=超时 |
| 0x05~0x07 pid_kp/ki/kd | rw | u16 ×1000 | PID 参数 |
| 0x08 control_mode | rw | u8 | 0=开环 1=PID速度 2=PID位置 |
| 0x09 target_position | rw | i32 | 位置模式目标 |
| 0x80 stop (CALL) | - | - | 停电机 |
| 0x81 reset_encoder (CALL) | - | - | 复位编码器 |
| 0x82 move_to (CALL) | - | - | 位置闭环 (i32 pos + u8 max_speed) |

---

## 8. ⚠️ 已踩过的坑（MCU 端）

### 8.1 SDK 的 `show()` 是 **1-indexed**

```c
show(0, "title");  // ❌ 写到屏外，看不到
show(1, "title");  // ✓ 第 1 行
```

### 8.2 `LCD_ClearBufferLine(N)` 有 bug

`ClearBufferLine(3)` 可能清了第 4 行。**不要用**。
**正确做法**：`show(N, "...")` 直接覆盖即可。

### 8.3 `printf()` 在 SDK 里走 LCD，**不走 UART**

```c
printf("hello");  // ❌ 出现在 LCD，不是终端！
```

要走 UART，用 `UartPC_Sendbytes(buf, len)` 封装成 `uart_print()`。

### 8.4 心跳 callback **不能写 UART**

历史教训：心跳 callback 调 `UartPC_Sendbytes()` 推心跳文本 → 与协议响应帧抢同一 TX buffer → 响应被截断 → PC 端 CRC 错。

**规则**：心跳 callback 只更新内部 counter。系统状态由 PC 端 `bot.system.*` 主动 poll。

### 8.5 3S 锂电池电压范围

- 满电：12.6V
- 放空：9.0V（实际 8.4V 还能工作，建议放空阈值降到 8.4V）

### 8.6 主循环被堵住时 LCD 不会动

`uart_print` 正常（心跳线程独立）但 LCD 卡住 → **主循环没跑**。
诊断：在 `while(1)` 开头加 `uart_print("[loop] iter=%u", ...)`。

---

## 9. TODO

### P0: 6 层架构补完（[ARCHITECTURE.md §4](../docs/ARCHITECTURE.md)）

- [ ] Layer 5: `devices/device_manager.{c,h}` — DeviceManager 抽象
- [ ] Layer 6: `devices/motor.{c,h}` — Motor 业务从 `services.c::motor_handler` 抽出
- [ ] Layer 6: `devices/bsp/driver_motor.{c,h}` — Driver 抽象（包 set_motor 闭源 SDK）
- [ ] Layer 6: `devices/bsp/driver_power.{c,h}` — Driver 抽象（包 getBatt_AVG）
- [ ] Filter / Homing / Safety 子组件

### P1: 加新 Service

- [ ] Servo (0x20) — 总线舵机（RS485）
- [ ] Stepper (0x30) — 步进电机
- [ ] Sensor (0x40+) — ToF / 颜色 / IMU

### P2: 应用层

- [ ] 麦轮车世界坐标系
- [ ] 路径跟踪 PID
- [ ] 避障（融合 ToF + IMU）

---

## 10. 快速命令

```bash
# 编译
cd C:/Users/young/Documents/projects/MC_602P/firmware
python tools/build_firmware.py

# 烧录 + 运行
cp build/Run.bin ~/Desktop/whalesbot/new_whalesbot/AI_Module_GCC/MC_602P/AT32Gcc/Debug/
cd ~/Desktop/whalesbot/new_whalesbot/AI_Module_GCC/MC_602P
python pybuilder/pydownload.py -file "AT32Gcc/Debug/Run.bin" -address 0x800D000
```

---

**最后更新**: 2026-07-03
**固件版本**: V102
**当前状态**: System + Motor Service 完成；6 层架构 L5/L6 部分实现（待补完）

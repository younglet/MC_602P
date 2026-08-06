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
cd C:/Users/young/Documents/projects/mc602p-firmware/firmware
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
| Stepper | 0x30 | `devices/services.c::stepper_handler` (SDK `step_driver.c`) | ✅ 已实现 |
| ServoBus | 0x20 | `devices/services.c::servobus_handler` (485, 经 step_driver) | ✅ 已实现 |
| ServoPWM | 0x21 | `devices/services.c::servopwm_handler` (P7~P13) | ✅ 已实现 |
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

### 7.3 Stepper Service (svc=0x30)

底层为 SDK `step_driver.c` (自带 100Hz 加减速线程, 3 通道 485 总线)。
`inst` = 通道 (1~3, 即 `STP_MOT_CH1~3`)。

| Prop | 访问 | 类型 | 含义 |
|------|------|------|------|
| 0x01 speed | rw | i16 | 目标速度 (-32000~32000, \|v\|<50 视为 0) |
| 0x02 distance | r | i32 | 驱动器反馈累计脉冲 |
| 0x03 acc | rw | u16 | 加减速 (0~32000, 默认 1000) |
| 0x80 stop (CALL) | - | - | 速度置 0 (保持力矩) |
| 0x81 reset (CALL) | - | - | 复位/释放 (阻塞 ~100ms) |

> ⚠️ reset 在协议线程内忙等 100ms, 期间响应延迟, 上位机自动重试兜底。
> 速度/acc 的 GET 返回固件侧最近一次 SET 记录 (SDK 无 getter)。

### 7.4 ServoBus Service (svc=0x20) — 485 总线舵机

底层经 SDK `step_driver.c` 的 `set_step_servoa()` 发送 (与步进电机共用 485 总线,
由 StepMotorThread 统一仲裁, 官方共存方案)。`inst` = 舵机 ID (S1~S18)。

| Prop/命令 | 访问 | 类型 | 含义 |
|------|------|------|------|
| 0x01 angle | r | i16 | 最近一次目标角度 (-150~150) |
| 0x80 set_angle (CALL) | - | - | [i16 angle][u8 speed] 阻塞 ≤10ms |

> ⚠️ 其余 485 舵机 API (set_servo_angle/读角度/力矩) 会抢占
> `setUartPort485_RxHandle` 与步进线程冲突, 不启用。首次调用会触发
> 步进线程启动 (set_stepmotor 速度 0, 不影响电机)。

### 7.5 ServoPWM Service (svc=0x21) — PWM 舵机

底层 SDK `SetServo()` (独立定时器, 与步进/485 无冲突)。
`inst` = 1~7 → D1~D7 (P7~P13)。

| Prop/命令 | 访问 | 类型 | 含义 |
|------|------|------|------|
| 0x01 angle | r | i16 | 最近一次目标角度 (0~180) |
| 0x80 set_angle (CALL) | - | - | [u16 angle][u8 speed(10~100)] |

> 初始化: `rx_process_start` 调 `ServoInit()` + `SERVO_PWR_ON()`。

---

### 7.6 Chassis Service (svc=0x04) — 麦轮底盘 (外环 + 车身速度环)

200Hz 控制环: 读 4 编码器 → 增量里程计 → (GOTO: 极坐标 P) → **车身速度环**
→ 逆运动学 → `set_motor` ×4。几何/控制参数由 host 推送或使用默认值。

| Prop | 访问 | 含义 |
|------|------|------|
| 0x01 pose | r | 位姿 x/y (cm×100) + θ (rad×1000) |
| 0x02 status | r | 状态机 (IDLE/RUNNING/ARRIVED/...) |
| 0x03 twist | r | 目标车身速度 |
| 0x06 stats | r | 总里程/到达次数/运行秒数 |
| 0x10 geometry | rw | 几何 (track/base/radius/ppr/roller) |
| 0x20~0x25 | rw | GOTO 极坐标 P/KI 参数 |
| 0x26~0x30 | rw | 容差 / 速度上限 / 超时 |
| 0x38~0x40 | rw | 速度环三轴 Kp/Ki/Kd (×1000) |
| 0x41/0x42 | rw | 速度环输出限幅 (±cm/s, ±deg/s) |

**车身速度环** (pid_x/pid_y/pid_yaw, 参考 cfg_vehicle.yaml):
编码器差分 → 前向运动学 → 实测车身速度 → PID → 限幅 → 逆运动学。
默认参数 Kp/Ki/Kd = 6/0.3/0.1 (X), 8/0.3/0.1 (Y), 10/0.2/0.1 (W),
输出限幅 ±60 cm/s / ±86°/s; 速度上限默认 70 cm/s / 172°/s (0.7m/s, 3rad/s)。
**三轴系数全 0 = 旁路**, 等效旧版开环透传。

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

- [x] Servo (0x20) — 总线舵机（RS485, 经 step_driver 共存）✅
- [x] ServoPWM (0x21) — PWM 舵机 (P7~P13) ✅
- [x] Stepper (0x30) — 步进电机 ✅ (SDK step_driver)
- [ ] Sensor (0x40+) — ToF / 颜色 / IMU

> 注意: 步进与 485 舵机共用总线 + 单 RX 回调。`setUartPort485_RxHandle`
> 每 10ms 被 StepMotorThread 重新注册。若需独立 485 舵机 API
> (读角度/力矩/旋转模式), 需统一总线仲裁 (即 build 注释里缺失的
> "新版 step_driver / servo_bus_* API")。

### P2: 应用层

- [ ] 麦轮车世界坐标系
- [ ] 路径跟踪 PID
- [ ] 避障（融合 ToF + IMU）

---

## 10. 快速命令

```bash
# 编译
cd C:/Users/young/Documents/projects/mc602p-firmware/firmware
python tools/build_firmware.py

# 烧录 + 运行
cp build/Run.bin ~/Desktop/whalesbot/new_whalesbot/AI_Module_GCC/mc602p-firmware/AT32Gcc/Debug/
cd ~/Desktop/whalesbot/new_whalesbot/AI_Module_GCC/mc602p-firmware
python pybuilder/pydownload.py -file "AT32Gcc/Debug/Run.bin" -address 0x800D000
```

---

**最后更新**: 2026-07-03
**固件版本**: V102
**当前状态**: System + Motor Service 完成；6 层架构 L5/L6 部分实现（待补完）

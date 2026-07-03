# mc602 — MC602P 机器人控制器 Python SDK + 烧录工具

> **面向对象 per-instance API** + **二进制 RPC 协议** + **一键烧录工具**
>
> 一站式发布包：拿到这一份就能控制 MC602P / 烧录固件

---

## 这是什么

`mc602` 是 MC602 MC602P 控制器（STM32F103ZE / AT32F403, Cortex-M3, FreeRTOS）的上位机 Python 包。

包含 3 部分：

| 部分 | 路径 | 用途 |
|------|------|------|
| **Python SDK** | `mc602/` | 写 Python 代码控制 MC602P |
| **烧录工具** | `tools/` | 把固件烧进 MC602P |
| **预编译固件** | `tools/Run.bin` | 最新可用固件（已含 System + Motor Service） |

---

## 快速开始

### 1. 烧录固件（首次使用必做）

把 MC602P 用 USB 接到 PC，然后：

```bash
# 标准: 烧录本包自带的 Run.bin
python tools/flash.py

# 或烧到指定槽 (RunA~RunF)
python tools/flash.py --address 0x08060000   # RunA
python tools/flash.py --address 0x08099000   # RunC
```

PING 慢帧会自动触发旧固件复位，**不需要按按钮**。

### 2. 用 Python 控制 MC602P

```python
from mc602 import Robot

with Robot.connect() as robot:
    # 速度闭环
    robot.motor(1).set_speed(50)

    # 读编码器
    pos = robot.motor(1).encoder

    # 位置闭环（链式）
    robot.motor(1).move_to(3000).wait()

    # 调 PID
    robot.motor(1).pid.kp = 0.25

    # 系统信息
    print(robot.system.voltage, robot.system.version)
```

### 3. 编译新固件（可选）

如果你要改固件逻辑，**完整源码在另一个仓库**（不在本包里）。本包只含**预编译**的 `Run.bin`。

开发流程：
```bash
# 在有源码的机器上:
cd /path/to/MC_602P/firmware
python tools/build_firmware.py --deploy
# ↑ 这会把新的 Run.bin 部署到 mc602/tools/flash/Run.bin
# 然后把这个 Run.bin 拷到本包, 走 Step 1 烧录
```

---

## 目录结构

```
mc602/                       ← 你正在读这个文件
├── __init__.py              ← 顶层导出 (Robot, Motor, System, MC602, ...)
├── comm/                    ← Layer 2+3: 通讯子模块
│   ├── client.py            ← Layer 2: MC602 串口客户端
│   ├── packet.py            ← Layer 3: Payload, Op, Status, 帧编/解码
│   ├── cobs.py              ← COBS 编码
│   └── crc8.py              ← CRC-8 校验
│   └── exceptions.py        ← 异常体系 (MC602Error, ConnectionError, ...)
├── robot.py                 ← Layer 1: Robot 顶层门面
├── devices/                 ← Layer 1: per-instance 面向对象设备
│   ├── __init__.py
│   ├── motor.py             ← Motor(port) + MotorPID + MoveToFuture
│   ├── system.py            ← System 单例
│   └── constants.py         ← M1-M6, P1-P13, S1-S18, 颜色, 方向...
├── services/                ← Layer 1.5: 薄 RPC 包装
│   ├── __init__.py
│   ├── motor.py             ← MotorService (对应下位机 motor_handler)
│   └── system.py            ← SystemService (对应下位机 system_handler)
│
└── tools/                   ← 烧录工具包
    └── flash/               ← 烧录子模块
        ├── flash.py         ← 一键烧录入口
        ├── pydownload.py    ← BootLoader 协议实现
        ├── Run.bin          ← 最新预编译固件
        └── README.md        ← tools 详细说明
```

---

## API 速查

### per-instance 风格（推荐）

```python
motor = robot.motor(1)
motor.set_speed(50)              # 速度 (-100~100)
motor.encoder                    # 读编码器
motor.reset_encoder()            # 复位
motor.pid.kp = 0.25              # 调 PID
motor.pid.ki = 0.001
motor.pid.kd = 0.004
motor.move_to(3000).wait()       # 位置闭环
motor.stop()
motor.is_running                 # bool
motor.status                     # 0=停 1=运 2=堵 3=到位 4=超时
```

### Service 风格（兼容）

```python
bot.motor.set_speed(M1, 50)
bot.motor.get_encoder(M1)
bot.system.voltage               # V
bot.system.version               # str
bot.system.uptime                # s
```

### 错误处理

```python
from mc602 import (
    SerialNotFoundError,   # CH340 没找到
    ConnectionError,       # 串口打开失败
    ProtocolError,         # MCU 返回错误状态
    TimeoutError,          # 等响应超时
)

try:
    with Robot.connect() as robot:
        robot.motor(1).set_speed(50)
except SerialNotFoundError as e:
    print("CH340 没接上:", e)
```

---

## 通信参数

| 项 | 值 |
|---|---|
| 串口 | USART1 → CH340 → USB |
| 波特率 | 1,000,000 (1 Mbps) |
| 字节序 | 小端 |
| VID/PID | 0x1A86 / 0x7523 (CH340) |
| 协议 | COBS + CRC-8/MAXIM + Service/Property |

---

## 烧录工具

详见 [`tools/flash/README.md`](tools/flash/README.md)。

**3 个用法**：
```bash
python tools/flash/flash.py                    # 烧录 tools/flash/Run.bin
python tools/flash/flash.py --rebuild          # 编译 + 烧录 (需完整源码)
python tools/flash/flash.py --bin x.bin        # 烧自定义固件
```

---

## 系统要求

- Python 3.8+
- `pyserial`
- Windows / Linux / macOS（CH340 驱动需自装）
- USB 串口（CH340 在大多数系统免驱）

安装依赖：
```bash
pip install pyserial
```

---

## 协议层

详见 `mc602/comm/` 和下位机 `firmware/protocol/`、`firmware/core/dispatcher.c`。

帧格式：
```
[COBS(payload)] [0x00] [CRC8(payload)]

payload = [seq:u8] [op:u8] [svc:u8] [inst:u8] [prop:u8] [value...]
```

---

## 架构（6 层）

| Layer | PC 端 | MCU 端 | 状态 |
|-------|-------|--------|------|
| 1. Python SDK | `mc602/devices/` | — | ✅ |
| 2. Transport | `mc602/comm/client.py` | 闭源 SDK | ✅ |
| 3. Packet | `mc602/comm/{packet,cobs,crc8}.py` | `firmware/protocol/` | ✅ |
| 4. Dispatcher | (内置) | `firmware/core/dispatcher.c` | ✅ |
| 5. DeviceManager | (内置) | ⚠️ TODO | 🟡 |
| 6. Device | `mc602/services/` | ⚠️ TODO | 🟡 |

详细：[完整架构文档（需访问源码仓库）]

---

## 故障排查

| 症状 | 原因 | 解决 |
|------|------|------|
| `SerialNotFoundError: 找不到 CH340` | 驱动没装/USB 没插 | 装 CH340 驱动 / 换口 |
| `TimeoutError: DISCOVER 超时` | 固件没起来/不是我们协议 | 重烧 + 等 3s |
| 烧录后连不上 | 固件 hang | 等 3s，重烧 |
| `ProtocolError: NOT_FOUND` | 属性/命令 ID 错 | 查 `PROP_*` 常量 |
| 电机不转 | `set_speed(0)` 默认停 | `set_speed(±1)` 起动 |

---

## 版本

| 版本 | 日期 | 改动 |
|------|------|------|
| 0.2.0 | 2026-07-03 | 加 per-instance OOP (Motor/System/Robot) + tools/ 一键烧录 |

---

**最后更新**: 2026-07-03
**适用硬件**: MC602 MC602P
**Python**: 3.8+
**依赖**: pyserial

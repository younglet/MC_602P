# mc602p-firmware 架构规范

> 6 层分层架构：Python SDK (OOP) → Transport → Packet → Dispatcher → DeviceManager → Device
>
> 适用于 10-20 个硬件的中小型机器人 / 桌面设备控制框架

---

## 0. 设计原则

| 原则 | 含义 |
|------|------|
| **一个资源 = 一个写线程** | UART 只由协议层写；硬件只由硬件层调 SDK |
| **共享 = mutex** | 跨线程数据通过 mutex 保护的共享结构交换 |
| **状态 = 单一来源** | 所有硬件状态在 `SharedState`，协议层不知硬件细节 |
| **拉模式优先** | PC 主动 poll，不推心跳（避免 UART 抢锁） |
| **无 busy-wait** | 线程全用 `wait()`，给 FreeRTOS 调度权 |
| **业务与协议解耦** | Dispatcher 永远不知道 PWM/PID/GPIO |

---

## 1. 全局架构图

```
                  ┌────────────────────────────┐
                  │   Python SDK (Layer 1)     │  host/mc602/
                  │   Motor(1).set_speed(300)  │
                  └─────────────┬──────────────┘
                                │ API 调用 (对象方法)
                                ▼
                  ┌────────────────────────────┐
                  │   Transport (Layer 2)      │  host/mc602/device.py
                  │   UART / USB / CAN / TCP   │  (pyserial)
                  └─────────────┬──────────────┘
                                │ Binary RPC (COBS+CRC8)
                                ▼
══════════════════ 下位机 ══════════════════════════

  Layer 3: Packet          firmware/protocol/      cobs.{c,h} crc8.{c,h}
       │
       ▼
  Layer 4: Dispatcher      firmware/core/          dispatcher.{c,h}
       │  (按 Service ID + Inst 路由)
       ▼
  Layer 5: DeviceManager    firmware/devices/       device_manager.{c,h}  ← TODO
       │  (持 motors[6], servos[18]...)
       ▼
  Layer 6: Device          firmware/devices/       motor.{c,h} services.{c,h} system_monitor.{c,h}
       │  (Driver + Controller + Filter + Safety + Homing)
       ▼
    Hardware
```

---

## 2. 数据流示例：`robot.motor(1).home()`

```
Python (Host)
   │
   ▼
Motor.home()                          ← Layer 1 (host/mc602/devices/motor.py)
   │
   ▼
MotorService.call(home)               ← Layer 1.5 (host/mc602/services/motor.py)
   │
   ▼
MC602._request(Op.CALL, ...)      ← Layer 2 (host/mc602/device.py)
   │
   ▼
encode_frame()                        ← Layer 3 (host/mc602/protocol.py)
   │  COBS + 0x00 + CRC8
   ▼
Transport.send() (UART)               ← Layer 2 (pyserial)
   │
═══════ USB ════════════════════════════════════════
   │
   ▼
UART RX 中断                          ← firmware/protocol/cobs.c
   │
   ▼
Packet Parser (COBS decode + CRC check)
   │
   ▼
Dispatcher                            ← firmware/core/dispatcher.c
   │  (按 svc_id + inst 找 handler)
   ▼
DeviceManager.getMotor(1)             ← firmware/devices/device_manager.c (TODO)
   │
   ▼
Motor.home()                          ← firmware/devices/motor.c
   │
   ├─ Controller (PID 闭环)
   ├─ Filter (低通/中值)
   ├─ Safety (堵转/超时/低电压)
   └─ Driver                            ← firmware/devices/bsp/driver_motor.c (TODO)
       │
       ▼
    set_motor(port, pwm)                ← 闭源 SDK (AT32Gcc/.o)
       │
       ▼
    PWM + DIR + Encoder
```

---

## 3. 6 层详解

### Layer 1: Python SDK（面向对象）

**职责**：用户面。所有 API 是 per-instance 对象方法。

**当前实现**：`host/mc602/`
```python
from mc602 import Robot

robot = Robot.connect()
with robot:
    robot.motor(1).set_speed(50)        # per-instance ✓
    robot.motor(2).pid.kp = 0.25        # PID 子对象 ✓
    robot.motor(1).move_to(3000).wait() # 链式 future ✓
    print(robot.system.voltage)
```

**约束**：
- ❌ 不发 GPIO / PWM 之类底层命令
- ❌ 不解析串口协议
- ✅ 所有方法转发到 `MotorService` / `SystemService`

---

### Layer 2: Transport

**职责**：字节收发，物理介质无关。

**当前实现**：`host/mc602/device.py` (pyserial) + `UartPC_Sendbytes` (闭源 SDK)

**支持的传输**：
- ✅ UART (CH340, 1Mbps)
- ⏳ USB CDC / CAN / TCP / BLE  — 预留接口

**API 约束**：
- `send(bytes)` / `recv(bytes)` 即可
- 换传输介质时，Layer 1 / 3 不改

---

### Layer 3: Packet（协议层）

**职责**：二进制帧编解码 + 校验。

**当前实现**：
- PC: `host/mc602/protocol.py` (cobs_encode / crc8 / Payload)
- MCU: `firmware/protocol/cobs.c` + `firmware/protocol/crc8.c`

**帧格式**：
```
[COBS(payload)] [0x00 DELIM] [CRC8(payload)]

payload:
  [seq:u8] [op:u8] [svc:u8] [inst:u8] [prop:u8] [value...]
```

**操作码**：
| Op | 值 | 含义 |
|----|----|------|
| DISCOVER | 0x00 | 枚举所有 service |
| GET | 0x01 | 读属性 |
| SET | 0x02 | 写属性 |
| NOTIFY | 0x03 | 主动推送（暂不用） |
| CALL | 0x04 | 调用命令 |
| ERROR | 0x7F | 错误响应 |

**状态码**：
| Status | 值 | 含义 |
|--------|----|------|
| OK | 0x00 | 成功 |
| NOT_FOUND | 0x01 | service / prop 不存在 |
| READ_ONLY | 0x02 | 写只读属性 |
| RANGE_ERR | 0x03 | 参数越界 |
| TIMEOUT | 0x04 | 超时 |
| HW_ERR | 0x05 | 硬件错误 |

---

### Layer 4: Command Dispatcher

**职责**：按 `svc_id + inst + op + prop` 路由到对应 device handler。

**当前实现**：`firmware/core/dispatcher.c`

**伪代码**：
```c
void dispatch(uint8_t op, uint8_t svc, uint8_t inst, uint8_t prop, ...) {
    Device* d = device_manager_get(svc, inst);  // Layer 5
    if (!d) return STATUS_NOT_FOUND;

    switch (op) {
        case OP_GET:    return d->get(prop, out, out_len);
        case OP_SET:    return d->set(prop, in, in_len);
        case OP_CALL:   return d->call(prop, in, in_len, out, out_len);
        default:        return STATUS_NOT_FOUND;
    }
}
```

**约束**：
- ❌ 不知道 PWM / PID / GPIO
- ❌ 不知道具体设备
- ✅ 只做"按 ID 查表 + 转 op"

---

### Layer 5: Device Manager

**职责**：统一管理所有设备实例。

**目标实现**：`firmware/devices/device_manager.c` (TODO)

**伪代码**：
```c
typedef struct {
    MotorDevice  motors[6];
    ServoDevice  servos[18];   // 暂未实现
    SystemDevice system;       // 单例
    // ... 可注册: PumpDevice, LEDDevice ...
} DeviceManager;

Device* device_manager_get(uint8_t svc, uint8_t inst) {
    switch (svc) {
        case SVC_MOTOR:  return &g_dm.motors[inst - 1];
        case SVC_SYSTEM: return &g_dm.system;
        // ... case SVC_SERVO: return ...
    }
}
```

**当前状态**：
- ⚠️ 当前由 `services.c` 直接 `switch(svc)`，未抽成 manager
- 短期：4 个 service 还能撑
- 长期：必须抽象（加 Servo/Stepper/Sensor 时复杂度爆炸）

---

### Layer 6: Device

**职责**：真正业务。每种设备 = 一个类，**包含** Driver + Controller + 业务逻辑。

**设备组件**（来自工业自动化/机器人 SDK 通用模式）：
```
MotorDevice
├── Driver          ← 只操作硬件 (PWM/DIR/EN), 不解析协议
├── Encoder         ← 只读编码器, 不做控制
├── Controller      ← PID/前馈/级联, 不碰硬件
├── Filter          ← 低通/中值/卡尔曼
├── Homing          ← 找零点逻辑
└── Safety          ← 堵转/超时/低电压保护
```

**当前实现**：
- ✅ `motor_pid.{c,h}` — 独立 PID 控制器类 (Layer 6 的 Controller)
- ⚠️ `services.c::motor_handler` — Motor 业务（混了协议字段映射 + SDK 调用）
- ⚠️ 缺 Driver 抽象（直接调 `set_motor(port, pwm)` 闭源 SDK）
- ❌ 缺 Filter / Homing / Safety（TODO）

**伪代码**（目标）：
```c
typedef struct {
    MotorDriver  driver;        // setPWM / enable / disable
    MotorEncoder encoder;       // read / reset
    PIDController speed_pid;
    PIDController pos_pid;
    LowPassFilter filter;
    StallDetector safety;
    HomingFSM    homing;
    int8_t       target_speed;
    uint8_t      port;
} MotorDevice;

void motor_set_speed(MotorDevice* m, int8_t speed) {
    if (m->safety.is_ok() && !m->homing.is_running()) {
        m->target_speed = m->filter.update(speed);
        m->driver.set_pwm(m->port, m->speed_pid.compute(m->encoder.delta()));
    }
}
```

---

## 4. 当前实现状态（对照 6 层）

| Layer | PC 端 | MCU 端 | 状态 |
|-------|-------|--------|------|
| 1. Python SDK | `host/mc602/devices/` | — | ✅ 完成 |
| 2. Transport | `host/mc602/device.py` (pyserial) | `UartPC_Sendbytes` (闭源) | ✅ 完成 |
| 3. Packet | `host/mc602/protocol.py` | `firmware/protocol/{cobs,crc8}.{c,h}` | ✅ 完成 |
| 4. Dispatcher | (Python SDK 内置) | `firmware/core/dispatcher.c` | ✅ 完成 |
| 5. DeviceManager | (MC602 内置) | ⚠️ `firmware/devices/services.c` (内联) | 🟡 **TODO** |
| 6. Device | `host/mc602/services/` | ⚠️ `firmware/devices/{motor_pid,services,system_monitor}` (部分) | 🟡 **TODO** |

**L5 缺口**：当前 `services.c` 在 Dispatcher 里直接 `switch(svc)`，没有 device_manager 抽象。
**L6 缺口**：当前 Motor 业务混在 `services.c::motor_handler` 里，没拆出 Driver/Controller/Filter/Homing/Safety 独立组件。

---

## 5. 加新设备的模板

按 6 层从上到下加，每层只动该层：

### Step 1: Python SDK（per-instance Device 类）

`host/mc602/devices/servo.py`:
```python
class Servo:
    def __init__(self, bot, port: int):
        self._bot = bot
        self._service = bot.servo_bus
        self.port = port
    
    def set_angle(self, angle: int) -> None:
        self._service.set_angle(self.port, angle)
```

### Step 2: Python Service（薄 RPC 包装）

`host/mc602/services/servo_bus.py`:
```python
class ServoBusService:
    SVC = 0x20
    PROP_ANGLE = 0x01
    # ... GET / SET 请求
```

### Step 3: MCU Service 注册（在 dispatcher 中）

`firmware/devices/services.c`:
```c
void services_init(void) {
    proto_service_register(SVC_MOTOR, "Motor", motor_handler);
    proto_service_register(SVC_SERVO, "ServoBus", servo_handler);  // 新加
    proto_service_register(SVC_SYSTEM, "System", system_handler);
}
```

### Step 4: MCU Device 业务

`firmware/devices/servo.c`:
```c
ServoDevice servos[18];

static uint8_t servo_handler(...) {
    ServoDevice* s = &servos[inst - 1];
    if (op == OP_SET && prop == PROP_ANGLE) {
        s->target_angle = value[0] | (value[1] << 8);
        s->driver.set_angle(s->target_angle);  // Layer 6 内部
    }
}
```

---

## 6. 6 层架构的价值

| 价值 | 体现 |
|------|------|
| **易扩展** | 加 Servo/Stepper/Sensor 只新增 Device 类 + 注册，不动 Dispatcher |
| **易维护** | 通信 / 控制 / 驱动完全解耦，可独立测试 |
| **Python 易用** | 与下位机 API 一一对应，学习成本低 |
| **控制稳定** | PID/滤波等实时算法全部在下位机，不受串口延迟影响 |
| **可移植** | UART 换 CAN/USB/TCP，Layer 1/3 不变 |
| **后期升级** | 控制器可独立升级 (PID → LQR → MPC)，Python 零修改 |

---

**最后更新**: 2026-07-03
**架构版本**: 6-Layer (v1.0)
**作者**: mc602p-firmware 架构组

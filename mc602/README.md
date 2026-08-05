# mc602 — MC602P 控制器 Python SDK + 烧录工具

> Python SDK + 蓝牙手柄 + 运动学/里程计 + 一键烧录

## 烧录固件

```bash
python tools/flash/flash.py                    # 烧录 tools/flash/Run.bin
```

## 控制 MC602P

```python
from mc602 import MC602, Motors, MecanumChassis, BTPad

with MC602.connect() as bot:
    # 通用 N 电机底盘
    chassis = Motors(bot, ports=(1, 2, 3, 4))         # 或 ("M1","M2","M3","M4")
    chassis.set_speeds(50, -50, -50, 50)              # 1 帧 4 路
    e1, e2, e3, e4 = chassis.get_encoders()

    # 麦克纳姆车 (底盘 + 运动学 + 里程计)
    car = MecanumChassis(bot, ports=(1, 2, 3, 4),
                        track=30, wheel_base=28, wheel_radius=3)
    car.move(vx=30, vy=0, omega=0.5)            # 车身速度 → 4 轮
    car.update()                                # 读编码器 → 里程计
    print(car.pose)                             # Pose2D(x=..., y=..., θ=...)

    # 蓝牙手柄
    pad = bot.pad
    state = pad.get_state()                    # 摇杆 + 按键
    pad.calibrate()                            # 自动校准中心
    fwd, strafe, rot = pad.get_deadzoned()     # 归一化
```

## 目录结构

```
mc602/
├── __init__.py
├── comm/                    串口客户端 + COBS + CRC-8
├── services/                薄 RPC 包装
│   ├── motor.py             MotorService      (SVC 0x01)
│   ├── system.py            SystemService     (SVC 0xFE)
│   ├── multi_motors.py      MultiMotorService (SVC 0x02, N=4; 逐路 N≠4)
│   ├── btpad.py             BTPadService      (SVC 0x03)
│   └── stepper.py           StepperService    (SVC 0x30, 485 步进)
├── drivers/                 面向对象设备
│   ├── motor.py             Motor(port)
│   ├── system.py            System
│   ├── motors.py            Motors (端口映射)
│   ├── mecanum_chassis.py   MecanumChassis (底盘 + 运动学)
│   ├── btpad.py             BTPad (死区/校准/KEY_MAP)
│   └── stepper.py           Stepper (485 步进, ST1~ST3)
├── motion/                  纯数学 (无 RPC)
│   ├── mecanum.py           MecanumMotion (正逆解 + 里程计)
│   └── coordinate.py        Transform2D
├── examples/                一键运行 demo
├── tests/                   单元测试 + 评测
└── tools/                   烧录工具
    └── flash/               一键烧录
```

## API 速查

### 电机 (per-instance)
```python
m = bot.motor.set_speed(port, 50)         # 单电机
m.reset_encoder(port)
m.get_encoder(port)
```

### 多电机底盘
```python
ch = Motors(bot, ports=(1,2,3,4))   # 端口顺序可配, 也支持 ("M1","M2","M3","M4")
ch.set_speeds(50, -50, -50, 50)          # 1 帧 4 路
ch.get_encoders()                         # (e1, e2, e3, e4)
ch.stop()
```

### 麦克纳姆车
```python
car = MecanumChassis(bot, ports=(1,2,3,4),
                     track=30, wheel_base=28, wheel_radius=3)
car.move(vx=30, vy=0, omega=0.5)          # 车身速度 (cm/s, rad/s)
car.update()                              # 读编码器 → 里程计
car.pose                                  # Pose2D (cm, rad)
car.distance                              # 总里程 cm
car.reset_pose()                          # 归零
```

### 蓝牙手柄
```python
pad = bot.pad
state = pad.get_state()                  # BTPadState (原始)
pad.calibrate()                          # 自动校准
fwd, strafe, rot = pad.get_deadzoned()   # -1.0~+1.0, 死区
pad.KEY_MAP[4]                           # "🔺"
```

### 步进电机 (485 总线)
```python
st = robot.stepper(3)            # ST1~ST3, 或 robot.stepper("ST3")
st.set_speed(3000)               # 脉冲速度 -32000~32000
st.speed = -1500                 # property 写法
print(st.distance)               # 驱动器反馈累计脉冲
st.acc = 2000                    # 加减速 (默认 1000)
st.stop()                        # 停 (保持力矩)
st.reset()                       # 复位/释放 (固件阻塞 ~100ms)
```

### 舵机 (485 总线 + PWM 两个版本)
```python
# 485 总线舵机 (S1~S18, 与步进共用总线)
s = robot.servo485(1)
s.set_angle(90)                  # -150~150, speed 默认 40
s.angle = -45                    # property 写法

# PWM 舵机 (P7~P13, 7 路)
p = robot.servo_pwm(7)           # 或 robot.servo_pwm("P7")
p.set_angle(90, speed=60)        # 0~180, speed 10~100
p.angle = 135
```

## 通信参数

| 项 | 值 |
|---|---|
| 串口 | USART1 → CH340 → USB |
| 波特率 | 1,000,000 (1 Mbps) |
| 协议 | COBS + CRC-8 + Service/Property |

## 错误处理

```python
from mc602 import (SerialNotFoundError, ConnectionError,
                    ProtocolError, TimeoutError)

try:
    with MC602.connect() as bot:
        bot.motor.set_speed(M1, 50)
except SerialNotFoundError as e:
    print("CH340 没接上:", e)
```

## 系统要求

- Python 3.8+
- `pyserial`
- CH340 驱动自装

```bash
pip install pyserial
```

## 版本

0.3.0 — 蓝牙手柄 + 运动学/里程计 + 组控协议

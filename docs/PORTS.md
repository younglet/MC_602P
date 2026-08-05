# 端口定义 — MC602P 实体接口与上位机 API 对照

> 与实体板子实物一一对应。固件/上位机按此文档组织。

## 1. 实体接口总览

```
P1~P6   (水晶头)  = 数字 DIG1~6  + 模拟 A1~A6      ← 合并口 (MCU 引脚独立)
AI1~AI3 (独立口)  = 模拟 (PC4/PC5/PB1)
D1~D7   (独立口)  = PWM 舵机 + 数字 DIG7~13         ← 这两者共用引脚, 互斥
```

## 2. 引脚映射

### P1~P6 水晶头 (数字 + 模拟)

| 口 | 数字 (DIG) | MCU 引脚 | 模拟 (A) | MCU 引脚 |
|----|-----------|---------|---------|---------|
| P1 | DIG1 | PD5  | A1 | PC0 (ADC10) |
| P2 | DIG2 | PD4  | A2 | PC1 (ADC11) |
| P3 | DIG3 | PC15 | A3 | PC2 (ADC12) |
| P4 | DIG4 | PD10 | A4 | PC3 (ADC13) |
| P5 | DIG5 | PA4  | A5 | PA0 (ADC0) |
| P6 | DIG6 | PB9  | A6 | PA1 (ADC1) |

> 数字与模拟是不同 MCU 引脚, 可同时使用。
> ⚠️ P1/P2 与 UART 复用 (SDK uart_p1/uart_p2)。

### AI1~AI3 独立模拟口

| 口 | MCU 引脚 | SDK getAI |
|----|---------|-----------|
| AI1 | PC4 (ADC14) | getAI(7) |
| AI2 | PC5 (ADC15) | getAI(8) |
| AI3 | PB1 (ADC9)  | getAI(9) |

### D1~D7 独立口 (PWM 舵机 / 数字)

| 口 | 数字 (DIG) | MCU 引脚 | PWM 舵机通道 |
|----|-----------|---------|-------------|
| D1 | DIG7  | PE9  | SERVO_PWM1 (T1C1) |
| D2 | DIG8  | PE11 | SERVO_PWM2 (T1C2) |
| D3 | DIG9  | PE13 | SERVO_PWM3 (T1C3) |
| D4 | DIG10 | PE14 | SERVO_PWM4 (T1C4) |
| D5 | DIG11 | PA7  | SERVO_PWM5 (T3C2) |
| D6 | DIG12 | PA6  | SERVO_PWM6 (T3C1) |
| D7 | DIG13 | PB14 | SERVO_PWM7 (T12C1) |

> ⚠️ 数字与 PWM 舵机是同一 MCU 引脚, **互斥** (同一时刻只能用一个功能)。

## 3. 能力矩阵

| 端口号 | 命名 | 数字 IO | 模拟输入 | PWM 舵机 |
|--------|------|:-------:|:--------:|:--------:|
| 1~6 | P1~P6 | ✅ | ✅ A1~A6 | — |
| 7~9 | D1~D3 | ✅ | ✅ AI1~AI3 | ✅ (与数字互斥) |
| 10~13 | D4~D7 | ✅ | — | ✅ (与数字互斥) |

## 4. 上位机 API

```python
from mc602 import P1, P6, D1, D7, A1, A6, AI1, AI3
# P1~P6 = 1~6, D1~D7 = 7~13, A1~A6 = 1~6 (P 口模拟), AI1~AI3 = 7~9 (D1~D3)

# 数字输出 (P1~P6 / D1~D7)
pump = robot.digital_out("P2")
pump.write(1)              # 输出高
pump.value = 0             # property 写法
pump.read()                # 读回电平
pump.toggle()              # 反转

# 模拟输入 (A1~A6 = P1~P6, AI1~AI3 = D1~D3)
a = robot.analog("AI2")
a.read()                   # 原始 ADC 值 (0~4095, 12 位)
a.voltage                  # 电压 V

# 通用 PWM (D1~D7, 40Hz; ⚠️ 与同口 DigitalOutput 互斥)
p = robot.pwm("D3")
p.set_duty(50.0)           # 占空比 0~100%

# 485 舵机 / PWM 舵机
robot.servo485(1).set_angle(90)
robot.servo_pwm("D1").set_angle(90)
```

## 5. 其他设备端口

| 设备 | 端口/ID | 说明 |
|------|---------|------|
| 电机 | M1~M6 | PID 速度/位置闭环 |
| 步进电机 | ST1~ST3 | 485 总线 (与舵机同链) |
| 485 舵机 | S1~S18 | 485 总线, 改 ID 限 1~3 |
| PWM 舵机 | D1~D7 | 见上表 |
| 底盘 | M1~M4 | Mecanum 外环控制器 (SVC 0x04) |

## 6. 服务 ID 汇总

| SVC | 服务 | 说明 |
|-----|------|------|
| 0xFE | System | 电压/版本/重启 |
| 0x01 | Motor | M1~M6 PID |
| 0x02 | Mecanum | 4 路组控 |
| 0x03 | BTRemote | 蓝牙手柄 |
| 0x04 | Chassis | 底盘外环 (运动学/里程计/GOTO) |
| 0x20 | ServoBus | 485 舵机 |
| 0x21 | ServoPWM | PWM 舵机 D1~D7 |
| 0x30 | Stepper | 步进电机 |
| 0x50 | IO | 数字 IO + 模拟输入 |

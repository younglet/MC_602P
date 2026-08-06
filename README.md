# mc602p-firmware — 鲸鱼机器人 GCC 用户固件

> 3 层清晰目录：项目根 → 分类 → 源码

```
mc602p-firmware/
├── docs/          # 参考文档（架构 / 烧录 / API / 硬件）
├── firmware/      # 下位机 C 固件 (STM32 / AT32F403, FreeRTOS)
├── host/          # 上位机 Python SDK + 评测脚本
├── AT32Gcc/       # 闭源 SDK (vendor, 不动)
├── pybuilder/     # 编译/烧录辅助工具 (vendor, 不动)
└── python/        # 旧 Scratch API (vendor, 不动)
```

## 快速开始

### 1. 编译下位机固件
```bash
# 方式 A: 分两步 (编译 + 烧录)
python firmware/tools/build_firmware.py --deploy
python mc602/tools/flash/flash.py

# 方式 B: 一键 (编译 + 部署 + 烧录)
python mc602/tools/flash/flash.py --rebuild
```

`--deploy` 拷贝 `Run.bin` 到 `mc602/tools/flash/`，`flash.py` 烧录它。
PING 慢帧会自动触发旧固件复位，**不需要手动按按钮**。

### 3. 跑上位机评测
```bash
# 自动化测试与设备评测 (单元测试无需硬件, *_test 实机)
python mc602/tests/test_protocol_unit.py
python mc602/tests/test_stepper_unit.py
python mc602/tests/test_servo_unit.py
python mc602/tests/test_chassis_unit.py

# 实机评测 (需要固件已烧录)
python mc602/examples/pad_mecanum.py         # 蓝牙手柄直读遥控 (固件模式)
python mc602/examples/pad_web_map.py         # Web 遥控 + 实时地图
python mc602/examples/chassis_calibrate.py   # 底盘标定
python mc602/examples/mecanum_full_eval.py   # 4 路电机全面评测
```

## 关键文档

| 想了解... | 看这里 |
|----------|--------|
| 6 层架构 / 加新 device 模板 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 烧录 / 状态机 / PING / 常见坑 | [docs/FIRMWARE.md](docs/FIRMWARE.md) |
| GPIO / 端口 / 内存 / SDK API 字典 | [docs/REFERENCE.md](docs/REFERENCE.md) |
| 端口定义 (P1~P6/AI/D1~D7 映射) | [docs/PORTS.md](docs/PORTS.md) |
| 336 个硬件 API 真值表 | [docs/hardware_api.csv](docs/hardware_api.csv) |
| 固件使用 / 编译 / LCD / Service 状态 | [firmware/README.md](firmware/README.md) |
| 上位机 SDK / per-instance OOP | [host/README.md](host/README.md) |

## 目录速查

| 路径 | 内容 |
|------|------|
| `firmware/app/` | 用户程序入口 (`user_main.c`) |
| `firmware/core/` | Dispatcher (协议引擎核心) |
| `firmware/devices/` | Device 业务（电机 PID、System 服务、Service 注册） |
| `firmware/protocol/` | Packet (COBS + CRC8) |
| `firmware/tools/` | 编译/烧录脚本 (build_firmware.py) |
| `firmware/build/` | 编译产物 (bin/elf/map) |
| `mc602/` | **发布包**: Python SDK + tools/flash/ + examples + tests |
| `mc602/examples/` | 实机 demo/eval (需硬件) |
| `unit_test/` | 单元测试 (mock, 验证代码) |
| `mc602/tests/` | 基础硬件功能测试 (简单) |
| `mc602/examples/` | 复杂项目: 遥控/评测/标定 |

---

**最后更新**: 2026-07-03
**固件版本**: V102
**Python SDK**: v0.2.0

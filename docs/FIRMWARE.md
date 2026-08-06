# MC602P 固件管理完全指南

> **核心原则：所有烧录、退出、启动操作都通过 PC 串口命令完成，绝不手动按按钮。**
> 如果你觉得需要手动复位 / 断电 — 那一定是你哪里没想对。

---

## 1. 控制器 3 个"执行体"

| 名字 | Flash 地址 | 角色 | 谁启动它 |
|------|------------|------|---------|
| **BootLoader** | `0x08000000` (52KB) | 系统引导、烧录协议 | 上电/复位后第一个跑 |
| **GUI** | `0x08040000` (128KB) | 菜单界面（Scratch 选 RunA~F 用的就是它） | BootLoader 默认跳到它 |
| **User Program** | `0x0800D000` (100KB) | 我们写的 C 固件 | GUI 菜单里选，或 `pydownload.py` 烧完自动 `RunCode(0x0800D000)` |
| RunA~F | `0x08060000`~`0x080E4000` | 备用用户程序存储 | GUI 菜单选择 |

**关键事实**：
- 6 个 RunA~F 槽位是**存储**（备份），不是独立执行区
- 所有用户程序都链接到 `0x0800D000` 运行（共用 linker script）
- 切换程序时，固件从 RunA 槽把代码**复制**到 `0x0800D000` 再跳过去

---

## 2. 烧录协议（PC ↔ 控制器）

`pydownload.py` 的 PING 帧（**注意是慢 PING**：每字节间隔 1ms）：

```
[0x55] [0xAA] [0x00] [0x01] [0x08] [0x00] [0x00] [~checksum]
 ↑    ↑     seq   PING  len=8  padding
```

PING 的**唯一作用**：让当前固件检测到 → 跳到 BootLoader，让 pydownload.py 能继续 PING 到 BootLoader。

**BootLoader / GUI 响应 PING**：

```
[0x66] [0xBB] [0x00] [0x01] [0x08] [0x00] [control_type_lo] [control_type_hi] [??] [~checksum]
                                                  ↑                ↑
                                                  602 = 0x025A → 字节 0x5A, 0x02
```

---

## 3. PC 端烧录/启动/退出的完整命令集

### 3.1 启动：把当前 slot1 跑起来

```bash
# GUI 启动后, 烧到 0x0800D000 并立即跳转
cd C:/Users/young/Desktop/whalesbot/new_whalesbot/AI_Module_GCC/mc602p-firmware
python pybuilder/pydownload.py -file "AT32Gcc/Debug/Run.bin" -address 0x800D000
```

**注意：不要加 `-run true`** — 那个参数会让 pydownload.py 在 PING 还没握上时就尝试跳，干扰握手。

### 3.2 退出当前固件（→ GUI）

```python
from mc602 import MC602
with MC602.connect() as bot:
    bot.system.bootloader()  # 跳到 GUI 0x08040000
# 之后 pydownload.py 能 PING 到 GUI, 重新烧
```

### 3.3 退出当前固件（→ BootLoader）

```python
bot.system.reboot()  # 跳到 BootLoader 0x08000000
```

### 3.4 自动：PING 触发退出

`pydownload.py` 发的慢 PING (1ms/byte) 会被固件的 UART 中断识别（8 字节序列匹配），然后**自动调用 `NVIC_SystemReset()` 复位到 BootLoader**。之后 pydownload.py 第二次 PING 就能 PING 到 BootLoader 完成握手。

**这是默认行为 — 用户完全不用按按钮。**

### 3.5 检查 slot1 是否在跑 + 是否是预期的版本

```python
with MC602.connect() as bot:
    print(bot.system.version)  # 期望: "MC602P v1.1"
    print(bot.system.uptime)   # 启动后秒数 (小 = 刚 boot 完)
```

如果连不上 (= `SerialNotFoundError` 或 `ConnectionError`)：
- 控制器不在 slot1 (可能在 GUI 或 BootLoader)
- 用 `pydownload.py -file FILENOLOAD -address 0x800D000` 不下载, 只 PING + RunCode 跳过去
- 等 3 秒让它 boot 完
- 再用 mc602 连

---

## 4. 标准工作流（每次改固件）

```bash
# 1. 编译
cd C:/Users/young/Documents/projects/mc602p-firmware
python smart_car_sdk/tools/build_firmware.py

# 2. 复制到 pydownload.py 能找到的位置
cp smart_car_sdk/build/Run.bin \
   C:/Users/young/Desktop/whalesbot/new_whalesbot/AI_Module_GCC/mc602p-firmware/AT32Gcc/Debug/Run.bin

# 3. 烧录 (pydownload.py 的 PING 会自动让旧固件退出)
cd C:/Users/young/Desktop/whalesbot/new_whalesbot/AI_Module_GCC/mc602p-firmware
python pybuilder/pydownload.py -file "AT32Gcc/Debug/Run.bin" -address 0x800D000

# 4. 等 3 秒让固件启动完
sleep 3

# 5. 验证
cd C:/Users/young/Documents/projects/mc602p-firmware
python -c "
from mc602 import MC602
with MC602.connect() as bot:
    print('FW:', bot.system.version)
    print('uptime:', bot.system.uptime)
    print('services:', [hex(s) for s in bot.discover()])
"

# 6. 跑 demo
python smart_car_sdk/examples/m1_pid_eval.py
```

---

## 5. 状态机速查

```
        ┌────────────┐
        │  BootLoader│  (上电/复位/NVIC_SystemReset)
        │  0x8000000 │
        └─────┬──────┘
              │  PING 之后, 默认下一步
              ▼
        ┌────────────┐
   ┌───►│    GUI     │  菜单选 RunA~F 或 GCC
   │    │  0x8040000 │
   │    └─────┬──────┘
   │          │  GUI 选 "GCC"  或  pydownload.py RunCode(0x800D000)
   │          ▼
   │    ┌────────────┐
   │    │User Program│  slot1 (0x800D000)
   │    │  0x800D000 │
   │    └─────┬──────┘
   │          │  PING 触发 NVIC_SystemReset()
   │          │  或  bot.system.reboot() / bootloader()
   │          ▼
   │    ┌────────────┐
   └────│  BootLoader│  → 然后到 GUI
        │  0x8000000 │
        └────────────┘
```

**重要**：PING 路径只走 **BootLoader → GUI**。所以 `pydownload.py` PING 成功后，**控制器在 GUI**（不在 BootLoader）。要再次跳到 user program 必须用 `pydownload.py` 的 `RunCode(0x800D000)`，或 GUI 菜单里点。

---

## 6. 常见坑

| 症状 | 原因 | 解决 |
|------|------|------|
| `SerialNotFoundError` | CH340 驱动没装 / USB 没插 | 装驱动 / 换口（不用动固件） |
| `TimeoutError: DISCOVER 超时` | 固件没起来 / 不是我们的协议固件 | 重烧 + 等 3s |
| `pydownload.py: ---Fail: No Control` 5 次 | PING 触发后固件退出，但还没轮回到下一 PING | 多跑几次 `pydownload.py`，或先 `bot.system.bootloader()` 再烧 |
| 烧完再连不上 | 固件 hang 住 (motor/SDK 死锁) | **`bot.system.reboot()`** — 不需要手动复位 |
| 想测多个版本 | RunA~F 是 6 个槽 | `pydownload.py -address 0x8060000` (RunA) 等 |
| **跑 1~2 个测试就卡死** | 心跳 callback 写 UART → 与协议响应帧抢同一 TX buffer → 响应截断, PC 端 CRC 错 | **心跳 callback 不能写 UART**. 系统状态 PC 端通过 `bot.system.*` 主动 poll (不需要主动推送) |

---

## 7. 怎么"绝对不需要手动"

PC 端能做的所有事情：
1. 烧新固件 → `pydownload.py`
2. 启动旧固件 → `pydownload.py -file FILENOLOAD -address 0x800D000`
3. 跳到 GUI → `bot.system.bootloader()`
4. 跳到 BootLoader → `bot.system.reboot()`
5. **PING 自动触发退出** → 慢 PING 序列检测 → `NVIC_SystemReset()`

如果某次跑 demo 固件 hang 了：
1. `bot.system.reboot()` 如果固件还响应
2. 不响应就发 PING (1ms/byte 8 次)，固件 UART 中断会识别，自动复位

**这两条都不需要按按钮**。

---

## 8. 验证清单（每次改固件后必跑）

- [ ] 烧录成功 (`---Download Success ---RunCode : ok`)
- [ ] 3 秒后 mc602 能连 (`MC602.connect()` 不抛异常)
- [ ] `bot.system.version` 字符串正确
- [ ] `bot.discover()` 返回 `['0xfe', '0x1']` (System + Motor)
- [ ] `bot.motor.set_speed(M1, 0)` + `bot.motor.stop(M1)` 不会 hang
- [ ] 跑 `m1_spin_demo.py` 跑完
- [ ] 跑 `m1_pid_eval.py` 跑完

---

**最后更新**: 2026-07-02
**固件版本**: V102
**核心原则**: 任何状态 → PC 命令切换。无例外。

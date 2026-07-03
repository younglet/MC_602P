# tools/flash/ — MC602P 烧录工具

> 把 `Run.bin` 烧到 MC602P 的工具集
>
> 自包含：`flash.py` + `pydownload.py` + `Run.bin` 在同一目录

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `flash.py` | 一键烧录入口（推荐用这个） |
| `pydownload.py` | BootLoader 协议实现（`flash.py` 内部调用） |
| `Run.bin` | 最新预编译固件（69KB，System + Motor Service） |

---

## 用法

### 1. 烧录当前 Run.bin（最常用）

```bash
python flash.py
```

输出：
```
[flash] 固件: .../tools/flash/Run.bin
[flash] 大小: 67 KB
[flash] 地址: 0x0800D000
[flash] 调 pydownload.py ...
```

PING 慢帧会自动触发旧固件 `NVIC_SystemReset()` 复位，**不需要按按钮**。

### 2. 烧录到指定槽位

MC602P 的 Flash 有 6 个用户槽位（RunA~RunF），加上 GCC 执行区（0x0800D000）：

| 地址 | 用途 |
|------|------|
| `0x0800D000` | GCC 用户程序执行区（默认） |
| `0x08060000` | RunA |
| `0x08080000` | RunB |
| `0x08099000` | RunC |
| `0x080B2000` | RunD |
| `0x080CB000` | RunE |
| `0x080E4000` | RunF |
| `0x08000000` | BootLoader |
| `0x08040000` | GUI 菜单 |

```bash
python flash.py --address 0x08060000   # 烧到 RunA
python flash.py --address 0x08099000   # 烧到 RunC
```

### 3. 烧录自定义固件

```bash
python flash.py --bin /path/to/Run.bin
```

### 4. 编译 + 部署 + 烧录（仅开发者）

```bash
python flash.py --rebuild
```

`--rebuild` 会调上级 `firmware/tools/build_firmware.py --deploy`，把源码编译并部署到本目录的 `Run.bin`，然后烧录。

**注意**：本包是发布包，**不含 C 源码**。`--rebuild` 失败是预期的（找不到源码路径），普通用户用不到这个选项。

---

## 故障排查

| 症状 | 原因 | 解决 |
|------|------|------|
| `找不到固件: Run.bin` | Run.bin 不在 | 从包管理器重装 / 重新下载 |
| `找不到 pydownload.py` | tools/flash/ 损坏 | 重新安装本包 |
| 烧录卡在 PING | 控制器不在 user program | 长按 reset 重启 |
| 烧完连不上 | 固件 hang | 等 3s 后 `python -c "from mc602 import Robot; Robot.connect()"` 试连 |
| `---Fail: No Control` | 协议错 | 重试 / 换 USB 口 |

---

## 通信参数

| 项 | 值 |
|---|---|
| 串口 | USART1 → CH340 → USB |
| 波特率 | 1,000,000 (1 Mbps) |
| 帧格式 | `[55 AA] [SEQ] [CMD] [LEN] [DATA] [~CHK]` |
| 关键命令 | `PING(0x01)` / `WRITE_BUFFER(0x10)` / `RAM2FLASH(0x20)` / `CRC(0x50)` / `RUNCODE(0x40)` |

---

**最后更新**: 2026-07-03

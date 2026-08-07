"""
flash.py — 一键烧录 mc602/tools/flash/Run.bin 到 MC602P

默认参数:
  - 固件: mc602/tools/flash/Run.bin
  - 地址: 0x0800D000 (GCC 用户程序执行区)
  - 烧录器: mc602/tools/flash/pydownload.py (BootLoader 协议)

烧录前启动阶梯 (解决"还在 download 就自动跳出"):
  1. 先 PING 探测
  2. PING 不通 → RunCode 启动 RunA 槽程序, 把控制器拉回用户程序运行态
     (只有用户程序跑起来, UART 中断里的慢 PING 检测才武装)
  3. 等固件 boot 完成 (时间给足)
  4. 再 PING
  5. 再不行才真正下载 (协议层自带 5 次重试)

下载阶段协议等待全部放宽 ("时间要足够写"):
  控制器写 flash / 回包较慢时, PC 端不会提前超时, 不会中途跳出下载态。

用法:
  # 标准: 烧录现有 Run.bin (自动启动阶梯)
  python mc602/tools/flash/flash.py

  # 编译 + 部署 + 烧录 (一键)
  python mc602/tools/flash/flash.py --rebuild

  # 跳过启动阶梯, 直接下载 (老行为)
  python mc602/tools/flash/flash.py --direct

  # 自定义固件
  python mc602/tools/flash/flash.py --bin path/to/Run.bin

  # 自定义地址
  python mc602/tools/flash/flash.py --address 0x08060000
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import time
from pathlib import Path


HERE         = Path(__file__).resolve().parent   # mc602/tools/flash/
PKG_ROOT     = HERE.parent                      # mc602/tools/
WORKSPACE    = PKG_ROOT.parent                  # mc602p-firmware/
DEFAULT_BIN  = HERE / "Run.bin"
PYDOWNLOAD   = HERE / "pydownload.py"
BUILD_SCRIPT = WORKSPACE / "firmware" / "tools" / "build_firmware.py"

DEFAULT_ADDRESS = 0x0800D000  # GCC 用户程序执行区
RUN_A_ADDR      = 0x08060000  # RunA 槽 (启动阶梯: 把控制器拉回用户程序运行态)

# 启动阶梯参数: 每轮 PING 间隔给足, 让运行中的用户程序检测到慢 PING 并复位
PING_ATTEMPTS = 3             # 每轮 PING 次数
PING_GAP_S    = 1.0           # 两次 PING 间隔
BOOT_WAIT_S   = 4.0           # RunCode 启动 RunA 后, 等固件 boot 完成的时间


def rebuild() -> None:
    """调 build_firmware.py --deploy 把新固件部署到 host/mc602/tools/Run.bin"""
    print(f"[rebuild] 调 {BUILD_SCRIPT} --deploy ...")
    if not BUILD_SCRIPT.exists():
        print(f"[!] 找不到构建脚本: {BUILD_SCRIPT}")
        print(f"    提示: 这个 mc602 包是纯运行时 SDK, 完整源码在 {WORKSPACE}/")
        sys.exit(1)
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--deploy"],
        cwd=str(WORKSPACE),
    )
    if result.returncode != 0:
        print(f"[!] 构建失败 (returncode={result.returncode})")
        sys.exit(result.returncode)


def load_pydownload():
    """加载 BootLoader 协议层 (与 mc602/comm/client.py 同一方式)。

    返回前放宽所有协议往返等待 —— "时间要足够写":
    控制器写 flash / 回包较慢时, PC 端不会提前超时, 更不会中途跳出下载态。
    """
    spec = importlib.util.spec_from_file_location("pydownload", PYDOWNLOAD)
    pd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pd)

    pd.TIMEOUT              = 0.5    # 串口读写超时 (0.2s → 0.5s)
    pd.PING_TIME_DELAY      = 0.02   # PING 回复等待 (5ms → 20ms)
    pd.DW_TIME_DELAY        = 0.02   # 下载指令回复等待
    pd.CRC_TIME_DELAY       = 0.02   # CRC 指令回复等待
    pd.RAM2FLASH_TIME_DELAY = 0.25   # Ram→Flash 写入等待 (0.1s → 0.25s)
    pd.RUNCODE_TIME_DELAY   = 0.1    # RunCode 回复等待 (50ms → 100ms)

    # 禁用 resume (CrcFlash 假匹配):
    # 控制器对 CRC 命令的响应是回显而非真实 flash CRC (实测返回请求值),
    # 依赖它跳过会永远 "Crc Same,Resume" → 只有 0k 块真写, 4k 起从未写入
    # (这就是"烧录时间太短"的根源: 秒完但固件是残缺的).
    # 强制全量真写, 87KB 约 6s, 可靠优先.
    pd.CrcFlash = lambda ser, addr, crc: False
    return pd


def find_ch340_port(pd):
    """找 CH340 串口 (用协议层的 PID/VID 过滤)"""
    import serial.tools.list_ports
    for p in serial.tools.list_ports.comports():
        if (p.pid, p.vid) == (pd.PID, pd.VID):
            return p.device
    return None


def ping_loop(pd, port, attempts=PING_ATTEMPTS, gap=PING_GAP_S):
    """阶段 1/3: 先 PING。

    每轮间隔给足: 运行中的用户程序收到慢 PING 后要复位到 BootLoader,
    需要时间, 连续快速 PING 只会全部打在复位窗口外。
    """
    for i in range(attempts):
        ctype = pd.PingControl(port)
        if ctype > 0:
            return ctype
        time.sleep(gap)
    return 0


def launch_runa(pd, port) -> None:
    """阶段 2: PING 不通 → RunCode 启动 RunA 槽程序。

    把控制器拉回用户程序运行态: 只有用户程序跑起来, UART 中断里的
    慢 PING 检测才武装, 下一次 PING 才能触发 NVIC_SystemReset 复位
    到 BootLoader 完成握手。之后无论 RunCode 是否成功, 都等足 boot 时间。
    """
    print(f"[preflight] PING 不通 → RunCode 启动 RunA @0x{RUN_A_ADDR:08X} ...")
    try:
        ok = pd.RunCode(port, RUN_A_ADDR)
    except Exception:
        ok = False
    if ok:
        print(f"[preflight] RunCode 已发送, 等 {BOOT_WAIT_S:.0f}s 让固件 boot ...")
    else:
        print(f"[preflight] RunCode 无响应 (控制器可能不在 BootLoader/GUI),"
              f" 仍等 {BOOT_WAIT_S:.0f}s ...")
    time.sleep(BOOT_WAIT_S)


def download(pd, port, bin_path, address) -> bool:
    """阶段 4/5: 真正下载 (协议层等待已放宽)。"""
    if not pd.ReadBin(str(bin_path)):
        print(f"[flash] 读取固件失败: {bin_path}")
        return False
    if not pd.Download(port, address):
        print("[flash] 下载失败 (控制器中途跳出下载态?)")
        return False
    if address == DEFAULT_ADDRESS:
        pd.SaveNameToStm32(port, "RunA")
    if not pd.RunCode(port, address):
        print("[flash] RunCode 失败")
        return False
    return True


def flash(bin_path: Path, address: int, direct: bool = False) -> int:
    """烧录: 先建立稳定握手 (PING → 启动 RunA → 再 PING → 强烧), 再下载。"""
    if not bin_path.exists():
        print(f"[!] 找不到固件: {bin_path}")
        print(f"    提示: 先跑 `python {BUILD_SCRIPT} --deploy`")
        print(f"    或加 --rebuild: `python {HERE / 'flash.py'} --rebuild`")
        return 1

    size_kb = bin_path.stat().st_size // 1024
    print(f"[flash] 固件: {bin_path}")
    print(f"[flash] 大小: {size_kb} KB")
    print(f"[flash] 地址: 0x{address:08X}")

    if not PYDOWNLOAD.exists():
        print(f"[!] 找不到 pydownload.py: {PYDOWNLOAD}")
        return 1

    pd = load_pydownload()
    port = find_ch340_port(pd)
    if port is None:
        print("[!] 找不到控制器串口 (CH340), 检查 USB 连接")
        return 1
    print(f"[flash] 串口: {port}")

    if direct:
        print("[preflight] --direct: 跳过启动阶梯, 直接下载")
    else:
        # 阶段 1: 先 PING
        ctype = ping_loop(pd, port)
        if ctype > 0:
            print(f"[preflight] PING 成功 (control_type={ctype}), 控制器就绪")
        else:
            # 阶段 2: PING 不通 → 启动 RunA
            launch_runa(pd, port)
            # 阶段 3: 再 PING
            ctype = ping_loop(pd, port)
            if ctype > 0:
                print(f"[preflight] 启动 RunA 后 PING 成功 (control_type={ctype})")
            else:
                # 阶段 5: 再不行 → 强烧 (协议层自带 5 次重试)
                print("[preflight] 仍无响应 → 直接尝试烧录 (pydownload 会继续重试)")

    if not download(pd, port, bin_path, address):
        return 1
    return 0


# 槽位表 (与 mc602/comm/client.py SLOT_TABLE 一致)
SLOT_TABLE = {
    "A":    {"name": "RunA",   "addr": 0x0800D000},
    "B":    {"name": "RunB",   "addr": 0x08060000},
    "C":    {"name": "RunC",   "addr": 0x08080000},
    "D":    {"name": "RunD",   "addr": 0x08099000},
    "E":    {"name": "RunE",   "addr": 0x080B2000},
    "F":    {"name": "RunF",   "addr": 0x080CB000},
}


def resolve_slot(slot: str) -> int:
    key = slot.upper()
    if key not in SLOT_TABLE:
        print(f"[!] 未知槽位: {slot}, 可用 {sorted(SLOT_TABLE)}")
        sys.exit(1)
    info = SLOT_TABLE[key]
    print(f"[flash] 槽位: {key} ({info['name']} @0x{info['addr']:08X})")
    return info["addr"]


def main() -> int:
    parser = argparse.ArgumentParser(description="一键烧录 MC602P 固件")
    parser.add_argument("--bin", type=Path, default=DEFAULT_BIN,
                        help=f"固件路径 (默认: {DEFAULT_BIN})")
    parser.add_argument("--slot", type=str, default="A",
                        help="烧录槽位: A~F (RunA~RunF, 默认 A = 主固件 0x0800D000)")
    parser.add_argument("--address", type=lambda s: int(s, 0), default=DEFAULT_ADDRESS,
                        help=f"目标地址 (默认: 0x{DEFAULT_ADDRESS:08X}, 与 --slot 二选一)")
    parser.add_argument("--rebuild", action="store_true",
                        help="先 build + deploy, 再烧录")
    parser.add_argument("--direct", action="store_true",
                        help="跳过启动阶梯 (PING→启动RunA→再PING), 直接下载")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  MC602P 一键烧录")
    print("=" * 60)

    # 槽位 → 地址 (--address 显式指定时优先)
    address = args.address
    if args.slot and args.address == DEFAULT_ADDRESS:
        address = resolve_slot(args.slot)

    if args.rebuild:
        rebuild()

    rc = flash(args.bin, address, direct=args.direct)

    if rc == 0:
        print(f"\n[OK] 烧录完成。固件已跳到 0x{address:08X} 执行。")
    else:
        print(f"\n[!] 烧录失败 (returncode={rc})")
    return rc


if __name__ == "__main__":
    sys.exit(main())

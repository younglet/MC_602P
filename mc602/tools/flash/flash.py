"""
flash.py — 一键烧录 mc602/tools/flash/Run.bin 到 MC602P

默认参数:
  - 固件: mc602/tools/flash/Run.bin
  - 地址: 0x0800D000 (GCC 用户程序执行区)
  - 烧录器: mc602/tools/flash/pydownload.py (BootLoader 协议)

用法:
  # 标准: 烧录现有 Run.bin
  python mc602/tools/flash/flash.py

  # 编译 + 部署 + 烧录 (一键)
  python mc602/tools/flash/flash.py --rebuild

  # 自定义固件
  python mc602/tools/flash/flash.py --bin path/to/Run.bin

  # 自定义地址
  python mc602/tools/flash/flash.py --address 0x08060000
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


HERE         = Path(__file__).resolve().parent   # mc602/tools/flash/
PKG_ROOT     = HERE.parent                      # mc602/tools/
WORKSPACE    = PKG_ROOT.parent                  # MC_602P/
DEFAULT_BIN  = HERE / "Run.bin"
PYDOWNLOAD   = HERE / "pydownload.py"
BUILD_SCRIPT = WORKSPACE / "firmware" / "tools" / "build_firmware.py"

DEFAULT_ADDRESS = 0x0800D000  # GCC 用户程序执行区


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


def flash(bin_path: Path, address: int) -> int:
    """调 pydownload.py 把 bin 烧到指定地址"""
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

    print(f"[flash] 调 pydownload.py ...")
    result = subprocess.run([
        sys.executable, str(PYDOWNLOAD),
        "-file", str(bin_path),
        "-address", hex(address),
    ])
    return result.returncode


# 槽位表 (与 mc602/comm/client.py SLOT_TABLE 一致)
SLOT_TABLE = {
    "A":    {"name": "GCC",    "addr": 0x0800D000},
    "GUI":  {"name": "GUI",    "addr": 0x08040000},
    "APP1": {"name": "APP1",   "addr": 0x08060000},
    "APP2": {"name": "APP2",   "addr": 0x08080000},
    "APP3": {"name": "APP3",   "addr": 0x08099000},
    "APP4": {"name": "APP4",   "addr": 0x080B2000},
    "APP5": {"name": "APP5",   "addr": 0x080CB000},
    "APP6": {"name": "APP6",   "addr": 0x080E4000},
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
                        help="烧录槽位: A/GUI/APP1~APP6 (默认 A = GCC 0x0800D000)")
    parser.add_argument("--address", type=lambda s: int(s, 0), default=DEFAULT_ADDRESS,
                        help=f"目标地址 (默认: 0x{DEFAULT_ADDRESS:08X}, 与 --slot 二选一)")
    parser.add_argument("--rebuild", action="store_true",
                        help="先 build + deploy, 再烧录")
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

    rc = flash(args.bin, address)

    if rc == 0:
        print(f"\n[OK] 烧录完成。固件已跳到 0x{address:08X} 执行。")
    else:
        print(f"\n[!] 烧录失败 (returncode={rc})")
    return rc


if __name__ == "__main__":
    sys.exit(main())

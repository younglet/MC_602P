"""
build_firmware.py — 智能车固件编译脚本
=======================================

编译 smart_car_sdk/device/ 下的 C 源码，链接 AT32Gcc 现成的
闭源 SDK (.o 文件) 和标准库, 输出 smart_car_sdk/build/Run.bin。

用法:
    python tools/build_firmware.py                # 编译
    python tools/build_firmware.py --clean        # 清理后重新编译
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# 全局: 强制 UTF-8 (避免 Windows GBK 撞 GCC 中文输出)
# ---------------------------------------------------------------------------

os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).resolve().parent                  # smart_car_sdk/tools/
SDK_DIR   = TOOLS_DIR.parent                                 # smart_car_sdk/

WORKSPACE_DIR = SDK_DIR.parent                                # Documents/projects/mc602p-firmware/
AT32GCC_DIR   = WORKSPACE_DIR / "AT32Gcc"                     # 现成 SDK
DEVICE_DIR    = SDK_DIR                                        # 我们的 C 源码 (firmware/ 本身就是源码根)
BUILD_DIR     = SDK_DIR / "build"                             # 编译输出
DEPLOY_DIR    = WORKSPACE_DIR / "mc602" / "tools" / "flash"  # 部署目标 (--deploy 写入这里)

TOOLCHAIN_DIR = WORKSPACE_DIR / "toolchain" / "arm_gcc_10"  # 项目内自带工具链
GCC           = TOOLCHAIN_DIR / "bin" / "arm-none-eabi-gcc.exe"
OBJCOPY       = TOOLCHAIN_DIR / "bin" / "arm-none-eabi-objcopy.exe"
SIZE          = TOOLCHAIN_DIR / "bin" / "arm-none-eabi-size.exe"

# 编译参数
CFLAGS_COMMON = [
    "-mcpu=cortex-m3",
    "-mthumb",
    "-mfloat-abi=soft",
    "-std=gnu11",
    "-g3", "-DDEBUG", "-DSTM32", "-DSTM32F1", "-DSTM32F101VETx",
    "-Ofast",
    "-ffunction-sections", "-fdata-sections",
    "-Wall", "-fstack-usage",
    "-MMD", "-MP",
]

# 头文件搜索路径
INCLUDE_DIRS = [
    DEVICE_DIR,
    DEVICE_DIR / "app",
    DEVICE_DIR / "core",
    DEVICE_DIR / "protocol",
    DEVICE_DIR / "devices",
    AT32GCC_DIR / "Inc" / "control",
    AT32GCC_DIR / "Inc" / "user",
    AT32GCC_DIR / "Inc" / "externlib",
    AT32GCC_DIR / "STM32_Stdlib" / "CMSIS" / "CM3" / "DeviceSupport" / "ST" / "STM32F10x",
    AT32GCC_DIR / "STM32_Stdlib" / "CMSIS" / "CM3" / "CoreSupport",
    AT32GCC_DIR / "STM32_Stdlib" / "STM32F10x_StdPeriph_Driver" / "inc",
    AT32GCC_DIR / "STM32_Stdlib" / "FreeRTOS" / "inc",
]

# 链接器配置
LINKER_SCRIPT = AT32GCC_DIR / "linkscript" / "stm32_flash.ld"
LDFLAGS = [
    "-mcpu=cortex-m3", "-mthumb", "-mfloat-abi=soft",
    "-static", "-Wl,--gc-sections",
    "--specs=nano.specs", "--specs=nosys.specs",
    "-u", "_printf_float", "-u", "_scanf_float",
    "-Wl,--start-group", "-lc", "-lm", "-Wl,--end-group",
]

# 链接时需要从现成 SDK 拉的 .o
SDK_OBJECT_DIRS = [
    AT32GCC_DIR / "Debug" / "Src" / "control",
    AT32GCC_DIR / "Debug" / "Src" / "externlib",
    AT32GCC_DIR / "Debug" / "STM32_Stdlib" / "STM32F10x_StdPeriph_Driver" / "src",
    AT32GCC_DIR / "Debug" / "STM32_Stdlib" / "FreeRTOS" / "src",
    AT32GCC_DIR / "Debug" / "Startup",
]

# 显式排除 (避免与我们的实现冲突)
# step_driver.o: 用自研源码版 firmware/devices/step_driver.c
# (增加 485 总线独占标志 step_bus_busy, 供舵机改 ID 等独立 API 使用),
# SDK 预编译版无此能力。
EXCLUDE_OBJECTS: set[str] = {
    "step_driver.o",
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def info(msg: str) -> None:
    print(f"  {msg}")


def section(msg: str) -> None:
    print(f"\n[{msg}]")


def error(msg: str) -> None:
    print(f"\n[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd: List[str]) -> subprocess.CompletedProcess:
    """运行命令, 捕获输出并以 UTF-8 解码."""
    res = subprocess.run(cmd, capture_output=True)
    res.stdout = res.stdout.decode("utf-8", errors="replace") if res.stdout else ""
    res.stderr = res.stderr.decode("utf-8", errors="replace") if res.stderr else ""
    return res


def check_toolchain() -> None:
    if not GCC.exists():
        error(f"工具链不存在: {GCC}\n请修改 TOOLCHAIN_DIR 路径。")
    info(f"toolchain: {TOOLCHAIN_DIR}")


def find_c_sources(root: Path) -> List[Path]:
    # 排除 _archive/ 目录 (备份代码, 不编译)
    return sorted(p for p in root.rglob("*.c") if "_archive" not in p.parts)


# ---------------------------------------------------------------------------
# 编译
# ---------------------------------------------------------------------------

def compile_source(src: Path, obj_dir: Path) -> Path:
    rel = src.relative_to(DEVICE_DIR)
    obj = obj_dir / rel.with_suffix(".o")
    obj.parent.mkdir(parents=True, exist_ok=True)
    dep = obj.with_suffix(".d")

    inc_args = [f"-I{d}" for d in INCLUDE_DIRS]

    cmd = [
        str(GCC), str(src),
        *CFLAGS_COMMON,
        *inc_args,
        f"-MF{dep}",
        f"-MT{obj}",
        "-c", "-o", str(obj),
    ]

    res = run(cmd)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        error(f"编译失败: {src.name}")
    return obj


def compile_all(clean: bool) -> List[Path]:
    section("编译 C 源码")
    obj_dir = BUILD_DIR / "obj"

    if clean and obj_dir.exists():
        info(f"清理: {obj_dir}")
        shutil.rmtree(obj_dir)
    obj_dir.mkdir(parents=True, exist_ok=True)

    sources = find_c_sources(DEVICE_DIR)
    if not sources:
        error(f"未找到 .c 源文件: {DEVICE_DIR}")

    info(f"源文件: {len(sources)} 个")
    objects = []
    t0 = time.time()
    for src in sources:
        rel = src.relative_to(DEVICE_DIR)
        info(f"  CC  {rel}")
        objects.append(compile_source(src, obj_dir))
    info(f"编译完成 ({time.time() - t0:.1f}s)")
    return objects


# ---------------------------------------------------------------------------
# 链接
# ---------------------------------------------------------------------------

def collect_sdk_objects() -> List[Path]:
    section("收集 SDK 对象文件")
    objects = []
    for d in SDK_OBJECT_DIRS:
        if not d.exists():
            error(f"SDK 目录不存在: {d}")
        for o in d.glob("*.o"):
            if o.name not in EXCLUDE_OBJECTS:
                objects.append(o)
    info(f"SDK .o: {len(objects)} 个")
    return objects


def generate_object_list(my_objects: List[Path], sdk_objects: List[Path]) -> Path:
    section("生成对象列表")
    list_file = BUILD_DIR / "objects.list"
    list_file.parent.mkdir(parents=True, exist_ok=True)
    with list_file.open("w", encoding="utf-8") as f:
        for o in my_objects:
            f.write(f'"{str(o).replace(os.sep, "/")}"\n')
        for o in sdk_objects:
            f.write(f'"{str(o).replace(os.sep, "/")}"\n')
    info(f"objects.list: {len(my_objects) + len(sdk_objects)} 个对象")
    return list_file


def link_elf(object_list: Path) -> Path:
    section("链接")
    elf = BUILD_DIR / "AT32Gcc.elf"
    map_file = BUILD_DIR / "AT32Gcc.map"

    cmd = [
        str(GCC),
        f"-T{LINKER_SCRIPT}",
        *LDFLAGS,
        f"-Wl,-Map={map_file}",
        f"@{object_list}",
        "-o", str(elf),
    ]
    info(f"  LD  {elf.name}")
    res = run(cmd)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        error("链接失败")
    return elf


def make_bin(elf: Path) -> Path:
    section("生成 BIN")
    bin_file = BUILD_DIR / "Run.bin"
    cmd = [str(OBJCOPY), "-O", "binary", str(elf), str(bin_file)]
    res = run(cmd)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        error("生成 BIN 失败")
    info(f"  BIN  {bin_file.name} ({bin_file.stat().st_size} bytes)")
    return bin_file


def show_size(elf: Path) -> None:
    section("大小")
    subprocess.run([str(SIZE), str(elf)])


# ---------------------------------------------------------------------------
# 部署 (--deploy): 拷贝 Run.bin 到 mc602sdk/
# ---------------------------------------------------------------------------

def deploy(bin_file: Path) -> None:
    """把编译产物复制到 mc602/tools/flash/Run.bin，供 flash.py 使用"""
    section("部署到 mc602/tools/flash/")
    target = DEPLOY_DIR / "Run.bin"
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bin_file, target)
    info(f"复制 {bin_file.name} -> {target}")
    info(f"  目标: {target} ({target.stat().st_size} bytes)")
    print(f"\n[下一步] 烧录: python {target.parent / 'flash.py'}")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="编译智能车固件")
    parser.add_argument("--clean", action="store_true", help="清理后编译")
    parser.add_argument("--deploy", action="store_true", help="编译后拷贝 Run.bin 到 mc602sdk/")
    args = parser.parse_args()

    print("=== smart_car_sdk 固件编译 ===")
    info(f"workspace: {WORKSPACE_DIR}")
    info(f"device:    {DEVICE_DIR}")
    info(f"build:     {BUILD_DIR}")

    check_toolchain()
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    my_objects = compile_all(clean=args.clean)
    sdk_objects = collect_sdk_objects()
    obj_list = generate_object_list(my_objects, sdk_objects)
    elf = link_elf(obj_list)
    bin_file = make_bin(elf)
    show_size(elf)

    print(f"\n[OK] 编译成功")
    print(f"     BIN: {bin_file}")

    if args.deploy:
        deploy(bin_file)


if __name__ == "__main__":
    main()

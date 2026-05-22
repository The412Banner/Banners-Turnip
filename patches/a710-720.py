#!/usr/bin/env python3
"""
Idempotent A7xx GPU entry additions for freedreno_devices.py.

Adds Adreno 710, 720, and 722 support using A730 magic regs.

Chip IDs:
  A710: 0x07010000 + wildcard 0xffff07010000
  A720: 0x43020000 + wildcard 0xffff43020000
  A722: 0x43020100 + wildcard 0xffff43020100

Safe to run multiple times (idempotent).
"""

import sys

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"

with open(DEVICES_PY, "r") as f:
    content = f.read()

original = content
changes = []

A710_BLOCK = """\
add_gpus([
        GPUId(chip_id=0x07010000, name="FD710"),
        GPUId(chip_id=0xffff07010000, name="FD710"),
    ], A6xxGPUInfo(
        CHIP.A7XX,
        [a7xx_base, a7xx_gen1],
        num_ccu = 3,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 1024,
        tile_max_h = 1024,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        highest_bank_bit = 16,
        magic_regs = a730_magic_regs,
        raw_magic_regs = a730_raw_magic_regs,
    ))

"""

A720_BLOCK = """\
add_gpus([
        GPUId(chip_id=0x43020000, name="FD720"),
        GPUId(chip_id=0xffff43020000, name="FD720"),
    ], A6xxGPUInfo(
        CHIP.A7XX,
        [a7xx_base, a7xx_gen1],
        num_ccu = 3,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 1024,
        tile_max_h = 1024,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        highest_bank_bit = 16,
        magic_regs = a730_magic_regs,
        raw_magic_regs = a730_raw_magic_regs,
    ))

"""

A722_BLOCK = """\
add_gpus([
        GPUId(chip_id=0x43020100, name="FD722"),
        GPUId(chip_id=0xffff43020100, name="FD722"),
    ], A6xxGPUInfo(
        CHIP.A7XX,
        [a7xx_base, a7xx_gen1],
        num_ccu = 3,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 1024,
        tile_max_h = 1024,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        highest_bank_bit = 16,
        magic_regs = a730_magic_regs,
        raw_magic_regs = a730_raw_magic_regs,
    ))

"""

def find_add_gpus_block_start(content, anchor_str):
    idx = content.find(anchor_str)
    if idx < 0:
        return -1
    start = content.rfind("add_gpus([", 0, idx)
    return start

if "chip_id=0x07010000" not in content:
    anchor = "chip_id=0x07030002"
    block_start = find_add_gpus_block_start(content, anchor)

    if block_start >= 0:
        content = content[:block_start] + A710_BLOCK + content[block_start:]
        changes.append("inserted FD710 add_gpus block before FD725")
    else:
        print("WARNING: could not find FD725 anchor to insert A710", file=sys.stderr)
        sys.exit(1)
else:
    print("A710 entry already present, skipping")

if "chip_id=0x43020000" not in content:
    anchor = "chip_id=0x07030002"
    block_start = find_add_gpus_block_start(content, anchor)

    if block_start >= 0:
        content = content[:block_start] + A720_BLOCK + content[block_start:]
        changes.append("inserted FD720 add_gpus block before FD725")
    else:
        print("WARNING: could not find FD725 anchor to insert A720", file=sys.stderr)
        sys.exit(1)
else:
    print("A720 entry already present, skipping")

if "chip_id=0x43020100" not in content:
    anchor = "chip_id=0x07030002"
    block_start = find_add_gpus_block_start(content, anchor)

    if block_start >= 0:
        content = content[:block_start] + A722_BLOCK + content[block_start:]
        changes.append("inserted FD722 add_gpus block before FD725")
    else:
        print("WARNING: could not find FD725 anchor to insert A722", file=sys.stderr)
        sys.exit(1)
else:
    print("A722 entry already present, skipping")

if content != original:
    with open(DEVICES_PY, "w") as f:
        f.write(content)

    for c in changes:
        print(f"✓ {c}")

    print(f"Wrote {DEVICES_PY}")
else:
    print("No changes needed — A710/A720/A722 already present")

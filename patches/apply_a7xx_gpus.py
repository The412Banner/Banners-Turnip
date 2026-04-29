#!/usr/bin/env python3
"""
Idempotent A7xx GPU entry additions for freedreno_devices.py.

Adds Adreno 710 and Adreno 720 chip IDs which are NOT in Mesa main.

Chip IDs extracted from binary analysis of MrPurple666's T27-toasted driver:
  A710: 0x07010000 + wildcard 0xffff07010000 (family=0x07, ADRENO_7XX_GEN1)
  A720: 0x43020000 + wildcard 0xffff43020000 (family=0x43, ADRENO_7XX_GEN2)

These match the kernel's chip_id scheme:
  0x07 family = GEN1 A7xx (same as A730: 0x07030001)
  0x43 family = GEN2 A7xx (same as A740: 0x43050a01, A735: 0x43030c00)

GPU properties are approximated from the same generation:
  A710 → a7xx_gen1 template + a730_magic_regs, num_ccu=2
  A720 → a7xx_gen2 template + a740_magic_regs, num_ccu=2

Safe to run multiple times.
"""
import sys
import re

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"

with open(DEVICES_PY, "r") as f:
    content = f.read()

original = content
changes = []

# ── A710: Adreno 710 (ADRENO_7XX_GEN1) ───────────────────────────────────
# Chip IDs from MrPurple's binary. Same gen1 family as A730 (0x07030001).
# Uses a730_magic_regs as best approximation — same firmware generation.
# num_ccu=2 based on hardware spec (smaller than A730's 4 CCU).

A710_BLOCK = """\
add_gpus([
        GPUId(chip_id=0x07010000, name="FD710"),
        GPUId(chip_id=0xffff07010000, name="FD710"),
    ], A6xxGPUInfo(
        CHIP.A7XX,
        [a7xx_base, a7xx_gen1],
        num_ccu = 2,
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

# ── A720: Adreno 720 (ADRENO_7XX_GEN2) ───────────────────────────────────
# Chip IDs from MrPurple's binary. Same gen2 family as A740 (0x43050a01).
# Uses a740_magic_regs as best approximation — same 0x43-family generation.
# num_ccu=2 based on estimated hardware spec (smaller than A735's 3 CCU).

A720_BLOCK = """\
add_gpus([
        GPUId(chip_id=0x43020000, name="FD720"),
        GPUId(chip_id=0xffff43020000, name="FD720"),
    ], A6xxGPUInfo(
        CHIP.A7XX,
        [a7xx_base, a7xx_gen2, GPUProps(enable_tp_ubwc_flag_hint = True)],
        num_ccu = 2,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 1024,
        tile_max_h = 1024,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        highest_bank_bit = 16,
        magic_regs = a740_magic_regs,
        raw_magic_regs = a740_raw_magic_regs,
    ))

"""

def find_add_gpus_block_containing(content, anchor_str):
    """Find the start offset of the add_gpus([...]) block containing anchor_str."""
    idx = content.find(anchor_str)
    if idx < 0:
        return -1
    # Walk back to find the add_gpus([ that owns this anchor
    start = content.rfind("add_gpus([", 0, idx)
    return start

# Insert A710 before the FD725 block (FD725 is the first existing A7xx gen1 above A702)
if "chip_id=0x07010000" not in content:
    anchor = "chip_id=0x07030002"  # FD725
    block_start = find_add_gpus_block_containing(content, anchor)
    if block_start >= 0:
        content = content[:block_start] + A710_BLOCK + content[block_start:]
        changes.append("inserted FD710 add_gpus block before FD725")
    else:
        print("  WARNING: could not find FD725 anchor to insert A710", file=sys.stderr)
else:
    print("  A710 entries already present, skipping")

# Insert A720 before FD725 (after A710, before A725)
if "chip_id=0x43020000" not in content:
    anchor = "chip_id=0x07030002"  # FD725 — still use same anchor, A710 is now above it
    block_start = find_add_gpus_block_containing(content, anchor)
    if block_start >= 0:
        content = content[:block_start] + A720_BLOCK + content[block_start:]
        changes.append("inserted FD720 add_gpus block before FD725")
    else:
        print("  WARNING: could not find FD725 anchor to insert A720", file=sys.stderr)
else:
    print("  A720 entries already present, skipping")

if content != original:
    with open(DEVICES_PY, "w") as f:
        f.write(content)
    for c in changes:
        print(f"  ✓ {c}")
    print(f"  Wrote {DEVICES_PY}")
else:
    print("  No changes needed — A710/A720 already present")

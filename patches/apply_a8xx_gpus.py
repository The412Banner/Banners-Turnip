#!/usr/bin/env python3
"""
Idempotent A8xx GPU entry applicator for freedreno_devices.py.
Applies GPU configs for A825, A810, A829 (A830 is already in Mesa main).
Safe to run multiple times — checks for existing entries before inserting.
"""
import sys
import re

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"

with open(DEVICES_PY, "r") as f:
    content = f.read()

original = content
changes = []

# ── helpers ────────────────────────────────────────────────────────────────

def already_has(marker):
    return marker in content

def insert_after(anchor, new_code):
    """Insert new_code after the first occurrence of anchor."""
    global content
    idx = content.find(anchor)
    if idx == -1:
        print(f"  WARNING: anchor not found: {anchor!r:.60}", file=sys.stderr)
        return False
    insert_pos = idx + len(anchor)
    content = content[:insert_pos] + "\n" + new_code + content[insert_pos:]
    return True

# ── a8xx_825 definition ────────────────────────────────────────────────────

A825_DEF = """\
a8xx_825 = GPUProps(
        reg_size_vec4 = 128,
        sysmem_vpc_attr_buf_size = 131072,
        sysmem_vpc_pos_buf_size = 65536,
        sysmem_vpc_bv_pos_buf_size = 32768,
        sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.FULL.value,
        sysmem_per_ccu_color_cache_size = 128 * 1024,
        sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.THREE_QUARTER.value,
        sysmem_per_ccu_depth_cache_size = 96 * 1024,
        gmem_vpc_attr_buf_size = 49152,
        gmem_vpc_pos_buf_size = 24576,
        gmem_vpc_bv_pos_buf_size = 32768,
        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,
        gmem_per_ccu_color_cache_size = 16 * 1024,
        gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.FULL.value,
        gmem_per_ccu_depth_cache_size = 127 * 1024,
        has_salu_int_narrowing_quirk = True
)
"""

A825_GPU = """\
# gen8_6_0
add_gpus([
        GPUId(chip_id=0x44030000, name="FD825"),
    ], A6xxGPUInfo(
        CHIP.A8XX,
        [a7xx_base, a7xx_gen3, a8xx_base, a8xx_825],
        num_ccu = 4,
        num_slices = 2,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 16384,
        tile_max_h = 16384,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        magic_regs = dict(
        ),
        raw_magic_regs = a8xx_base_raw_magic_regs,
    ))

"""

# ── a8xx_810 definition ────────────────────────────────────────────────────

A810_DEF = """\
a8xx_810 = GPUProps(
        reg_size_vec4 = 128,
        sysmem_vpc_attr_buf_size = 131072,
        sysmem_vpc_pos_buf_size = 65536,
        sysmem_vpc_bv_pos_buf_size = 32768,
        sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.FULL.value,
        sysmem_per_ccu_color_cache_size = 32 * 1024,
        sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.THREE_QUARTER.value,
        sysmem_per_ccu_depth_cache_size = 32 * 1024,
        gmem_vpc_attr_buf_size = 49152,
        gmem_vpc_pos_buf_size = 24576,
        gmem_vpc_bv_pos_buf_size = 32768,
        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,
        gmem_per_ccu_color_cache_size = 16 * 1024,
        gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.FULL.value,
        gmem_per_ccu_depth_cache_size = 64 * 1024,
        has_ray_intersection = False,
        has_sw_fuse = False,
        disable_gmem = True,
        has_salu_int_narrowing_quirk = True
)
"""

A810_GPU = """\
# gen8_3_0
add_gpus([
        GPUId(chip_id=0x44010000, name="FD810"),
    ], A6xxGPUInfo(
        CHIP.A8XX,
        [a7xx_base, a7xx_gen3, a8xx_base, a8xx_810],
        num_ccu = 2,
        num_slices = 1,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 16384,
        tile_max_h = 16384,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        magic_regs = dict(
        ),
        raw_magic_regs = a8xx_base_raw_magic_regs,
    ))

"""

# ── a8xx_829 definition ────────────────────────────────────────────────────

A829_DEF = """\
a8xx_829 = GPUProps(
        reg_size_vec4 = 128,
        sysmem_vpc_attr_buf_size = 131072,
        sysmem_vpc_pos_buf_size = 65536,
        sysmem_vpc_bv_pos_buf_size = 32768,
        sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.FULL.value,
        sysmem_per_ccu_color_cache_size = 128 * 1024,
        sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.THREE_QUARTER.value,
        sysmem_per_ccu_depth_cache_size = 96 * 1024,
        gmem_vpc_attr_buf_size = 49152,
        gmem_vpc_pos_buf_size = 24576,
        gmem_vpc_bv_pos_buf_size = 32768,
        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,
        gmem_per_ccu_color_cache_size = 16 * 1024,
        gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.FULL.value,
        gmem_per_ccu_depth_cache_size = 127 * 1024,
        disable_gmem = True,
        has_salu_int_narrowing_quirk = True
)
"""

A829_GPU = """\
# TODO: Properly fill all values for this GPU
add_gpus([
    GPUId(chip_id=0x44030A00, name="FD829"),
    GPUId(chip_id=0x44030A20, name="FD829"),
    GPUId(chip_id=0xffff44030A00, name="FD829"),
    ], A6xxGPUInfo(
        CHIP.A8XX,
        [a7xx_base, a7xx_gen3, a8xx_base, a8xx_829,],
        num_ccu = 4,
        num_slices = 2,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 16384,
        tile_max_h = 16384,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        magic_regs = dict(
        ),
        raw_magic_regs = a8xx_base_raw_magic_regs,
    ))

"""

# ── Apply changes ──────────────────────────────────────────────────────────

# Ensure a8xx_base_raw_magic_regs name is used (rename from a8xx_gen2_raw_magic_regs if needed)
if "a8xx_gen2_raw_magic_regs" in content and "a8xx_base_raw_magic_regs" not in content:
    content = content.replace("a8xx_gen2_raw_magic_regs", "a8xx_base_raw_magic_regs")
    changes.append("renamed a8xx_gen2_raw_magic_regs -> a8xx_base_raw_magic_regs")

# Find the anchor: end of a8xx_gen1 block followed by A830 add_gpus
# We look for the A830 chip_id as the insertion anchor
A830_GPU_ID = "GPUId(chip_id=0x44050000, name=\"FD830\")"

if not already_has("a8xx_825"):
    if already_has(A830_GPU_ID):
        # Insert a8xx_825 DEF before the A830 add_gpus block
        # Anchor: find the line before "add_gpus([" that contains the A830 id
        # We need to find the start of the A830 add_gpus block
        idx = content.find("add_gpus([\n        GPUId(chip_id=0x44050000")
        if idx == -1:
            idx = content.find("add_gpus([\n    GPUId(chip_id=0x44050000")
        if idx == -1:
            idx = content.find(A830_GPU_ID)
            # Go back to find the add_gpus( call
            idx = content.rfind("add_gpus([", 0, idx)
        if idx != -1:
            content = content[:idx] + A825_DEF + "\n" + A825_GPU + content[idx:]
            changes.append("inserted a8xx_825 definition and A825 add_gpus before A830")
        else:
            print("  WARNING: could not find A830 add_gpus anchor for a8xx_825", file=sys.stderr)
    else:
        print("  WARNING: a8xx_base_raw_magic_regs or A830 anchor not found, skipping a8xx_825", file=sys.stderr)
else:
    print("  a8xx_825 already present, skipping")

if not already_has("a8xx_810"):
    # Insert a8xx_810 DEF and add_gpus after a8xx_825 add_gpus block
    # Anchor: find a8xx_gen2 = GPUProps( which follows the A825 add_gpus in the original patch
    anchor_825_end = "GPUId(chip_id=0x44030000, name=\"FD825\")"
    if already_has(anchor_825_end):
        # Find the end of the A825 add_gpus block
        idx = content.find(anchor_825_end)
        # Find the )) that closes the add_gpus block
        idx_close = content.find("))\n", idx)
        if idx_close != -1:
            insert_after_pos = idx_close + 3  # after "))\n"
            content = content[:insert_after_pos] + "\n" + A810_DEF + "\n" + A810_GPU + content[insert_after_pos:]
            changes.append("inserted a8xx_810 definition and A810 add_gpus after A825")
        else:
            print("  WARNING: could not find close of A825 add_gpus for a8xx_810", file=sys.stderr)
    else:
        print("  WARNING: A825 GPU id not found, skipping a8xx_810", file=sys.stderr)
else:
    print("  a8xx_810 already present, skipping")

if not already_has("a8xx_829"):
    anchor_810_end = "GPUId(chip_id=0x44010000, name=\"FD810\")"
    if already_has(anchor_810_end):
        idx = content.find(anchor_810_end)
        idx_close = content.find("))\n", idx)
        if idx_close != -1:
            insert_after_pos = idx_close + 3
            content = content[:insert_after_pos] + "\n" + A829_DEF + "\n" + A829_GPU + content[insert_after_pos:]
            changes.append("inserted a8xx_829 definition and A829 add_gpus after A810")
        else:
            print("  WARNING: could not find close of A810 add_gpus for a8xx_829", file=sys.stderr)
    else:
        print("  WARNING: A810 GPU id not found, skipping a8xx_829", file=sys.stderr)
else:
    print("  a8xx_829 already present, skipping")

# ── Write result ───────────────────────────────────────────────────────────

if content != original:
    # Syntax check before writing
    try:
        compile(content, DEVICES_PY, "exec")
    except SyntaxError as e:
        print(f"  FATAL: syntax error after patching at line {e.lineno}: {e.msg}", file=sys.stderr)
        sys.exit(1)
    with open(DEVICES_PY, "w") as f:
        f.write(content)
    print(f"  Applied {len(changes)} change(s) to {DEVICES_PY}:")
    for c in changes:
        print(f"    + {c}")
else:
    print(f"  No changes needed in {DEVICES_PY} (all GPU entries already present)")

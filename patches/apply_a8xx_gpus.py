#!/usr/bin/env python3
"""
Idempotent A8xx GPU entry fixup for freedreno_devices.py.

Mesa main already has A810, A829, A830 entries but:
  - A825 is completely missing
  - A810 is missing its KGSL chip_id (0x44010000) and disable_gmem
  - A829 is missing additional chip IDs (0x44030A00, 0xffff44030A00)

Safe to run multiple times.
"""
import sys
import re

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"

with open(DEVICES_PY, "r") as f:
    content = f.read()

original = content
changes = []

# ── A825: completely missing from mesa main ────────────────────────────────

A825_BLOCK = """\
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
        has_salu_int_narrowing_quirk = True,
)

add_gpus([
        GPUId(chip_id=0x44030000, name="Adreno (TM) 825"),
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
        magic_regs = dict(),
        raw_magic_regs = a8xx_base_raw_magic_regs,
    ))

"""

if "a8xx_825" not in content:
    # Insert before the A810 add_gpus block
    anchor = 'GPUId(chip_id=0xffff44010000, name="Adreno (TM) 810")'
    idx = content.find("add_gpus([")
    while idx != -1:
        block_end = content.find("add_gpus([", idx + 1)
        chunk = content[idx:block_end] if block_end != -1 else content[idx:]
        if anchor in chunk:
            content = content[:idx] + A825_BLOCK + content[idx:]
            changes.append("inserted a8xx_825 definition and A825 add_gpus before A810")
            break
        idx = block_end
    else:
        print("  WARNING: could not find A810 add_gpus anchor for a8xx_825 insertion", file=sys.stderr)
else:
    print("  a8xx_825 already present, skipping")

# ── A810: add missing KGSL chip_id and disable_gmem ───────────────────────

A810_KGSL_ID = 'GPUId(chip_id=0xffff44010000, name="Adreno (TM) 810")'
A810_DIRECT_ID = 'GPUId(chip_id=0x44010000, name="Adreno (TM) 810")'

if A810_KGSL_ID in content and A810_DIRECT_ID not in content:
    content = content.replace(
        A810_KGSL_ID,
        'GPUId(chip_id=0x44010000, name="Adreno (TM) 810"),\n       ' + A810_KGSL_ID,
        1
    )
    changes.append("added chip_id=0x44010000 to A810 GPU entry")
else:
    if A810_DIRECT_ID in content:
        print("  A810 direct chip_id already present, skipping")
    else:
        print("  WARNING: A810 KGSL entry not found", file=sys.stderr)

# Add disable_gmem to A810 inline GPUProps if not already there
A810_PROPS_ANCHOR = "            has_fs_tex_prefetch = False,\n        )],"
A810_PROPS_WITH_GMEM = "            has_fs_tex_prefetch = False,\n            disable_gmem = True,\n        )],"

if A810_PROPS_ANCHOR in content and "disable_gmem" not in content[content.find(A810_KGSL_ID):content.find(A810_KGSL_ID)+800]:
    content = content.replace(A810_PROPS_ANCHOR, A810_PROPS_WITH_GMEM, 1)
    changes.append("added disable_gmem = True to A810 inline GPUProps")
else:
    print("  A810 disable_gmem already present or anchor not found, skipping")

# ── A829: add missing chip IDs ─────────────────────────────────────────────

A829_EXISTING = 'GPUId(chip_id=0x44030a20, name="Adreno (TM) 829")'
A829_EXTRA_1  = 'GPUId(chip_id=0x44030A00, name="Adreno (TM) 829")'
A829_EXTRA_2  = 'GPUId(chip_id=0xffff44030A00, name="Adreno (TM) 829")'

if A829_EXISTING in content:
    if A829_EXTRA_1 not in content:
        content = content.replace(
            A829_EXISTING,
            A829_EXTRA_1 + ",\n        " + A829_EXTRA_2 + ", # KGSL\n        " + A829_EXISTING,
            1
        )
        changes.append("added chip_id 0x44030A00 and 0xffff44030A00 to A829 GPU entry")
    else:
        print("  A829 extra chip IDs already present, skipping")
else:
    print("  WARNING: A829 entry not found", file=sys.stderr)

# ── Write result ───────────────────────────────────────────────────────────

if content != original:
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
    print(f"  No changes needed in {DEVICES_PY}")

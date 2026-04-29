#!/usr/bin/env python3
"""
Idempotent A7xx GPU entry additions for freedreno_devices.py.

Adds Adreno 710, 720, and 722 support which are NOT in Mesa main.

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

MAGIC_REGS_BLOCK = """\
fd720_722_magic_regs = dict(
        RB_DBG_ECO_CNTL      = 0x00000000,
        RB_DBG_ECO_CNTL_blit = 0x00000000,
        RB_RBP_CNTL          = 0x0,
)

fd720_722_raw_magic_regs = [
        [A6XXRegs.REG_A6XX_UCHE_CACHE_WAYS,              0x00840004],
        [A6XXRegs.REG_A6XX_TPL1_DBG_ECO_CNTL,            0x01000000],
        [A6XXRegs.REG_A6XX_TPL1_DBG_ECO_CNTL1,           0x00040724],
        [A6XXRegs.REG_A6XX_SP_CHICKEN_BITS,               0x00001400],
        [A6XXRegs.REG_A7XX_SP_CHICKEN_BITS_1,             0x00402400],
        [A6XXRegs.REG_A7XX_SP_CHICKEN_BITS_2,             0x00000000],
        [A6XXRegs.REG_A7XX_SP_CHICKEN_BITS_3,             0x00000000],
        [A6XXRegs.REG_A7XX_UCHE_UNKNOWN_0E10,             0x00000000],
        [A6XXRegs.REG_A7XX_UCHE_UNKNOWN_0E11,             0x00000040],
        [A6XXRegs.REG_A7XX_SP_HLSQ_DBG_ECO_CNTL,         0x00008000],
        [A6XXRegs.REG_A6XX_SP_DBG_ECO_CNTL,              0x10000000],
        [A6XXRegs.REG_A6XX_PC_MODE_CNTL,                 0x0000003f],
        [A6XXRegs.REG_A6XX_PC_DBG_ECO_CNTL,              0x20080000],
        [A6XXRegs.REG_A7XX_PC_UNKNOWN_9E24,              0x21fc7f00],
        [A6XXRegs.REG_A7XX_VFD_DBG_ECO_CNTL,             0x00000000],
        [A6XXRegs.REG_A7XX_SP_ISDB_CNTL,                 0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_AE6A,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_HLSQ_TIMEOUT_THRESHOLD_DP, 0x00000080],
        [A6XXRegs.REG_A7XX_SP_HLSQ_DBG_ECO_CNTL_1,      0x00000000],
        [A6XXRegs.REG_A7XX_SP_HLSQ_MODE_CNTL,            0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_AB01,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_AB22,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_B310,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE2,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE2+1,            0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE4,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE4+1,            0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE6,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE6+1,            0x00000000],
        [A6XXRegs.REG_A7XX_GRAS_ROTATION_CNTL,           0x00000000],
        [A6XXRegs.REG_A6XX_GRAS_DBG_ECO_CNTL,            0x00000800],
        [A6XXRegs.REG_A7XX_RB_UNKNOWN_8E79,              0x00000000],
        [A6XXRegs.REG_A7XX_RB_LRZ_CNTL2,                0x00000000],
        [A6XXRegs.REG_A7XX_RB_CCU_DBG_ECO_CNTL,         0x02080000],
        [A6XXRegs.REG_A6XX_VPC_DBG_ECO_CNTL,            0x02000000],
        [A6XXRegs.REG_A6XX_UCHE_UNKNOWN_0E12,            0x03200000],
]

fd710_magic_regs = dict(
        PC_DBG_ECO_CNTL      = 0x20100000,
        RB_DBG_ECO_CNTL      = 0x00000000,
        RB_DBG_ECO_CNTL_blit = 0x00000000,
        RB_RBP_CNTL          = 0x0,
)

fd710_raw_magic_regs = [
        [A6XXRegs.REG_A6XX_UCHE_CACHE_WAYS,              0x00040004],
        [A6XXRegs.REG_A6XX_TPL1_DBG_ECO_CNTL,            0x01000000],
        [A6XXRegs.REG_A6XX_TPL1_DBG_ECO_CNTL1,           0x00040724],
        [A6XXRegs.REG_A6XX_SP_CHICKEN_BITS,               0x00001400],
        [A6XXRegs.REG_A7XX_SP_CHICKEN_BITS_1,             0x00402400],
        [A6XXRegs.REG_A7XX_SP_CHICKEN_BITS_2,             0x00000000],
        [A6XXRegs.REG_A7XX_SP_CHICKEN_BITS_3,             0x00000000],
        [A6XXRegs.REG_A7XX_UCHE_UNKNOWN_0E10,             0x00000000],
        [A6XXRegs.REG_A7XX_UCHE_UNKNOWN_0E11,             0x00000040],
        [A6XXRegs.REG_A7XX_SP_HLSQ_DBG_ECO_CNTL,         0x00008000],
        [A6XXRegs.REG_A6XX_SP_DBG_ECO_CNTL,              0x10000000],
        [A6XXRegs.REG_A6XX_PC_MODE_CNTL,                 0x0000003f],
        [A6XXRegs.REG_A6XX_PC_DBG_ECO_CNTL,              0x20100000],
        [A6XXRegs.REG_A7XX_PC_UNKNOWN_9E24,              0x21fc7f00],
        [A6XXRegs.REG_A7XX_VFD_DBG_ECO_CNTL,             0x00000000],
        [A6XXRegs.REG_A7XX_SP_ISDB_CNTL,                 0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_AE6A,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_HLSQ_TIMEOUT_THRESHOLD_DP, 0x00000080],
        [A6XXRegs.REG_A7XX_SP_HLSQ_DBG_ECO_CNTL_1,      0x00000000],
        [A6XXRegs.REG_A7XX_SP_HLSQ_MODE_CNTL,            0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_AB01,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_AB22,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_B310,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE2,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE2+1,            0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE4,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE4+1,            0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE6,              0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE6+1,            0x00000000],
        [A6XXRegs.REG_A7XX_GRAS_ROTATION_CNTL,           0x00000000],
        [A6XXRegs.REG_A6XX_GRAS_DBG_ECO_CNTL,            0x00000800],
        [A6XXRegs.REG_A7XX_RB_UNKNOWN_8E79,              0x00000000],
        [A6XXRegs.REG_A7XX_RB_LRZ_CNTL2,                0x00000000],
        [A6XXRegs.REG_A7XX_RB_CCU_DBG_ECO_CNTL,         0x02080000],
        [A6XXRegs.REG_A6XX_VPC_DBG_ECO_CNTL,            0x02000000],
        [A6XXRegs.REG_A6XX_UCHE_UNKNOWN_0E12,            0x03200000],
]

"""

A710_BLOCK = """\
add_gpus([
        GPUId(chip_id=0x07010000, name="FD710"),
        GPUId(chip_id=0xffff07010000, name="FD710"),
    ], A6xxGPUInfo(
        CHIP.A7XX,
        [a7xx_base, a7xx_gen1, GPUProps(
            sysmem_per_ccu_color_cache_size = 256 * 1024,
            sysmem_per_ccu_depth_cache_size = 64 * 1024,
            has_gmem_vpc_attr_buf = True,
            sysmem_vpc_attr_buf_size = 131072,
            gmem_vpc_attr_buf_size = 49152,
        )],
        num_ccu = 3,
        tile_align_w = 32,
        tile_align_h = 16,
        tile_max_w = 1024,
        tile_max_h = 1024,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        highest_bank_bit = 16,
        magic_regs = fd710_magic_regs,
        raw_magic_regs = fd710_raw_magic_regs,
    ))

"""

A720_BLOCK = """\
add_gpus([
        GPUId(chip_id=0x43020000, name="FD720"),
        GPUId(chip_id=0xffff43020000, name="FD720"),
    ], A6xxGPUInfo(
        CHIP.A7XX,
        [a7xx_base, a7xx_gen1, GPUProps(
            sysmem_per_ccu_color_cache_size = 256 * 1024,
            sysmem_per_ccu_depth_cache_size = 64 * 1024,
            has_gmem_vpc_attr_buf = True,
            sysmem_vpc_attr_buf_size = 131072,
            gmem_vpc_attr_buf_size = 49152,
        )],
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
        magic_regs = fd720_722_magic_regs,
        raw_magic_regs = fd720_722_raw_magic_regs,
    ))

"""

A722_BLOCK = """\
add_gpus([
        GPUId(chip_id=0x43020100, name="FD722"),
        GPUId(chip_id=0xffff43020100, name="FD722"),
    ], A6xxGPUInfo(
        CHIP.A7XX,
        [a7xx_base, a7xx_gen1, GPUProps(
            sysmem_per_ccu_color_cache_size = 256 * 1024,
            sysmem_per_ccu_depth_cache_size = 64 * 1024,
            has_gmem_vpc_attr_buf = True,
            sysmem_vpc_attr_buf_size = 131072,
            gmem_vpc_attr_buf_size = 49152,
        )],
        num_ccu = 4,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 1024,
        tile_max_h = 1024,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        highest_bank_bit = 16,
        magic_regs = fd720_722_magic_regs,
        raw_magic_regs = fd720_722_raw_magic_regs,
    ))

"""

def find_add_gpus_block_start(content, anchor_str):
    idx = content.find(anchor_str)
    if idx < 0:
        return -1
    start = content.rfind("add_gpus([", 0, idx)
    return start

def find_magic_regs_insertion_point(content):
    anchor = "chip_id=0x07030002"
    block_start = find_add_gpus_block_start(content, anchor)
    if block_start < 0:
        anchor = "chip_id=0x07030001"
        block_start = find_add_gpus_block_start(content, anchor)
    return block_start

if "fd710_magic_regs" not in content and "fd720_722_magic_regs" not in content:
    insert_at = find_magic_regs_insertion_point(content)
    if insert_at >= 0:
        content = content[:insert_at] + MAGIC_REGS_BLOCK + content[insert_at:]
        changes.append("inserted fd710_magic_regs and fd720_722_magic_regs definitions")
    else:
        print("  WARNING: could not find insertion point for magic regs", file=sys.stderr)
        sys.exit(1)
else:
    print("  magic regs definitions already present, skipping")

if "chip_id=0x07010000" not in content:
    anchor = "chip_id=0x07030002"
    block_start = find_add_gpus_block_start(content, anchor)
    if block_start >= 0:
        content = content[:block_start] + A710_BLOCK + content[block_start:]
        changes.append("inserted FD710 add_gpus block before FD725")
    else:
        print("  WARNING: could not find FD725 anchor to insert A710", file=sys.stderr)
        sys.exit(1)
else:
    print("  A710 entry already present, skipping")

if "chip_id=0x43020000" not in content:
    anchor = "chip_id=0x07030002"
    block_start = find_add_gpus_block_start(content, anchor)
    if block_start >= 0:
        content = content[:block_start] + A720_BLOCK + content[block_start:]
        changes.append("inserted FD720 add_gpus block before FD725")
    else:
        print("  WARNING: could not find FD725 anchor to insert A720", file=sys.stderr)
        sys.exit(1)
else:
    print("  A720 entry already present, skipping")

if "chip_id=0x43020100" not in content:
    anchor = "chip_id=0x07030002"
    block_start = find_add_gpus_block_start(content, anchor)
    if block_start >= 0:
        content = content[:block_start] + A722_BLOCK + content[block_start:]
        changes.append("inserted FD722 add_gpus block before FD725")
    else:
        print("  WARNING: could not find FD725 anchor to insert A722", file=sys.stderr)
        sys.exit(1)
else:
    print("  A722 entry already present, skipping")

if content != original:
    with open(DEVICES_PY, "w") as f:
        f.write(content)
    for c in changes:
        print(f"  ✓ {c}")
    print(f"  Wrote {DEVICES_PY}")
else:
    print("  No changes needed — A710/A720/A722 already present")

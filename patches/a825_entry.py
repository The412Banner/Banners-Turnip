#!/usr/bin/env python3
"""
Adreno 825 device entry for the gen8 drivers (A8xx, Banners-AIO). Run from the Mesa tree right
after patches/a8xx_gen8.patch, before the other EXTRA_SCRIPT steps (a8xx_shared_mem.py and the AIO
gates read this entry).

Mesa main has no A825 yet. Mesa MR 46716 ("freedreno: Add Adreno 825", Artem Peshkov, open since
2026-11-25) adds one. Until then this script adds ours; once Mesa has an A825 entry it adds
nothing and the driver uses Mesa's. Before 2026-11-26 the entry was three parts of
a8xx_gen8.patch; as a patch it would clash with Mesa's entry and stop the build, the way the
upstream A812 entry did on 2026-11-25.

The entry below is byte for byte what those three parts produced:
  - "freedreno/common: enable A825" (whitebelyash, 2026-04-15)
  - the A825 hunk of "freedreno/common: update a8xx family configs" (DVD, 2026-04)
  - "freedreno/common: Fix offsets for A825/829" (DVD, 2026-06-02)
Mesa's dev_id_compare() matches its 0xffff44030000 entry to the 0x44030000 KGSL reports, so no
extra chip ID is needed when Mesa's entry is used.
"""
import re
import sys

DEVICES = "src/freedreno/common/freedreno_devices.py"
MARKER = "# gen8_6_0\n"
ANCHOR = 'add_gpus([\n        GPUId(chip_id=0xffff44030a20, name="Adreno (TM) 829"),'

A825 = MARKER + '''add_gpus([
        GPUId(chip_id=0x44030000, name="Adreno (TM) 825"),
    ], A6xxGPUInfo(
        CHIP.A8XX,
        [a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen1, a8xx_vpc_cache_lg, GPUProps(
            gmem_ccu_color_cache_fraction = CCUColorCacheFraction.HALF.value,
            gmem_per_ccu_color_cache_size = 128 * 1024,
            gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,
            gmem_per_ccu_depth_cache_size = 128 * 1024,

            sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.FULL.value,
            sysmem_per_ccu_color_cache_size = 128 * 1024,
            sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.THREE_QUARTER.value,
            sysmem_per_ccu_depth_cache_size = 96 * 1024,
            disable_gmem = False,
            gmem_size = 2 * 1024 * 1024,
            shading_rate_matches_vk = True,
        )],
        num_ccu = 4,
        num_slices = 2,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 16416,
        tile_max_h = 16384,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        raw_magic_regs = a8xx_base_raw_magic_regs,
    ))

'''


def main():
    try:
        text = open(DEVICES).read()
    except FileNotFoundError:
        sys.exit(f"a825_entry.py: {DEVICES} not found (run from the Mesa tree)")

    if MARKER in text:
        print("a825_entry.py: our A825 entry is already in the tree")
        return
    if (re.search(r"chip_id=0x(?:ffff)?44030000\b", text, re.IGNORECASE)
            or 'name="Adreno (TM) 825"' in text or 'name="FD825"' in text):
        print("a825_entry.py: Mesa has its own A825 entry (MR 46716?) - ours not added, Mesa's is used")
        return
    if text.count(ANCHOR) != 1:
        sys.exit("a825_entry.py: A829 entry (insertion point) not found once - update the anchor")

    text = text.replace(ANCHOR, A825 + ANCHOR, 1)
    compile(text, DEVICES, "exec")
    with open(DEVICES, "w") as f:
        f.write(text)
    print("a825_entry.py: added our A825 entry (Mesa has none yet)")


main()

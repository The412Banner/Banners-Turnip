#!/usr/bin/env python3
"""
One driver: limit the A8xx recipe's global changes to A8xx chips at runtime.

The One driver is built from the A8xx recipe (patches/a8xx_gen8.patch plus Max's
patches/a8xx-winnative series through apply_common.sh) and patches/a710-720.py, so a
single libvulkan_freedreno.so carries every GPU's settings and Turnip picks them by
chip ID at startup. Five parts of the A8xx recipe act on every GPU; this script turns
each one into a check on the chip, so A6xx and A7xx keep what the standard driver does:

  1. Compute shared memory: the A8xx recipe no longer raises it to 64 KiB (that gave
     wrong results on an Adreno 830); this script checks that no device entry
     reports more than 32 KiB.
  2. gen8 "HACK: tu: enforce TU_DEBUG=nocb": only when the device is gen 8.
  3. winnative 0001 mesh shaders: exposed on chip >= 8 instead of >= 7, and the
     task/mesh required-subgroup stage bits only where mesh shaders are exposed.
     patches/common/SOURCE: on A7xx they steered DX12 games onto slower paths.
  4. winnative 0002 half-wave subgroups: minSubgroupSize halved on chip >= 8 only
     (it also switched on for A7xx and A6xx gen4 through has_getfiberid).
  5. gen8 pipeline patch "FDM for A810,825,829,830": its A830 check was always true, so
     per-layer FDM and forced sample interpolation were off on every GPU; it now compares
     the two A830 chip IDs.

Also keeps the numInts >= 2 bounds check that gen8 "HACK: u_gralloc: always use
ubwc detection path" removed; the UBWC flag is still read without the 'gmsm' magic.

Run from the Mesa source root after EXTRA_PATCH. Every edit is asserted; any pattern
that is missing fails the build, so a driver without a gate is never zipped.
Safe to run more than once.
"""
import re
import sys
from pathlib import Path

errors = []


def fail(msg):
    errors.append(msg)
    print(f"  FATAL: {msg}", file=sys.stderr)


def edit(path, old, new, label):
    p = Path(path)
    s = p.read_text()
    if new in s:
        print(f"  {label}: already gated")
        return
    n = s.count(old)
    if n != 1:
        fail(f"{label}: expected 1 match in {path}, found {n}")
        return
    p.write_text(s.replace(old, new))
    print(f"  {label}: gated")


# 1. Shared memory: no entry above 32 KiB.
devices = Path("src/freedreno/common/freedreno_devices.py")
src = devices.read_text()
sizes = [int(m.group(1)) for m in re.finditer(r"cs_shared_mem_size = (\d+) \* 1024", src)]
a8 = sum(1 for b in src.split("add_gpus(")[1:] if "CHIP.A8XX" in b)
if not sizes:
    fail("no cs_shared_mem_size in freedreno_devices.py")
elif max(sizes) > 32:
    fail(f"a device entry reports {max(sizes)} KiB compute shared memory (limit 32 KiB)")
elif a8 == 0:
    fail("no CHIP.A8XX entries: the gen8 stack is missing")
else:
    print(f"  shared memory: {len(sizes)} entries, none above 32 KiB ({a8} A8XX)")

dev = "src/freedreno/vulkan/tu_device.cc"

# 2. Concurrent binning off on gen 8 only.
edit(dev,
     "   /* HACK: disable concurrent binning for now */\n"
     "   tu_env.debug |= TU_DEBUG_NO_CONCURRENT_BINNING;\n",
     "   /* HACK: disable concurrent binning for now (One driver: A8xx only) */\n"
     "   if (fd_dev_gen(&physical_device->dev_id) >= 8)\n"
     "      tu_env.debug |= TU_DEBUG_NO_CONCURRENT_BINNING;\n",
     "concurrent binning (gen8 nocb hack)")

# 3. Mesh shaders on A8xx only.
edit(dev,
     "   return device->info->chip >= 7 &&\n"
     "          device->info->cs_shared_mem_size >= 32 * 1024;\n",
     "   return device->info->chip >= 8 &&\n"
     "          device->info->cs_shared_mem_size >= 32 * 1024;\n",
     "mesh shaders (winnative 0001)")
edit(dev,
     "         : (VK_SHADER_STAGE_COMPUTE_BIT | VK_SHADER_STAGE_FRAGMENT_BIT |\n"
     "            VK_SHADER_STAGE_TASK_BIT_EXT | VK_SHADER_STAGE_MESH_BIT_EXT);\n",
     "         : (VK_SHADER_STAGE_COMPUTE_BIT | VK_SHADER_STAGE_FRAGMENT_BIT |\n"
     "            (tu_has_mesh_shader(pdevice)\n"
     "                ? (VK_SHADER_STAGE_TASK_BIT_EXT | VK_SHADER_STAGE_MESH_BIT_EXT)\n"
     "                : 0));\n",
     "required-subgroup task/mesh stages (winnative 0001)")

# 4. Half-wave subgroups on A8xx only.
edit(dev,
     "   return device->info->threadsize_base /\n"
     "          (device->info->props.has_getfiberid ? 2 : 1);\n",
     "   return device->info->threadsize_base /\n"
     "          (device->info->chip >= 8 && device->info->props.has_getfiberid ? 2 : 1);\n",
     "half-wave subgroups (winnative 0002)")

# 5. gen8 "tu/pipeline: ... FDM for A810,825,829,830": its A830 check is
#    `chip_id == 0xffff44050000 || 0x44050001`, always true, so fdm_per_layer and
#    force_sample_interp were turned off on every GPU. Compare both A830 IDs.
edit("src/freedreno/vulkan/tu_pipeline.cc",
     "   const bool is_a830 = chip_id == 0xffff44050000 || 0x44050001;\n",
     "   const bool is_a830 = chip_id == 0xffff44050000ull || chip_id == 0x44050001ull;\n",
     "A830 check in the FDM / sample-interp keys (gen8 pipeline patch)")

# Gralloc: keep the bounds check the gen8 hack dropped.
edit("src/util/u_gralloc/u_gralloc_fallback.c",
     "   bool ubwc = hnd->handle->data[hnd->handle->numFds + 1] & 0x08000000;\n"
     "   out->modifier = ubwc ? DRM_FORMAT_MOD_QCOM_COMPRESSED : DRM_FORMAT_MOD_LINEAR;\n",
     "   if (hnd->handle->numInts >= 2) {\n"
     "      bool ubwc = hnd->handle->data[hnd->handle->numFds + 1] & 0x08000000;\n"
     "      out->modifier = ubwc ? DRM_FORMAT_MOD_QCOM_COMPRESSED : DRM_FORMAT_MOD_LINEAR;\n"
     "   }\n",
     "gralloc UBWC flag (bounds check)")

# The rest of the recipe must be in the tree too (the Android leg applies the gen8 stack
# with fuzz and carries on after a reject, so check its results here).
checks = [
    ("src/freedreno/common/freedreno_devices.py", 'name="Adreno (TM) 825"', "gen8 stack (A825 entry)"),
    ("src/freedreno/common/freedreno_devices.py", "FD722_CUSTOM", "a710-720.py (A722 entry)"),
    ("src/freedreno/common/freedreno_dev_info.h", "disable_gmem", "gen8 stack (disable_gmem property)"),
    ("src/freedreno/vulkan/tu_util.h", "DECK_EMU", "gen8 stack (DECK_EMU)"),
    ("src/freedreno/vulkan/tu_mesh.cc", "", "winnative 0001 (tu_mesh.cc)"),
]
for path, needle, label in checks:
    p = Path(path)
    if not p.exists() or (needle and needle not in p.read_text()):
        fail(f"{label} missing from {path}")

if errors:
    print(f"one_gpu_gates.py: {len(errors)} problem(s), not building a One driver", file=sys.stderr)
    sys.exit(1)
print("one_gpu_gates.py: all A8xx-only changes gated; recipe present")

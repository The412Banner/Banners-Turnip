#!/usr/bin/env python3
"""
One driver: limit the A8xx recipe's global changes to A8xx chips at runtime.

The One driver is built from the A8xx recipe (patches/a8xx_gen8.patch plus Max's
patches/a8xx-winnative series through apply_common.sh) and patches/a710-720.py, so a
single libvulkan_freedreno.so carries every GPU's settings and Turnip picks them by
chip ID at startup. Four parts of the A8xx recipe act on every GPU; this script turns
each one into a check on the chip, so A6xx and A7xx keep what the standard driver does:

  1. cs_shared_mem_size 32 KiB -> 64 KiB: only in the CHIP.A8XX device entries
     (patches/a8xx_shared_mem.py changes all of them; the One recipe does not run it).
  2. gen8 "HACK: tu: enforce TU_DEBUG=nocb": only when the device is gen 8.
  3. winnative 0001 mesh shaders: exposed on chip >= 8 instead of >= 7, and the
     task/mesh required-subgroup stage bits only where mesh shaders are exposed.
     patches/common/SOURCE: on A7xx they steered DX12 games onto slower paths.
  4. winnative 0002 half-wave subgroups: minSubgroupSize halved on chip >= 8 only
     (it also switched on for A7xx and A6xx gen4 through has_getfiberid).

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


# 1. Shared memory: 64 KiB on A8XX entries only.
devices = Path("src/freedreno/common/freedreno_devices.py")
src = devices.read_text()
starts = [m.start() for m in re.finditer(r"^add_gpus\(", src, re.M)]
if not starts:
    fail("no add_gpus( blocks in freedreno_devices.py")
else:
    out = [src[: starts[0]]]
    a8 = changed = 0
    for i, st in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(src)
        block = src[st:end]
        if "CHIP.A8XX" in block:
            a8 += 1
            if "cs_shared_mem_size = 32 * 1024" in block:
                block = block.replace("cs_shared_mem_size = 32 * 1024",
                                      "cs_shared_mem_size = 64 * 1024")
                changed += 1
            elif "cs_shared_mem_size = 64 * 1024" not in block:
                fail(f"A8XX block at offset {st} has no cs_shared_mem_size")
        elif "cs_shared_mem_size = 64 * 1024" in block:
            fail(f"non-A8XX block at offset {st} has 64 KiB shared memory")
        out.append(block)
    new_src = "".join(out)
    try:
        compile(new_src, str(devices), "exec")
    except SyntaxError as e:
        fail(f"freedreno_devices.py syntax error after edit: line {e.lineno}: {e.msg}")
    if a8 == 0:
        fail("no CHIP.A8XX entries: the gen8 stack is missing")
    devices.write_text(new_src)
    print(f"  shared memory: {a8} A8XX entries ({changed} changed to 64 KiB), other entries unchanged")

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

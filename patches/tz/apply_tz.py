#!/usr/bin/env python3
"""
TurnipZ 0.3.0 port for Banners-AIO (lab branch feat/aio-tz, not merged).

TurnipZ 0.3.0 by AlexSanz0902 (https://github.com/AlexSanz0902/turnip-sd865-z) ships binaries only.
This patch rebuilds its mutable-image and BGRA (red/blue) handling from that binary: mutable images
stay tiled (UBWC only for a fixed format list at level 4), R/B-swapped views sample through a
ZYXW swizzle, render targets swap in the fragment shader (load_rt_swap_mask_ir3 driver param),
clear colours swap, and images seen with other swapped views fall back to linear next time.

Per GPU family (tu_tz_config): on for A6xx (TurnipZ's target), off elsewhere until tested.
Env TU_TZ_MUTABLE (0-4) and TU_TZ_BGRA (0 or 3) override.

Runs from the Mesa source root after the AIO recipe; applies tz_port.patch with git apply and
fails the build if it does not apply exactly.
"""
import os
import subprocess
import sys

here = os.path.dirname(os.path.abspath(__file__))
patch = os.path.join(here, "tz_port.patch")

if subprocess.run(["git", "apply", "--check", patch]).returncode != 0:
    sys.exit("apply_tz.py: tz_port.patch does not apply to this tree")
subprocess.run(["git", "apply", patch], check=True)

checks = {
    "src/compiler/nir/nir_intrinsics.py": 'system_value("rt_swap_mask_ir3", 1)',
    "src/freedreno/vulkan/tu_image.cc": "tz_mutable_keep_format",
    "src/freedreno/vulkan/tu_shader.cc": "tz_lower_rt_swap",
    "src/freedreno/vulkan/tu_device.cc": "TU_TZ_MUTABLE",
}
for path, marker in checks.items():
    if marker not in open(path).read():
        sys.exit(f"apply_tz.py: marker {marker!r} missing in {path}")
print("apply_tz.py: TurnipZ 0.3.0 mutable/BGRA port applied")

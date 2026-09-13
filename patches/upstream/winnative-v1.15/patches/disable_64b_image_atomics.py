#!/usr/bin/env python3
"""
Workaround: disable EXT_shader_image_atomic_int64 / shaderImageInt64Atomics
feature advertisement by clearing `has_64b_image_atomics = True` on the
A7xx_gen2 and A7xx_gen3 GPU presets (A8xx inherits from gen3).

Why: upstream mesa landed `5b87bbfad3b "tu: Support EXT_shader_image_atomic_int64"`
in early Apr 2026. UE5 / VKD3D-Proton with SM6.6 hits the new 64-bit image atomic
codegen path on A8xx and hangs the GPU after first render submit (game freezes
on black screen post-vkd3d-init). v3.2.2 (Mar 31 mesa) didn't have this feature
so games worked; v3.3.0 (Apr 17 mesa) did and froze. Confirmed live on Reanimal:
disabling the feature makes the game run again.

Until upstream resolves the underlying A8xx 64-bit image atomic implementation,
this workaround keeps WN-Turnip usable on UE5 / D3D12 SM6.6 titles.

Idempotent.
"""

import sys

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"

with open(DEVICES_PY, "r") as f:
    content = f.read()

count = content.count("has_64b_image_atomics = True,")
if count == 0:
    if "has_64b_image_atomics = False," in content:
        print(f"  {DEVICES_PY}: has_64b_image_atomics already disabled")
    else:
        print(f"  WARNING: {DEVICES_PY}: has_64b_image_atomics line not found", file=sys.stderr)
    sys.exit(0)

content = content.replace(
    "has_64b_image_atomics = True,",
    "has_64b_image_atomics = False,"
)

with open(DEVICES_PY, "w") as f:
    f.write(content)

print(f"  {DEVICES_PY}: disabled has_64b_image_atomics ({count} occurrences)")
print("disable_64b_image_atomics.py: done")

#!/usr/bin/env python3
"""
Compute shared memory stays at 32 KiB on A8xx.

This script used to apply whitebelyash/mesa-unified turnip/gen8 commit dcbb41b2
("freedreno/common: increase shared mem size"), which raised every
`cs_shared_mem_size = 32 * 1024` to `64 * 1024`, so the A8xx driver reported
maxComputeSharedMemorySize = 65536.

On an Adreno 830 (AYANEO Pocket FIT Elite, 2026-11-04) that is wrong: Vulkan CTS
dEQP-VK.compute.pipeline.workgroup_memory_explicit_layout.size.49152 and size.65536
fail ("compute failed") while size.8 ... size.32768 pass, and Qualcomm's own driver
(512.800.48) reports 32768. Shaders that use more than 32 KiB of shared memory got
wrong results. The other A8xx GPUs are not verified, so all of them keep 32 KiB.

Now the script only makes sure no CHIP.A8XX entry reports more than 32 KiB (it
lowers any that do) and fails the build if the result is not valid Python.
Mesh shader emulation (winnative 0001) still turns on: it needs >= 32 KiB.

Runs from turnip_workdir/mesa (paths relative to Mesa source root).
Idempotent.
"""
import re
import sys

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"
LIMIT = 32 * 1024

with open(DEVICES_PY) as f:
    src = f.read()

starts = [m.start() for m in re.finditer(r"^add_gpus\(", src, re.M)]
if not starts:
    print("a8xx_shared_mem.py: FATAL no add_gpus( blocks in freedreno_devices.py", file=sys.stderr)
    sys.exit(1)

size_re = re.compile(r"cs_shared_mem_size = (\d+) \* 1024")
out = [src[: starts[0]]]
a8 = lowered = 0
for i, st in enumerate(starts):
    end = starts[i + 1] if i + 1 < len(starts) else len(src)
    block = src[st:end]
    if "CHIP.A8XX" in block:
        a8 += 1

        def clamp(m):
            global lowered
            if int(m.group(1)) * 1024 > LIMIT:
                lowered += 1
                return f"cs_shared_mem_size = {LIMIT // 1024} * 1024"
            return m.group(0)

        block = size_re.sub(clamp, block)
    out.append(block)
src = "".join(out)

try:
    compile(src, DEVICES_PY, "exec")
except SyntaxError as e:
    print(f"a8xx_shared_mem.py: FATAL syntax error after edit at line {e.lineno}: {e.msg}", file=sys.stderr)
    sys.exit(1)

if a8 == 0:
    print("a8xx_shared_mem.py: no CHIP.A8XX entries - nothing to check")
else:
    big = [int(m.group(1)) for blk in src.split("add_gpus(")[1:] if "CHIP.A8XX" in blk
           for m in size_re.finditer(blk) if int(m.group(1)) * 1024 > LIMIT]
    if big:
        print(f"a8xx_shared_mem.py: FATAL A8XX entries still above 32 KiB: {big}", file=sys.stderr)
        sys.exit(1)

with open(DEVICES_PY, "w") as f:
    f.write(src)

print(f"a8xx_shared_mem.py: {a8} A8XX entries, compute shared memory 32 KiB ({lowered} lowered)")

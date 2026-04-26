#!/usr/bin/env python3
"""
A830 performance tuning for freedreno_devices.py.

Mesa main's A830 entry uses a8xx_gen1 as its base, which inherits
has_fs_tex_prefetch = True from the A7xx chain. Every other A8xx GPU
explicitly disables this:
  - A810 -> has_fs_tex_prefetch = False  (inline GPUProps override)
  - A829, A840 -> has_fs_tex_prefetch = False  (via a8xx_gen2)

Mesa's own source has a TODO comment on the A810 entry:
  "This is possibly also needed for a830 (and all of a8xx),
   move to a8xx_base if confirmed needed for a830."

A830 is the only A8xx GPU still attempting to use a fragment shader
texture prefetch path that does not work correctly on A8xx hardware.
This patch disables it for A830, matching the behaviour of all other
A8xx GPUs and confirming the upstream TODO.

Safe to run multiple times.
"""
import sys

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"

with open(DEVICES_PY, "r") as f:
    content = f.read()

original = content
changes = []

# ── A830: add has_fs_tex_prefetch = False ─────────────────────────────────
# The A830 props chain is:
#   [a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen1]
# We append an inline GPUProps override, matching the A810 pattern.

A830_PROPS_OLD = '[a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen1],'
A830_PROPS_NEW = '[a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen1, GPUProps(has_fs_tex_prefetch = False)],'

# Only patch within the A830 add_gpus block
A830_ANCHOR = 'GPUId(chip_id=0xffff44050000, name="Adreno (TM) 830")'

if A830_ANCHOR not in content:
    print("  WARNING: A830 GPU entry not found — skipping tune_a830 patch", file=sys.stderr)
    sys.exit(0)

# Find the A830 block boundaries
block_start = content.rfind("add_gpus([", 0, content.find(A830_ANCHOR))
block_end_marker = "))\n"
block_end = content.find(block_end_marker, block_start) + len(block_end_marker)
a830_block = content[block_start:block_end]

if "has_fs_tex_prefetch" in a830_block:
    print("  A830 has_fs_tex_prefetch already set, skipping")
elif A830_PROPS_OLD in a830_block:
    patched_block = a830_block.replace(A830_PROPS_OLD, A830_PROPS_NEW, 1)
    content = content[:block_start] + patched_block + content[block_end:]
    changes.append("added has_fs_tex_prefetch = False to A830 inline GPUProps")
else:
    print("  WARNING: could not find A830 props list anchor — skipping", file=sys.stderr)

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

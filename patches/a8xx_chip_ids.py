#!/usr/bin/env python3
"""
Idempotent A8xx chip_id wildcards for freedreno_devices.py.

Several A8xx GPUs ship with more than one patch revision in the chip_id
(A840: 0x44050A01 in the upstream kernel catalog, 0x44050A21 on retail
SM8850 phones, 0x44050A31 in Mesa; A829: 0x44030A00 / 0x44030A20).
dev_id_compare() treats a table entry whose low byte is 0xff as a wildcard
for the patch revision, and 0xffff in bits 47..32 as a wildcard for the
fuse id, so one entry per GPU covers every revision reported by KGSL or msm.

Safe to run multiple times.
"""
import re
import sys

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"

# (anchor chip_id already in the table, wildcard to add, name)
WILDCARDS = [
    ("0xffff44050a31", "0xffff44050AFF", "Adreno (TM) 840"),
    ("0x44030a20",     "0xffff44030AFF", "Adreno (TM) 829"),
]

with open(DEVICES_PY, "r") as f:
    content = f.read()

changed = False
for anchor, wildcard, name in WILDCARDS:
    if re.search(rf"chip_id={wildcard}\b", content, re.IGNORECASE):
        print(f"  {name} wildcard {wildcard} already present, skipping")
        continue
    m = re.search(rf'^(\s*)GPUId\(chip_id={anchor}, name="[^"]*"\),[^\n]*\n', content,
                  re.IGNORECASE | re.MULTILINE)
    if not m:
        print(f"  FATAL: {name} entry ({anchor}) not found", file=sys.stderr)
        sys.exit(1)
    # Append at the end of the GPUId list, so exact entries keep priority
    end = re.compile(r'^\s*\], A6xxGPUInfo\(', re.MULTILINE).search(content, m.end())
    if not end:
        print(f"  FATAL: end of the {name} GPUId list not found", file=sys.stderr)
        sys.exit(1)
    line = f'{m.group(1)}GPUId(chip_id={wildcard}, name="{name}"), # any patch revision\n'
    content = content[:end.start()] + line + content[end.start():]
    print(f"  Added {name} wildcard {wildcard}")
    changed = True

if changed:
    try:
        compile(content, DEVICES_PY, "exec")
    except SyntaxError as e:
        print(f"  FATAL: syntax error after patching at line {e.lineno}: {e.msg}", file=sys.stderr)
        sys.exit(1)
    with open(DEVICES_PY, "w") as f:
        f.write(content)

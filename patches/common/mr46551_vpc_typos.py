#!/usr/bin/env python3
"""Mesa MR 46551 (Artem Peshkov, open since 2026-11-20): two typos in the A8xx VPC cache
groups that Mesa d60076223315 "freedreno/common: Rework gen8 VPC GMEM cache" (MR 46240)
introduced:
  a8xx_vpc_cache_lg  sysmem_vpc_pos_buf_size = 65 * 1024 -> 64 * 1024 (the old 65536; the
                     MR reports a GPU hang in every app on an Adreno 840 with 65 * 1024)
  a8xx_vpc_cache_med sysmem_vpc_pos_buf_size = 48 * 102  -> 48 * 1024 (4896 -> 49152 bytes)
Every driver gets it (the groups are upstream Mesa: A829, A830/A831, A840, X2 in Standard too).
Fixes only what is still wrong, then asserts the result, so it turns into a check once
Mesa merges the MR. A Mesa without the groups (older than d6007622) needs nothing.
Run from the Mesa source root.
"""
import re
import sys
from pathlib import Path

p = Path("src/freedreno/common/freedreno_devices.py")
s = p.read_text()
if "a8xx_vpc_cache_lg = GPUProps(" not in s:
    print("[mr46551] no A8xx VPC cache groups in this Mesa (older than d6007622): nothing to do")
    sys.exit(0)

def group(name):
    m = re.search(r"(?ms)^%s = GPUProps\(\n(.*?)^\)" % name, s)
    if not m:
        sys.exit(f"[mr46551] {name} not found")
    return m

fixes = [("a8xx_vpc_cache_lg", "sysmem_vpc_pos_buf_size = 65 * 1024,", "sysmem_vpc_pos_buf_size = 64 * 1024,"),
         ("a8xx_vpc_cache_med", "sysmem_vpc_pos_buf_size = 48 * 102,", "sysmem_vpc_pos_buf_size = 48 * 1024,")]
for name, bad, good in fixes:
    m = group(name)
    body = m.group(1)
    if bad in body:
        s = s[:m.start(1)] + body.replace(bad, good) + s[m.end(1):]
        print(f"[mr46551] {name}: {bad} -> {good}")
    elif good in body:
        print(f"[mr46551] {name}: already {good} (upstream has the fix)")
    else:
        sys.exit(f"[mr46551] {name}: sysmem_vpc_pos_buf_size is neither the typo nor the fix; check Mesa")
p.write_text(s)
for name, _bad, good in fixes:
    if good not in group(name).group(1):
        sys.exit(f"[mr46551] {name}: fix did not land")

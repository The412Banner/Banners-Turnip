#!/usr/bin/env python3
"""
Keep a8xx_base supports_double_threadsize = False (Mesa's own value) after the gen8 stack.

gen8 commit "freedreno/common: update a8xx family configs" (DVD, 2026-04-15) turns it on. With it on, the
subgroup and reconvergence compute tests fail on an Adreno 830 (660 of 660 tested: subgroupAdd and the other
arithmetic, shuffle / rotate, clustered, ballot broadcast, uniform control flow), while Mesa's own value passes
629 of them; the Qualcomm driver passes all. Found 2026-11-05 by leaving each of the 14 gen8 commits out in
turn. Speed with it off, DriverLab 10 scenes: within +-1.5 %, compute unchanged.

Runs from the Mesa tree after a8xx_gen8.patch. Only the a8xx_base block is changed (A6xx / A7xx entries keep
theirs); fails if that block does not have exactly one `supports_double_threadsize = True,`.
"""
import sys

p = "src/freedreno/common/freedreno_devices.py"
s = open(p).read()
a = s.find("a8xx_base = GPUProps(")
b = s.find("\na8xx_base_raw_magic_regs", a)
if a < 0 or b < 0:
    sys.exit("a8xx_no_double_threadsize.py: a8xx_base block not found")
block = s[a:b]
n = block.count("supports_double_threadsize = True,")
if n != 1:
    sys.exit(f"a8xx_no_double_threadsize.py: expected one 'supports_double_threadsize = True,' in a8xx_base, found {n}")
s = s[:a] + block.replace("supports_double_threadsize = True,", "supports_double_threadsize = False,") + s[b:]
compile(s, p, "exec")
open(p, "w").write(s)
print("a8xx_no_double_threadsize.py: a8xx_base supports_double_threadsize = False")

#!/usr/bin/env python3
"""LAB ONLY (branch lab/aio-a8xx-ab): put a8xx_base supports_double_threadsize back to False (Mesa's own value).
gen8 commit 6 ("freedreno/common: update a8xx family configs", DVD) turns it on; with it on, the subgroup /
reconvergence compute CTS tests fail on the Adreno 830. Run from the Mesa tree after the gen8 stack."""
import sys
p = "src/freedreno/common/freedreno_devices.py"
s = open(p).read()
a = s.find("a8xx_base = GPUProps(")
b = s.find("\na8xx_base_raw_magic_regs", a)
if a < 0 or b < 0:
    sys.exit("a8xx_no_double_threadsize.py: a8xx_base block not found")
block = s[a:b]
if block.count("supports_double_threadsize = True,") != 1:
    sys.exit(f"a8xx_no_double_threadsize.py: expected one 'supports_double_threadsize = True,' in a8xx_base, "
             f"found {block.count('supports_double_threadsize = True,')}")
s = s[:a] + block.replace("supports_double_threadsize = True,", "supports_double_threadsize = False,") + s[b:]
compile(s, p, "exec")
open(p, "w").write(s)
print("a8xx_no_double_threadsize.py: a8xx_base supports_double_threadsize = False")

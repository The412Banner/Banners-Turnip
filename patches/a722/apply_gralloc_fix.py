#!/usr/bin/env python3
"""
Applies 01-u_gralloc-newer-qcom-handle.patch to the Mesa tree (run with cwd = Mesa) and fails the
build if it does not apply cleanly. EXTRA_PATCH only warns on a failed patch; this does not.

The patch: newer Qualcomm grallocs (seen on the Retroid Pocket Duo, Adreno 722, Android 14) no
longer put the 'gmsm' magic in their buffer handles, so upstream treats every gralloc buffer as
linear and a UBWC buffer comes out scrambled. The patch keeps the old path and adds a strict second
one that recognizes the newer layout by its format and aligned width, then reads the UBWC flag.
"""
import os
import subprocess
import sys

patch = os.path.join(os.path.dirname(os.path.abspath(__file__)), "01-u_gralloc-newer-qcom-handle.patch")
target = "src/util/u_gralloc/u_gralloc_fallback.c"

src = open(target).read()
if "Newer Qualcomm grallocs" in src:
    print("[a722] gralloc fix already present, skipping")
    sys.exit(0)

r = subprocess.run(["git", "apply", "--verbose", patch], capture_output=True, text=True)
print(r.stdout + r.stderr, end="")
if r.returncode != 0 or "Newer Qualcomm grallocs" not in open(target).read():
    print("[a722] FATAL: gralloc fix did not apply", file=sys.stderr)
    sys.exit(1)
print("[a722] gralloc fix applied")

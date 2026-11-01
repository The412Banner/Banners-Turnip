#!/usr/bin/env python3
"""A722 lab: runs the experiment steps named in LAB_STEPS (colon-separated) on the Mesa tree.

build_turnip.sh runs this from the Mesa source dir (EXTRA_SCRIPT). Each step is either
steps/<name>.py (run with cwd = Mesa) or steps/<name>.patch (git apply, must apply cleanly).
An empty LAB_STEPS builds pure upstream Mesa.
"""
import os
import runpy
import subprocess
import sys

here = os.path.dirname(os.path.abspath(__file__))
steps = [s for s in os.environ.get("LAB_STEPS", "").split(":") if s]
for s in steps:
    py = os.path.join(here, "steps", s + ".py")
    pa = os.path.join(here, "steps", s + ".patch")
    if os.path.exists(py):
        print(f"[lab] step {s}")
        runpy.run_path(py, run_name="__main__")
    elif os.path.exists(pa):
        print(f"[lab] patch {s}")
        subprocess.run(["git", "apply", "--check", pa], check=True)
        subprocess.run(["git", "apply", pa], check=True)
    else:
        sys.exit(f"[lab] unknown step {s}")
print("[lab] steps:", ":".join(steps) if steps else "none (pure upstream)")

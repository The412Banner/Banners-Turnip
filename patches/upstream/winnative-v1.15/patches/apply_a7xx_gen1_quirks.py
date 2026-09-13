#!/usr/bin/env python3
"""
WN-Turnip A7xx_gen1 quirks for A720 / A725 / A730.

Upstream a7xx_gen1 inherits has_early_preamble=True and has_scalar_predicates=True
from a7xx_base. Both cause visual regressions and compute hangs on shipped
A720/A725/A730 silicon. We override them to False in the a7xx_gen1 props block
only — A7xx_gen2 (A740 / X1-85) and A7xx_gen3 (A750+, the A8xx base) are
unaffected because they do not select a7xx_gen1.

Idempotent.
"""
import sys

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"

with open(DEVICES_PY, "r") as f:
    content = f.read()

OLD = (
    "a7xx_gen1 = GPUProps(\n"
    "        supports_uav_ubwc = True,\n"
    "        fs_must_have_non_zero_constlen_quirk = True,\n"
    "        enable_tp_ubwc_flag_hint = True,\n"
    "        reading_shading_rate_requires_smask_quirk = True,\n"
    "        cs_lock_unlock_quirk = True,\n"
    "    )"
)
NEW = (
    "a7xx_gen1 = GPUProps(\n"
    "        supports_uav_ubwc = True,\n"
    "        fs_must_have_non_zero_constlen_quirk = True,\n"
    "        enable_tp_ubwc_flag_hint = True,\n"
    "        reading_shading_rate_requires_smask_quirk = True,\n"
    "        cs_lock_unlock_quirk = True,\n"
    "        has_early_preamble = False,\n"
    "        has_scalar_predicates = False,\n"
    "    )"
)

if NEW in content:
    print(f"  {DEVICES_PY}: a7xx_gen1 quirks already applied")
elif OLD in content:
    content = content.replace(OLD, NEW, 1)
    try:
        compile(content, DEVICES_PY, "exec")
    except SyntaxError as e:
        print(f"  FATAL: syntax error after patching at line {e.lineno}: {e.msg}", file=sys.stderr)
        sys.exit(1)
    with open(DEVICES_PY, "w") as f:
        f.write(content)
    print(f"  {DEVICES_PY}: appended has_early_preamble=False, has_scalar_predicates=False to a7xx_gen1")
else:
    print(f"  WARNING: a7xx_gen1 anchor not matched, skipping", file=sys.stderr)

print("apply_a7xx_gen1_quirks.py: done")

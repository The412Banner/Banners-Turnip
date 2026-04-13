#!/usr/bin/env python3
"""
MTR GMEM force patch for tu_cmd_buffer.cc.
Injects 'return false' at the top of use_sysmem_rendering() so the driver
always uses on-chip tile memory (GMEM) instead of falling back to system RAM.
Idempotent — safe to run multiple times.
"""
import sys

PATH = "src/freedreno/vulkan/tu_cmd_buffer.cc"

with open(PATH, "r") as f:
    content = f.read()

GUARD = "/* MTR: Force GMEM */"
if GUARD in content:
    print("MTR GMEM force already applied, skipping.")
    sys.exit(0)

# Find the opening of use_sysmem_rendering function body.
# The function signature is:
#   static bool
#   use_sysmem_rendering(struct tu_cmd_buffer *cmd,
#                        struct tu_renderpass_result **autotune_result)
#   {
FN = "use_sysmem_rendering"
fn_idx = content.find(FN)
if fn_idx == -1:
    print(f"ERROR: '{FN}' not found in {PATH}", file=sys.stderr)
    sys.exit(1)

# Find the opening brace of the function body (first '{' after the function name)
brace_idx = content.find("{", fn_idx)
if brace_idx == -1:
    print(f"ERROR: Opening brace not found after '{FN}'", file=sys.stderr)
    sys.exit(1)

inject = (
    "\n"
    "   /* MTR: Force GMEM — always use on-chip tile memory */\n"
    "   return false;\n"
)

new_content = content[:brace_idx + 1] + inject + content[brace_idx + 1:]

with open(PATH, "w") as f:
    f.write(new_content)

print(f"MTR: Applied GMEM force patch to {PATH}")

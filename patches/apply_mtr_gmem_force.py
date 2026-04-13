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

# Find the function DEFINITION specifically, not a call site.
# The definition is preceded by the return type on the previous line:
#   static bool
#   use_sysmem_rendering(...)
#   {
# We search for "static bool" followed (within ~300 chars) by "use_sysmem_rendering".
import re

# Match the pattern: static bool <whitespace> use_sysmem_rendering ... {
m = re.search(
    r'static\s+bool\s+use_sysmem_rendering\s*\([^)]*\)\s*\{',
    content,
    re.DOTALL
)
if not m:
    # Fallback: multiline signature (params span multiple lines)
    m = re.search(
        r'static\s+bool\s*\n\s*use_sysmem_rendering\b',
        content
    )
    if not m:
        print("ERROR: use_sysmem_rendering function definition not found", file=sys.stderr)
        sys.exit(1)
    # Find the opening brace of this definition
    brace_idx = content.find("{", m.start())
    if brace_idx == -1:
        print("ERROR: Opening brace not found after use_sysmem_rendering", file=sys.stderr)
        sys.exit(1)
else:
    # m matched through the opening brace — inject after it
    brace_idx = m.end() - 1  # position of '{'

inject = (
    "\n"
    "   /* MTR: Force GMEM — always use on-chip tile memory */\n"
    "   return false;\n"
)

new_content = content[:brace_idx + 1] + inject + content[brace_idx + 1:]

with open(PATH, "w") as f:
    f.write(new_content)

print(f"MTR: Applied GMEM force patch to {PATH}")

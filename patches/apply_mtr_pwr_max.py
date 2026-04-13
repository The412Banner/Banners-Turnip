#!/usr/bin/env python3
"""
MTR PWR_MAX patch for tu_knl_kgsl.cc.

Uses KGSL's KGSL_PROP_PWR_CONSTRAINT ioctl to lock the GPU to its maximum
power level. Applied once at KGSL context creation (device init). Sufficient
for Winlator's always-active GPU context; KGSL will hold the constraint for
the lifetime of the context.

Idempotent — safe to run multiple times.
"""
import sys
import re

PATH = "src/freedreno/vulkan/tu_knl_kgsl.cc"

with open(PATH, "r") as f:
    content = f.read()

GUARD = "/* MTR: PWR_MAX */"
if GUARD in content:
    print("MTR PWR_MAX already applied, skipping.")
    sys.exit(0)

# ── Step 1: add #include <atomic> if needed ──────────────────────────────────

if "#include <atomic>" not in content:
    m = re.search(r'^#include\s+[<"]', content, re.MULTILINE)
    if m:
        end = content.find("\n", m.start()) + 1
        content = content[:end] + "#include <atomic>\n" + content[end:]

# ── Step 2: inject defines + helper after the last #include ──────────────────

DEFINES = """
/* MTR: PWR_MAX — KGSL power constraint */
#define MTR_KGSL_PROP_PWR_CONSTRAINT       0x18
#define MTR_KGSL_CONSTRAINT_PWRLEVEL       0x1
#define MTR_KGSL_CONSTRAINT_PWR_MAX        0x1
#define MTR_IOCTL_KGSL_DEVICE_SETPROPERTY  _IOW(0x09, 0x14, struct mtr_kgsl_setprop)

struct mtr_kgsl_pwr_constraint {
   unsigned int type;
   unsigned int sub_type;
   unsigned int level;
   unsigned int id;
};

struct mtr_kgsl_setprop {
   unsigned int type;
   void        *value;
   size_t       sizebytes;
};

static void
mtr_kgsl_set_pwr_max(int kgsl_fd, unsigned int ctx_id)
{
   /* MTR: PWR_MAX — lock GPU to highest frequency via KGSL power constraint */
   struct mtr_kgsl_pwr_constraint pwr = {};
   pwr.type     = MTR_KGSL_CONSTRAINT_PWRLEVEL;
   pwr.sub_type = MTR_KGSL_CONSTRAINT_PWR_MAX;
   pwr.level    = 0;
   pwr.id       = ctx_id;

   struct mtr_kgsl_setprop prop = {};
   prop.type      = MTR_KGSL_PROP_PWR_CONSTRAINT;
   prop.value     = &pwr;
   prop.sizebytes = sizeof(pwr);

   if (ioctl(kgsl_fd, MTR_IOCTL_KGSL_DEVICE_SETPROPERTY, &prop) != 0) {
      mesa_logw("MTR: Failed to set initial PWR_MAX constraint: %s", strerror(errno));
   } else {
      mesa_logi("MTR: PWR_MAX constraint set (ctx=%u)", ctx_id);
   }
}
"""

last_include_end = 0
for m in re.finditer(r'^#include\s+[<"].*?[>"]\s*$', content, re.MULTILINE):
    last_include_end = m.end()

if last_include_end == 0:
    print(f"ERROR: No #include found in {PATH}", file=sys.stderr)
    sys.exit(1)

content = content[:last_include_end] + "\n" + DEFINES + content[last_include_end:]

# ── Step 3: inject PWR_MAX call after KGSL context creation ──────────────────
#
# After IOCTL_KGSL_DRAWCTXT_CREATE succeeds, the drawctxt_id field of the
# request struct holds the new context id. We inject our PWR_MAX call right
# after the ioctl call that creates the context.
#
# We look for the statement containing IOCTL_KGSL_DRAWCTXT_CREATE.
# It may span multiple lines so we use DOTALL matching.

m = re.search(
    r'(IOCTL_KGSL_DRAWCTXT_CREATE[^;]*;)',
    content,
    re.DOTALL
)
if not m:
    print(f"ERROR: IOCTL_KGSL_DRAWCTXT_CREATE not found in {PATH}", file=sys.stderr)
    sys.exit(1)

# Find the end of this statement and the line ending after it
stmt_end = m.end()  # position after the semicolon

# Find the newline at end of this statement
nl = content.find("\n", stmt_end)
if nl == -1:
    nl = len(content)

# Get indentation of the line containing the ioctl call
line_start = content.rfind("\n", 0, m.start()) + 1
indent = ""
for ch in content[line_start:]:
    if ch in (" ", "\t"):
        indent += ch
    else:
        break

# The req struct field for the new context id differs across Mesa versions.
# Try to detect which field name is used near the DRAWCTXT_CREATE call.
ctx_field = "drawctxt_id"  # most common
nearby = content[max(0, m.start() - 400):m.end() + 400]
if "context_id" in nearby and "drawctxt_id" not in nearby:
    ctx_field = "context_id"

# We also need the fd variable name — look for the ioctl first arg
ioctl_line = content[line_start:stmt_end]
fd_match = re.search(r'(?:ioctl|drmIoctl)\s*\(\s*([^,\n]+?)\s*,', ioctl_line)
fd_expr = fd_match.group(1).strip() if fd_match else "device->fd"

INJECT = (
    f"\n{indent}/* MTR: PWR_MAX — set power constraint right after context creation */\n"
    f"{indent}mtr_kgsl_set_pwr_max({fd_expr}, req.{ctx_field});\n"
)

content = content[:nl] + INJECT + content[nl:]

with open(PATH, "w") as f:
    f.write(content)

print(f"MTR: Applied PWR_MAX patch to {PATH}")
print(f"     Helper injected after last #include")
print(f"     PWR_MAX call injected after IOCTL_KGSL_DRAWCTXT_CREATE "
      f"(fd={fd_expr}, ctx=req.{ctx_field})")

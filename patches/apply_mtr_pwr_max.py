#!/usr/bin/env python3
"""
MTR PWR_MAX patch for tu_knl_kgsl.cc.

Uses KGSL's KGSL_PROP_PWR_CONSTRAINT ioctl to lock the GPU to its maximum
power level. Refreshed every 1000 command buffer submissions.

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

# ── Step 1: add #include <atomic> if not already present ────────────────────

if "#include <atomic>" not in content:
    # Inject after the first #include line
    m = re.search(r'^#include\s+[<"]', content, re.MULTILINE)
    if m:
        end = content.find("\n", m.start()) + 1
        content = content[:end] + "#include <atomic>\n" + content[end:]

# ── Step 2: inject defines + helper after the last #include ─────────────────

DEFINES = """
/* MTR: PWR_MAX — KGSL power constraint definitions */
#define MTR_KGSL_PROP_PWR_CONSTRAINT    0x18
#define MTR_KGSL_CONSTRAINT_PWRLEVEL    0x1
#define MTR_KGSL_CONSTRAINT_PWR_MAX     0x1
#define MTR_IOCTL_KGSL_DEVICE_SETPROPERTY _IOW(0x09, 0x14, struct mtr_kgsl_setprop)

struct mtr_kgsl_pwr_constraint {
   unsigned int type;
   unsigned int sub_type;
   unsigned int level;
   unsigned int id;  /* context id — 0 applies to all contexts */
};

struct mtr_kgsl_setprop {
   unsigned int type;
   void        *value;
   size_t       sizebytes;
};

/* MTR: per-process submission counter */
static std::atomic<uint32_t> mtr_submit_count{0};

static void
mtr_kgsl_set_pwr_max(int kgsl_fd, unsigned int ctx_id)
{
   struct mtr_kgsl_pwr_constraint pwr = {};
   pwr.type     = MTR_KGSL_CONSTRAINT_PWRLEVEL;
   pwr.sub_type = MTR_KGSL_CONSTRAINT_PWR_MAX;
   pwr.level    = 0;   /* 0 = highest frequency tier */
   pwr.id       = ctx_id;

   struct mtr_kgsl_setprop prop = {};
   prop.type      = MTR_KGSL_PROP_PWR_CONSTRAINT;
   prop.value     = &pwr;
   prop.sizebytes = sizeof(pwr);

   if (ioctl(kgsl_fd, MTR_IOCTL_KGSL_DEVICE_SETPROPERTY, &prop) != 0) {
      static bool warned = false;
      if (!warned) {
         mesa_logw("MTR: Failed to set initial PWR_MAX constraint: %s", strerror(errno));
         warned = true;
      }
   }
}
"""

# Find last #include and inject after it
last_include_end = 0
for m in re.finditer(r'^#include\s+[<"].*?[>"]\s*$', content, re.MULTILINE):
    last_include_end = m.end()

if last_include_end == 0:
    print(f"ERROR: No #include found in {PATH}", file=sys.stderr)
    sys.exit(1)

content = content[:last_include_end] + "\n" + DEFINES + content[last_include_end:]

# ── Step 3: find the actual ioctl() submit call site ─────────────────────────
#
# We look for ioctl() or drmIoctl() calls that contain IOCTL_KGSL_GPU_COMMAND
# on the SAME line (not a #define). The submit function uses a local 'req'
# struct of type kgsl_gpu_command; req.context_id holds the KGSL context id.
#
# Pattern: optional_whitespace ioctl/drmIoctl ( ... IOCTL_KGSL_GPU_COMMAND ... ) ;

m = re.search(
    r'^([ \t]+(?:ret\s*=\s*)?(?:ioctl|drmIoctl)\s*\([^;]*IOCTL_KGSL_GPU_COMMAND[^;]*;)',
    content,
    re.MULTILINE
)
if not m:
    print(f"ERROR: ioctl call with IOCTL_KGSL_GPU_COMMAND not found in {PATH}",
          file=sys.stderr)
    sys.exit(1)

# Get indentation of the ioctl line
line_start = m.start()
indent = ""
for ch in content[line_start:]:
    if ch in (" ", "\t"):
        indent += ch
    else:
        break

# We need the fd argument. In Mesa KGSL backend the ioctl is called as:
#   ioctl(fd, IOCTL_KGSL_GPU_COMMAND, &req)
# or
#   drmIoctl(dev->fd, IOCTL_KGSL_GPU_COMMAND, &req)
# Extract the first argument name by looking at the call.
call_text = m.group(1)
fd_match = re.search(r'(?:ioctl|drmIoctl)\s*\(\s*([^,]+?)\s*,', call_text)
fd_expr = fd_match.group(1).strip() if fd_match else "queue->device->fd"

REFRESH_CODE = (
    f"{indent}/* MTR: PWR_MAX refresh every 1000 submissions */\n"
    f"{indent}{{\n"
    f"{indent}   auto _mtr_n = mtr_submit_count.fetch_add(1, std::memory_order_relaxed);\n"
    f"{indent}   if (_mtr_n % 1000 == 0)\n"
    f"{indent}      mtr_kgsl_set_pwr_max({fd_expr}, req.context_id);\n"
    f"{indent}}}\n"
)

content = content[:line_start] + REFRESH_CODE + content[line_start:]

with open(PATH, "w") as f:
    f.write(content)

print(f"MTR: Applied PWR_MAX patch to {PATH}")
print(f"     Defines + helper injected after last #include")
print(f"     Submit refresh injected before ioctl call (fd={fd_expr}, ctx=req.context_id)")

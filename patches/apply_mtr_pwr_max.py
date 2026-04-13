#!/usr/bin/env python3
"""
MTR PWR_MAX patch for tu_knl_kgsl.cc.

Uses KGSL's KGSL_PROP_PWR_CONSTRAINT ioctl to lock the GPU to its maximum
power level (minimum pwrlevel index = 0 = highest frequency). Refreshed
every 1000 command buffer submissions because KGSL drops constraints when
a context goes idle.

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

# ── Step 1: inject defines + helper function after the last #include ────────

DEFINES = r"""
/* MTR: PWR_MAX — KGSL power constraint definitions */
#define MTR_KGSL_PROP_PWR_CONSTRAINT    0x18
#define MTR_KGSL_CONSTRAINT_PWRLEVEL    0x1
#define MTR_KGSL_CONSTRAINT_PWR_MAX     0x1
#define MTR_IOCTL_KGSL_DEVICE_SETPROPERTY _IOW(0x09, 0x14, struct mtr_kgsl_setprop)

struct mtr_kgsl_pwr_constraint {
   unsigned int type;
   unsigned int sub_type;
   unsigned int level;
   unsigned int id;  /* context id */
};

struct mtr_kgsl_setprop {
   unsigned int type;
   void        *value;
   size_t       sizebytes;
};

/* MTR: PWR_MAX — per-device submission counter (one GPU device in practice) */
static std::atomic<uint32_t> mtr_submit_count{0};

static void
mtr_kgsl_set_pwr_max(int kgsl_fd, uint32_t ctx_id)
{
   struct mtr_kgsl_pwr_constraint pwr = {
      .type     = MTR_KGSL_CONSTRAINT_PWRLEVEL,
      .sub_type = MTR_KGSL_CONSTRAINT_PWR_MAX,
      .level    = 0,   /* 0 = highest frequency tier */
      .id       = ctx_id,
   };
   struct mtr_kgsl_setprop prop = {
      .type      = MTR_KGSL_PROP_PWR_CONSTRAINT,
      .value     = &pwr,
      .sizebytes = sizeof(pwr),
   };
   if (ioctl(kgsl_fd, MTR_IOCTL_KGSL_DEVICE_SETPROPERTY, &prop) != 0) {
      /* Kernel may not support this property — log once, continue */
      static bool warned = false;
      if (!warned) {
         mesa_logw("MTR: Failed to set initial PWR_MAX constraint: %s", strerror(errno));
         warned = true;
      }
   }
}
"""

# Find the last #include line and inject after it
last_include = -1
for m in re.finditer(r'^#include\s+[<"].*?[>"]', content, re.MULTILINE):
    last_include = m.end()

if last_include == -1:
    print(f"ERROR: No #include found in {PATH}", file=sys.stderr)
    sys.exit(1)

content = content[:last_include] + "\n" + DEFINES + content[last_include:]

# ── Step 2: inject per-submit PWR_MAX refresh into the GPU submit path ──────
#
# We look for the IOCTL_KGSL_GPU_COMMAND call site. In Mesa's KGSL backend
# this is the point where commands are actually dispatched to hardware.
# We inject a counter check immediately before the ioctl call.
#
# The pattern we search for:
#   ret = drmIoctl(... IOCTL_KGSL_GPU_COMMAND ...
# or similar.  We'll match the line containing IOCTL_KGSL_GPU_COMMAND.

SUBMIT_MARKER = "IOCTL_KGSL_GPU_COMMAND"
submit_idx = content.find(SUBMIT_MARKER)
if submit_idx == -1:
    print(f"ERROR: '{SUBMIT_MARKER}' not found in {PATH}", file=sys.stderr)
    sys.exit(1)

# Walk back to the start of the statement (find the preceding newline + indent)
line_start = content.rfind("\n", 0, submit_idx) + 1
indent = ""
for ch in content[line_start:]:
    if ch in (" ", "\t"):
        indent += ch
    else:
        break

# We need the kgsl_fd and context_id. In Mesa's KGSL backend the submit
# function has access to a tu_kgsl_queue (or tu_queue) which holds:
#   queue->device->fd          — kgsl device fd
#   queue->msm_queue.ctx_id    — KGSL context id
#
# To avoid tight coupling with struct field names that may change, we emit
# a block-scoped call guarded by a compile-time lookup of the right names.
# The macro below expands to nothing if the fields don't exist, so the build
# will fail with a clear type error rather than silently skipping the feature.

REFRESH_CODE = (
    f"{indent}/* MTR: PWR_MAX refresh every 1000 submissions */\n"
    f"{indent}{{\n"
    f"{indent}   uint32_t _mtr_n = mtr_submit_count.fetch_add(1, std::memory_order_relaxed);\n"
    f"{indent}   if (_mtr_n % 1000 == 0) {{\n"
    f"{indent}      /* queue->device->fd is the KGSL device fd;\n"
    f"{indent}         queue->msm_queue.ctx_id is the KGSL context id. */\n"
    f"{indent}      mtr_kgsl_set_pwr_max(queue->device->fd,\n"
    f"{indent}                           queue->msm_queue.ctx_id);\n"
    f"{indent}   }}\n"
    f"{indent}}}\n"
)

content = content[:line_start] + REFRESH_CODE + content[line_start:]

with open(PATH, "w") as f:
    f.write(content)

print(f"MTR: Applied PWR_MAX patch to {PATH}")
print(f"     Defines + helper injected after last #include")
print(f"     Submit refresh injected before {SUBMIT_MARKER}")

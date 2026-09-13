#!/usr/bin/env python3
"""
Apply aggressive autotune and variant-specific GPU clock forcing for performance
builds.

Supported BUILD_VARIANT modes:
- p:  Baseline PWR_MAX constraint with refresh every 1000 submissions
- p1: PWR_MAX constraint with 40 ms time-based refresh, piggybacked on submit
- p2: Experimental KGSL_PROP_PWRCTRL governor disable / turbo forcing
"""

import os
import re
import sys

KGSL_FILE = "src/freedreno/vulkan/tu_knl_kgsl.cc"
AUTOTUNE_FILE = "src/freedreno/vulkan/tu_autotune.cc"

BUILD_VARIANT = os.environ.get("BUILD_VARIANT", "p")
if BUILD_VARIANT not in {"p", "p1", "p2"}:
    print(f"Unsupported BUILD_VARIANT for perf script: {BUILD_VARIANT}", file=sys.stderr)
    sys.exit(1)


def replace_once(content: str, old: str, new: str, label: str) -> tuple[str, bool]:
    """Three-state edit per MAINTENANCE.md. Never returns silently.

    A silent no-op here used to be possible, and it is the worst outcome
    available: the -p zip would build and ship without PWR_MAX clock forcing,
    the CI drift check greps for "anchor absent" and would find nothing, and the
    variant would quietly be a -b with a different name.
    """
    if old in content:
        print(f"  {KGSL_FILE}: {label}")
        return content.replace(old, new, 1), True
    if new in content:
        print(f"  {KGSL_FILE}: {label} - already applied")
        return content, False
    print(f"  WARNING: {KGSL_FILE}: anchor absent for {label} "
          f"- upstream refactored? skipping", file=sys.stderr)
    return content, False


def ensure_regex(content: str, pattern: str, repl: str, label: str,
                 marker: str) -> tuple[str, bool]:
    """As replace_once, but the already-applied test needs an explicit marker
    because `repl` can carry backreferences."""
    updated, count = re.subn(pattern, repl, content, count=1, flags=re.MULTILINE)
    if count:
        print(f"  {KGSL_FILE}: {label}")
        return updated, True
    if marker in content:
        print(f"  {KGSL_FILE}: {label} - already applied")
        return content, False
    print(f"  WARNING: {KGSL_FILE}: anchor absent for {label} "
          f"- upstream refactored? skipping", file=sys.stderr)
    return content, False


with open(KGSL_FILE, "r") as f:
    kgsl = f.read()

kgsl_changed = False

if BUILD_VARIANT in {"p", "p1"}:
    old_ctx = """   struct kgsl_drawctxt_create req = {
      .flags = KGSL_CONTEXT_SAVE_GMEM |
              KGSL_CONTEXT_NO_GMEM_ALLOC |
              KGSL_CONTEXT_PREAMBLE,
   };"""
    new_ctx = """   struct kgsl_drawctxt_create req = {
      .flags = KGSL_CONTEXT_SAVE_GMEM |
              KGSL_CONTEXT_NO_GMEM_ALLOC |
              KGSL_CONTEXT_PREAMBLE | KGSL_CONTEXT_PWR_CONSTRAINT,
   };"""
    kgsl, changed = replace_once(
        kgsl,
        old_ctx,
        new_ctx,
        "added KGSL_CONTEXT_PWR_CONSTRAINT to context flags",
    )
    kgsl_changed |= changed

    helper_anchor = "static int\nsafe_ioctl(int fd, unsigned long request, void *arg)\n{\n"
    if "wnturnip_set_pwr_max_constraint(" not in kgsl:
        helper_block = """static int
wnturnip_set_pwr_max_constraint(int fd, uint32_t context_id)
{
   struct kgsl_device_constraint_pwrlevel pwrlevel = {
      .level = KGSL_CONSTRAINT_PWR_MAX,
   };
   struct kgsl_device_constraint constraint = {
      .type = KGSL_CONSTRAINT_PWRLEVEL,
      .context_id = context_id,
      .data = (void *)&pwrlevel,
      .size = sizeof(pwrlevel),
   };
   struct kgsl_device_getproperty prop = {
      .type = KGSL_PROP_PWR_CONSTRAINT,
      .value = (void *)&constraint,
      .sizebytes = sizeof(constraint),
   };

   return safe_ioctl(fd, IOCTL_KGSL_SETPROPERTY, &prop);
}

"""
        pos = kgsl.find("static int\nkgsl_submitqueue_new(")
        if pos != -1:
            kgsl = kgsl[:pos] + helper_block + kgsl[pos:]
            kgsl_changed = True
            print(f"  {KGSL_FILE}: inserted PWR_MAX helper")
        else:
            print(f"  WARNING: {KGSL_FILE}: anchor absent for the PWR_MAX helper "
                  f"insertion point - upstream refactored? skipping", file=sys.stderr)
    else:
        print(f"  {KGSL_FILE}: PWR_MAX helper - already applied")

    if BUILD_VARIANT == "p1" and "wnturnip_should_refresh_pwr_max_constraint(" not in kgsl:
        helper_block = """static bool
wnturnip_should_refresh_pwr_max_constraint(void)
{
   static int64_t last_pwr_refresh_ns = 0;
   static const int64_t pwr_refresh_interval_ns = 40 * 1000 * 1000;
   const int64_t now_ns = os_time_get_nano();
   const int64_t last_ns = p_atomic_read(&last_pwr_refresh_ns);

   if (last_ns != 0 && now_ns - last_ns < pwr_refresh_interval_ns)
      return false;

   return p_atomic_cmpxchg(&last_pwr_refresh_ns, last_ns, now_ns) == last_ns;
}

"""
        pos = kgsl.find("static int\nkgsl_submitqueue_new(")
        if pos != -1:
            kgsl = kgsl[:pos] + helper_block + kgsl[pos:]
            kgsl_changed = True
            print(f"  {KGSL_FILE}: inserted 40 ms refresh gate helper")
        else:
            print(f"  WARNING: {KGSL_FILE}: anchor absent for the 40 ms refresh gate "
                  f"helper insertion point - upstream refactored? skipping", file=sys.stderr)

    init_old = """   queue->msm_queue_id = req.drawctxt_id;\n\n   return 0;\n}"""
    init_new = """   queue->msm_queue_id = req.drawctxt_id;\n\n   /* WN-Turnip: Set PWR_MAX constraint to request maximum GPU clocks */\n   {\n      int pwr_ret = wnturnip_set_pwr_max_constraint(dev->physical_device->local_fd,\n                                               req.drawctxt_id);\n      if (pwr_ret)\n         mesa_logw(\"WN-Turnip: Failed to set initial PWR_MAX constraint: %s\", strerror(errno));\n   }\n\n   return 0;\n}"""
    if "Failed to set initial PWR_MAX constraint" not in kgsl:
        kgsl, changed = replace_once(
            kgsl,
            init_old,
            init_new,
            "inserted initial PWR_MAX constraint setup",
        )
        kgsl_changed |= changed
    else:
        print(f"  {KGSL_FILE}: initial PWR_MAX constraint setup - already applied")

    old_flags = ".flags = KGSL_CMDBATCH_SUBMIT_IB_LIST,"
    new_flags = ".flags = KGSL_CMDBATCH_SUBMIT_IB_LIST | KGSL_CMDBATCH_PWR_CONSTRAINT,"
    if "KGSL_CMDBATCH_PWR_CONSTRAINT" not in kgsl:
        kgsl, changed = replace_once(
            kgsl,
            old_flags,
            new_flags,
            "added KGSL_CMDBATCH_PWR_CONSTRAINT to submission flags",
        )
        kgsl_changed |= changed
    else:
        print(f"  {KGSL_FILE}: KGSL_CMDBATCH_PWR_CONSTRAINT - already applied")

    refresh_anchor = "      timestamp = req.timestamp;\n   } else {"
    if BUILD_VARIANT == "p" and "pwr_refresh_counter" not in kgsl:
        refresh_block = """      /* WN-Turnip: Periodically re-assert PWR_MAX to prevent downclocking */\n      static uint32_t pwr_refresh_counter = 0;\n      uint32_t count = p_atomic_inc_return(&pwr_refresh_counter);\n      if (count % 1000 == 0) {\n         int pwr_ret = wnturnip_set_pwr_max_constraint(\n               queue->device->physical_device->local_fd,\n               queue->msm_queue_id);\n         if (pwr_ret)\n            mesa_logw(\"WN-Turnip: PWR_MAX refresh failed at sub %u: %s\", count, strerror(errno));\n      }\n\n      timestamp = req.timestamp;\n   } else {"""
        kgsl, changed = replace_once(
            kgsl,
            refresh_anchor,
            refresh_block,
            "inserted periodic PWR_MAX refresh",
        )
        kgsl_changed |= changed

    elif BUILD_VARIANT == "p":
        print(f"  {KGSL_FILE}: periodic PWR_MAX refresh - already applied")
    if BUILD_VARIANT == "p1" and "wnturnip_should_refresh_pwr_max_constraint" in kgsl and "PWR_MAX refresh failed after %" not in kgsl:
        refresh_block = """      /* WN-Turnip: Re-assert PWR_MAX at most every 40 ms, piggybacked on submit */\n      if (wnturnip_should_refresh_pwr_max_constraint()) {\n         int pwr_ret = wnturnip_set_pwr_max_constraint(\n               queue->device->physical_device->local_fd,\n               queue->msm_queue_id);\n         if (pwr_ret)\n            mesa_logw(\"WN-Turnip: 40 ms PWR_MAX refresh failed: %s\", strerror(errno));\n      }\n\n      timestamp = req.timestamp;\n   } else {"""
        kgsl, changed = replace_once(
            kgsl,
            refresh_anchor,
            refresh_block,
            "inserted 40 ms time-based PWR_MAX refresh",
        )
        kgsl_changed |= changed

        bind_anchor = """         timestamp = req.timestamp;\n         i++;\n      }\n   }\n"""
        bind_block = """         if (wnturnip_should_refresh_pwr_max_constraint()) {\n            int pwr_ret = wnturnip_set_pwr_max_constraint(\n                  queue->device->physical_device->local_fd,\n                  queue->msm_queue_id);\n            if (pwr_ret)\n               mesa_logw(\"WN-Turnip: 40 ms PWR_MAX refresh failed: %s\", strerror(errno));\n         }\n\n         timestamp = req.timestamp;\n         i++;\n      }\n   }\n"""
        kgsl, changed = replace_once(
            kgsl,
            bind_anchor,
            bind_block,
            "added 40 ms refresh to aux/bind submissions",
        )
        kgsl_changed |= changed

if BUILD_VARIANT == "p2":
    if "wnturnip_set_pwrctrl_enabled(" not in kgsl:
        helper_block = """static int
wnturnip_set_pwrctrl_enabled(struct tu_device *dev, unsigned int enable)
{
   struct kgsl_device_getproperty prop = {
      .type = KGSL_PROP_PWRCTRL,
      .value = (void *)&enable,
      .sizebytes = sizeof(enable),
   };

   return safe_ioctl(dev->physical_device->local_fd, IOCTL_KGSL_SETPROPERTY, &prop);
}

static int32_t wnturnip_pwrctrl_force_users = 0;

"""
        pos = kgsl.find("static int\nkgsl_submitqueue_new(")
        if pos != -1:
            kgsl = kgsl[:pos] + helper_block + kgsl[pos:]
            kgsl_changed = True
            print(f"  {KGSL_FILE}: inserted PWRCTRL helper")

    init_old = "   queue->msm_queue_id = req.drawctxt_id;\n\n   return 0;\n}"
    init_new = """   queue->msm_queue_id = req.drawctxt_id;\n\n   /* WN-Turnip: Disable KGSL governor and force turbo while any queue is active */\n   if (p_atomic_inc_return(&wnturnip_pwrctrl_force_users) == 1) {\n      int pwr_ret = wnturnip_set_pwrctrl_enabled(dev, 0);\n      if (pwr_ret)\n         mesa_logw(\"WN-Turnip: Failed to disable KGSL governor via KGSL_PROP_PWRCTRL: %s\",\n                   strerror(errno));\n   }\n\n   return 0;\n}"""
    if "disable KGSL governor via KGSL_PROP_PWRCTRL" not in kgsl:
        kgsl, changed = replace_once(
            kgsl,
            init_old,
            init_new,
            "inserted KGSL_PROP_PWRCTRL governor disable on queue create",
        )
        kgsl_changed |= changed

    close_old = """static void\nkgsl_submitqueue_close(struct tu_device *dev, struct tu_queue *queue)\n{\n   struct kgsl_drawctxt_destroy req = {\n      .drawctxt_id = queue->msm_queue_id,\n   };\n\n   safe_ioctl(dev->physical_device->local_fd, IOCTL_KGSL_DRAWCTXT_DESTROY, &req);\n}"""
    close_new = """static void\nkgsl_submitqueue_close(struct tu_device *dev, struct tu_queue *queue)\n{\n   struct kgsl_drawctxt_destroy req = {\n      .drawctxt_id = queue->msm_queue_id,\n   };\n\n   if (p_atomic_dec_return(&wnturnip_pwrctrl_force_users) == 0) {\n      int pwr_ret = wnturnip_set_pwrctrl_enabled(dev, 1);\n      if (pwr_ret)\n         mesa_logw(\"WN-Turnip: Failed to re-enable KGSL governor via KGSL_PROP_PWRCTRL: %s\",\n                   strerror(errno));\n   }\n\n   safe_ioctl(dev->physical_device->local_fd, IOCTL_KGSL_DRAWCTXT_DESTROY, &req);\n}"""
    if "re-enable KGSL governor via KGSL_PROP_PWRCTRL" not in kgsl:
        kgsl, changed = replace_once(
            kgsl,
            close_old,
            close_new,
            "inserted KGSL_PROP_PWRCTRL governor restore on queue close",
        )
        kgsl_changed |= changed

if kgsl_changed:
    with open(KGSL_FILE, "w") as f:
        f.write(kgsl)

with open(AUTOTUNE_FILE, "r") as f:
    autotune = f.read()

at_changed = False

old_dc = "if (cmd_buffer->state.rp.drawcall_count > 5)"
new_dc = "if (cmd_buffer->state.rp.drawcall_count > 10)"
if new_dc in autotune:
    print(f"  {AUTOTUNE_FILE}: drawcall threshold already at 10")
elif old_dc in autotune:
    autotune = autotune.replace(old_dc, new_dc)
    at_changed = True
    print(f"  {AUTOTUNE_FILE}: raised drawcall threshold 5 -> 10")
else:
    print(f"  {AUTOTUNE_FILE}: '> 5' drawcall anchor absent (upstream restructured) — skipping threshold tweak")

old_bw = "gmem_bandwidth = (gmem_bandwidth * 11 + total_draw_call_bandwidth) / 10;"
new_bw = "gmem_bandwidth = (gmem_bandwidth * 10 + total_draw_call_bandwidth) / 10;"
if old_bw in autotune:
    autotune = autotune.replace(old_bw, new_bw)
    at_changed = True
    print(f"  {AUTOTUNE_FILE}: reduced bandwidth multiplier 11 -> 10")
elif "* 10 + total" in autotune:
    print(f"  {AUTOTUNE_FILE}: bandwidth multiplier already reduced")
else:
    print(f"  WARNING: {AUTOTUNE_FILE}: anchor absent for the bandwidth multiplier "
          f"- upstream refactored? skipping", file=sys.stderr)

if at_changed:
    with open(AUTOTUNE_FILE, "w") as f:
        f.write(autotune)

print(f"apply_perf_variant.py: done for BUILD_VARIANT={BUILD_VARIANT}")

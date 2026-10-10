# KGSL zero-timeout poll: a timeline "poll" that waited for the GPU

**Status:** fixed in Mesa `main` since 2026-10-08 (e984ef29 "tu/kgsl: Prevent indefinite wait times
for 0 timeout waits", MR 44838, crediting The412Banner). The patch this repo carried,
`patches/common/kgsl-zero-timeout-poll.patch`, was dropped on 2026-10-10; `apply_common.sh` now asserts
Mesa has the fix. The rest of this document is the original report.
**Branch:** `fix/kgsl-zero-timeout-poll`. **Found:** 2026-09-29 on an AYANEO Pocket FIT (Snapdragon 8
Gen 3, Adreno 750) while chasing why D3D12 was slower on Bannerlator's Wayland backend than on X11.
**Upstream status:** fixed by MR 44838 (2026-10-08); the report below predates it.

## Summary

Turnip's KGSL backend turns a *poll* ("has the GPU reached timestamp T yet? don't wait") into
`IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID` with `timeout = 0`. The KGSL kernel driver treats a timeout
of 0 as **wait forever**. Mesa's emulated timeline semaphores poll from `vk_sync_timeline_gc_locked()`
on every `vkQueueSubmit2` that signals a timeline, **while holding the timeline mutex**. vkd3d-proton
signals a timeline on every submit and runs a fence thread that takes the same mutex, so the CPU sat
blocked until the GPU finished the previous work on every submit: CPU and GPU ran in lock-step
instead of overlapping. The fix answers polls with
`IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID` (`KGSL_TIMESTAMP_RETIRED`) and never waits.

## The code path

`src/freedreno/vulkan/tu_knl_kgsl.cc` (Mesa main):

```c
static int
get_relative_ms(uint64_t abs_timeout_ns)
{
   ...
   if (abs_timeout_ms <= cur_time_ms)
      return 0;                       /* a poll, or a deadline already past */
   ...
}

static VkResult
wait_timestamp_safe(int fd, unsigned int context_id, unsigned int timestamp,
                    uint64_t abs_timeout_ns)
{
   struct kgsl_device_waittimestamp_ctxtid wait = {
      .context_id = context_id,
      .timestamp = timestamp,
      .timeout = get_relative_ms(abs_timeout_ns),   /* 0 for a poll ... */
   };
   ...
   int ret = ioctl(fd, IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID, &wait);
   /* ... and KGSL (adreno_waittimestamp -> adreno_drawctxt_wait) treats 0 as "no timeout" */
```

Callers that mean "poll": `kgsl_syncobj_wait()` / `kgsl_syncobj_wait_any()` with
`abs_timeout_ns == 0` or an expired deadline — reached from `vk_sync_wait()` with a zero timeout,
which the common timeline emulation (`vk_sync_timeline_gc_locked`, called from
`vk_sync_timeline_alloc_point`) does for every pending point on every signalling submit.

## Evidence

Measured with `simpleperf` on the device (sched-switch, frame-pointer call chains, time-weighted):

- Wayland, D3D12 demo, `vkd3d_queue` thread: 91 % of its time inside the driver's
  `vkQueueSubmit2` — 63 % waiting on the timeline mutex, 25 % asleep in
  `kgsl_ioctl_device_waittimestamp_ctxtid → adreno_waittimestamp → adreno_drawctxt_wait`
  (driver offset `+9ea920`, the `wait_timestamp_safe` ioctl; reached from
  `vk_sync_timeline_alloc_point` `+a2bf08` → `vk_sync_timeline_gc_locked` `+a2c93c`).
- X11 showed the same pattern, milder (74 % / 41 % / 31 %).
- DXVK (D3D11) does not signal a timeline per submit the same way and was not throttled.
- Symptom: a standalone D3D12 scene ran at a flat ~1.62 ms/frame (~615 fps) on Wayland regardless
  of load (a hello-triangle ran at the same ~600), with the GPU idle ~25 %.

Changing latency knobs (`VKD3D_SWAPCHAIN_LATENCY_FRAMES`, present wait off, more swapchain images,
DXGI max frame latency, zero-copy vs copy) did not move it — they are all above the driver.

## The fix

```c
/* Whether the context has retired timestamp, without waiting. */
static bool
kgsl_timestamp_retired(int fd, unsigned int context_id, unsigned int timestamp)
{
   struct kgsl_cmdstream_readtimestamp_ctxtid req = {
      .context_id = context_id,
      .type = KGSL_TIMESTAMP_RETIRED,
   };
   if (safe_ioctl(fd, IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID, &req))
      return false;
   return timestamp_cmp(req.timestamp, timestamp);   /* wrap-safe >= */
}

wait_timestamp_safe(...)
{
   /* KGSL treats a zero timeout as "wait forever", so a poll must not reach the wait ioctl. */
   if (get_relative_ms(abs_timeout_ns) == 0)
      return kgsl_timestamp_retired(fd, context_id, timestamp) ? VK_SUCCESS : VK_TIMEOUT;
   ...   /* real waits (a positive timeout or forever) are unchanged */
}
```

A read failure reports "not retired" (`VK_TIMEOUT`), which is always safe for a poll.

The same answer was first proven from *outside* the driver, in Bannerlator's Wayland adapter
(The412Banner/bionic-vulkan-wrapper `banner/wayland-wsi` `3af78e4`, `banner/kgsl/banner_kgsl_poll.h`:
redirect the loaded Turnip's `ioctl` import and answer zero-timeout waits from the retired
timestamp; `BANNER_KGSL_POLL_FIX=0` turns it off). With it off the cap came straight back
(466–596 fps), with it on 4335 fps. This patch moves the fix into the driver so X11, Wayland, the
Linux (DroidDeck) legs and other apps get it.

## Device results (Pocket FIT, Adreno 750, Bannerlator 3.1.3, Proton 11.0-2.1-arm64ec-16,
VKD3D-Proton 3.0.1, DXVK 2.4.1 gplasync, 1280x720, uncapped)

Fixed driver = this branch's Android regular leg (dry-run 36566685611, Mesa `97b154f`), installed as
"Turnip KGSL-poll FIX TEST 97b154f". Baseline = release `v26.3.0-20260929-r2` (Mesa `fe55488`).
Wayland used Bannerlator's built-in adapter **without** the adapter-side workaround (333fa5d), so
the gain is the driver fix alone. Each pair was run back to back in one session.

| Standalone test (fps from the demo's own counter) | r2 | fixed | gain |
|---|---|---|---|
| D3D12 demo (`dx12_demo/D3D12_x64.exe`), X11 | 378 | **1422** | ×3.8 |
| D3D12 demo, Wayland | 588 | **3449** | ×5.9 |
| D3D12HelloTriangle, X11 | 264 | **451** | ×1.7 |
| D3D12HelloTriangle, Wayland | 566 | **880** | ×1.6 |

AIO Graphics Test (fullscreen build `--sweep 15`, one window presenting every API through its D3D11
shell), fps averages from the AIO's own report:

| AIO row | X11 r2 | X11 fixed | Wayland r2 (mean of 2) | Wayland fixed (mean of 2) |
|---|---|---|---|---|
| Vulkan | – | – | 491 | 492 |
| Direct3D 12 | 270 | **342** | 372.5 | 381 |
| Direct3D 11 | 848 | **1386** | 2887 | 2915 |
| Direct3D 10 | 231 | **287** | 327.5 | 333 |

- X11 is a single back-to-back pair. Wayland is an A-B-A-B run (r2, fixed, r2, fixed) to cancel
  run order and heat: runs were 359/383/386/379 (D3D12) and 2482/3083/3293/2748 (D3D11), so the
  Wayland AIO difference is inside run-to-run noise. **No regression on any row.**
- Why the AIO gains less than the standalone demos: the AIO's D3D12 row renders offscreen and is
  copied into a D3D11 swapchain every frame. That copy/present path, not the timeline poll, is its
  limit. The remaining AIO D3D12/D3D10 gap between Wayland and X11 is a separate, still-open issue.
- Conditions: device at 76–80 °C and not charging. A single unpaired Wayland run with the fix read
  low (D3D11 1344) purely from heat and order, which is why the A-B-A-B was done.

## Build verification

- Dry-run of `turnip_build_combined.yml` on the branch (run 36566685611, headSha `7e81e6f`):
  all 9 legs green (Android / Wayland / Linux × regular / A8xx / 710-720-Test); the
  `apply_common.sh` assert (`kgsl_timestamp_retired(fd, context_id, timestamp) ? VK_SUCCESS :
  VK_TIMEOUT` present in `tu_knl_kgsl.cc`) passed on every leg.

## Upstreaming

Worth sending to Mesa: the bug is in upstream Turnip's KGSL backend, not in our patches. The same
treatment may be wanted for the `sync_wait(s->fd, 0)` / `poll(fds, …, 0)` paths (those use real
fds where 0 means "don't wait", so they are fine as they are).

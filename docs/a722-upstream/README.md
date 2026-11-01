# Adreno 722: toward a pure upstream Turnip (lab notes, 2026-11-01)

Branch `feat/a722-upstream` only. Nothing here is released, merged or sent to Mesa.
Device: Retroid Pocket Duo (Adreno 722, chip id 0x43020100, Qualcomm driver V@0800.73,
Android 14). Mesa: main 1d4b5ef4a5562b6e2dba2cb5aacd60787979ba86.

## Which patches the 722 really needs

| Patch | Source | Needed? |
|---|---|---|
| A722 register block (`patches/a710-720.py`) | Vauzi-17/710 | **No** for correctness: pure upstream's A722 entry passed the same 7,638 Vulkan CTS tests (0 failures, 0 GPU faults) as our own entry. Our own entry (below) matches the Qualcomm driver and is the upstream candidate. |
| u_gralloc "always use the UBWC detection path" | whitebelyash | **Replaced** by `0002`: it reads the wrong field on the newer handle (always "not compressed"). That is right for Bannerlator's linear buffers but wrong for real UBWC buffers. |
| `0002-u_gralloc-newer-qcom-handle.diff` | own | **Yes** for Bannerlator's Wayland path. Without it, pure upstream draws a scrambled picture. |
| `0001-a722-own-entry.diff` | own | Optional: matches the Qualcomm driver's start-up registers. No CTS difference found. Speed comparison: see the overnight bench. |

## 0001: Adreno 722 entry

Upstream (MR 43101) gives the 722 the A730 register list and `num_ccu = 1`. The Qualcomm driver on
the 722 writes upstream's A720 list (MR 44466) with 5 different values, sets neither
`TPL1_DBG_ECO_CNTL1.TP_UBWC_FLAG_HINT` nor `SP_CHICKEN_BITS.EOLM_ENABLE`, and lays out GMEM for
2 CCUs (color CCU offset 0xFC000 = 1 MB - 2 x 64 KB / 8). Evidence: freedreno `.rd` recordings
of the Qualcomm driver on the device (36 Vulkan CTS + 54 GLES captures, every Vulkan capture
agrees), compared register by register with DriverLab.

| Register | Upstream A720 list | Qualcomm on A722 |
|---|---|---|
| UCHE_CACHE_WAYS | 0x00040004 | 0 |
| SP_CHICKEN_BITS | 0x00001400 | 0x00000400 |
| SP_CHICKEN_BITS_2 | 0 | 0x00000010 |
| SP_UNKNOWN_AB01 | 1 | 0 (1 in GLES only) |
| RB_CCU_DBG_ECO_CNTL | 0 | 0x00080000 |

## 0002: newer Qualcomm gralloc handles

On this device the gralloc private handle has numFds 2, numInts 38 and no `'gmsm'` magic.
Dumped with `AHardwareBuffer_getNativeHandle` (tool: DriverLab lab `ahbdump.c`):

| int | linear RGBA8 1172x686 | with GRALLOC_USAGE_PRIVATE_ALLOC_UBWC |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 1 | 1 |
| 2 (flags) | 0x00000200 | 0x0a000000 (UBWC_ALIGNED, TILE_RENDERED) |
| 3 | 0x1300 (stride, bytes) | 0x1300 |
| 4 | 0x4c0 (aligned width) | 0x4c0 |
| 5 | 0x2ae (aligned height) | 0x2b0 |
| 6, 7 | 1172, 686 | 1172, 686 |
| 8 | 1 (HAL format) | 1 |

The patch keeps the old `'gmsm'` path and adds a second, strict one: when int 8 equals the
buffer's HAL format and int 4 equals its pixel stride, read the UBWC flag from int 2.
Unrecognised handles stay as upstream treats them.

Checked: Bannerlator Wayland AIO picture correct (0 bad frames of 893) with pure upstream + this
patch; scrambled without it. Not checked: a real UBWC gralloc buffer through Turnip (the CTS
AHB tests abort in the standalone CTS build on Android 13+).

## Speed (AIO Graphics Test cube, Bannerlator d4fd644d Wayland, sysmem)

Standalone `--cube <api> --bench 15`, one launch per API, two passes (second in reverse
driver order), average fps. All 80 runs: 0 GPU page faults, 0 crashes.

| Driver | Vk | GL | D3D12 | D3D11 | D3D10 | D3D9 | D3D8 | D3D7 |
|---|---|---|---|---|---|---|---|---|
| upstream + 0002 | 1575 | 1227 | 1803 | 1937 | 1923 | 2185 | 2210 | 1192 |
| 0001 + 0002 | 1533 | 1226 | 1787 | 1930 | 1929 | 2217 | 2229 | 1232 |
| Vauzi block + whitebelyash | 1555 | 1238 | 1810 | 1932 | 1935 | 2224 | 2214 | 1238 |
| 710-720-Test (10-31 build) | 1579 | 1236 | 1520 | 1725 | 1671 | 1917 | 1905 | 1235 |

- The three builds on this Mesa are equal within run-to-run noise (about 5 %): the patches change
  correctness, not speed.
- The 10-31 build's lower D3D numbers are a Bannerlator setting, not Mesa: that driver has a
  cached Wayland probe, so the Auto profile turns on zero-copy (`BANNER_WAYLAND_ZERO_COPY=1`,
  seen in the game's environment). Same driver with zero-copy off: D3D11 1912; pure upstream with
  zero-copy on: D3D11 1671. Zero-copy costs about 13 % in D3D on this path; Vulkan is unchanged.
- `TU_DEBUG` switches on pure upstream (Vk / D3D11): `hiprio` 1474 / 1913, `nolrz` 1529 / 1887
  (both noise), `noubwc` 1444 / 1036 (UBWC must stay on).
- GPU busy is about 50 % and no CPU thread is saturated (game thread about 60 %), so at these
  frame rates the cube test is limited by the hand-offs between the game, wineserver, the
  compositor and SurfaceFlinger, not by Turnip. It does not measure Turnip's GPU efficiency.
- "System" is not a valid comparison on this device: with System picked, Bannerlator's Wayland
  compositor falls back to its bundled `turnip-sdk36`, which does not support the A722
  (`tu_device.cc:1570 ... unsupported`, `BannerWayland: renderer unavailable`). The screen stays
  black and the game's frames are never composited, so its fps (2400-3000) is not real.

## GMEM on A722 (bug report draft)

With `TU_DEBUG=gmem`, every Turnip variant tried (pure upstream, our entry, Vauzi's block,
CCU carve-out experiments) shows:

- kernel `GPU PAGE FAULT ... write translation fault, FAULTING BLOCK: CCU` at addresses
  0x0-0x1140 (64-byte steps) during the AIO Graphics Test GUI (DXVK D3D11, 4 bins of 640x352),
  continuously while it renders;
- single-frame green blocks in that GUI when UBWC is on (gone with `TU_DEBUG=noubwc`, faults stay);
- in CTS, `dEQP-VK.pipeline.monolithic.render_to_image.core.{2d,cube}.*` run as one batch:
  CCU faults in about 2 of 5 runs and an occasional failure, mostly
  `*.huge.width_height.r8g8b8a8_unorm_s8_uint`; each test alone passes with no fault;
  sysmem never faults.

Not caused by the A722 registers, `num_ccu`, the depth CCU fraction or keeping bins below the CCU
carve-outs. The Qualcomm driver's GMEM `RB_CCU_CACHE_CNTL` is 0x7e600000 (no depth carve-out);
Turnip writes 0x7e6ecc00. GMEM gave no speed gain in the AIO cube tests (Vulkan 1461 vs
sysmem 1526 fps), so sysmem is the safe default on A722 for now.

# WinNative-Emu/Drivers, release v1.15 (WN-Turnip 1.15)

- Repository: https://github.com/WinNative-Emu/Drivers
- Release: `v1.15`, published 2026-09-10T21:08:24Z, assets `WN-Turnip-1.15-b_Axxx.zip` (Balanced)
  and `WN-Turnip-1.15-p_Axxx.zip` (Performance)
- Tag commit: `8407c8012d7b3096621becec73d836f4fbe7b3ce`
- Mesa the release was built from: `12b7b819edb4ddd3580e7e5ffe384610ae726c90` (26.3.0-devel), stated in
  the release notes ("Mesa `12b7b819e` (26.3.0-devel)", `<!-- wn-mesa-commit: ... -->`).

Files here are verbatim copies from that commit (`raw.githubusercontent.com/.../8407c801.../<path>`):
`build_wn_turnip.sh`, `build_turnip.sh`, `verify_patches.sh`, and `patches/` (every `.py` plus
`aimapper/u_gralloc_aimapper.c`, which `add_aimapper_gralloc.py` copies into Mesa).

The recipe, as `build_wn_turnip.sh` runs it (EXTRA_SCRIPT, in order):
`fix_gralloc_flushall.py`, `fix_a8xx_dev_info.py`, `apply_a8xx_gpus.py`, `apply_a7xx_gen1_quirks.py`,
`apply_a7xx_gen2_ubwc_hint.py`, `add_aimapper_gralloc.py`, `add_ubwc_swapchain_usage.py`; then
`apply_balance_variant.py` for `-b` (Balanced) or `apply_perf_variant.py` with `BUILD_VARIANT=p`
for `-p` (Performance). `disable_64b_image_atomics.py` is in their tree but not in EXTRA_SCRIPT and
is not used. Their Android-side build also strips `-Werror=gnu-empty-initializer` from meson.build
and applies NDK r29 `sed` fixes to Android-only files; neither is part of the driver and the
Wayland build (`build_wayland.sh`) does not do them.

How the Wayland build uses it: both a8xx drivers come from one Mesa checkout at the commit above,
with the Wayland changes applied first; `fix_a8xx_dev_info.py`, `apply_a8xx_gpus.py`,
`apply_a7xx_gen1_quirks.py` and `apply_a7xx_gen2_ubwc_hint.py` must report no missing anchor and
must change the tree; the three Android-side scripts (gralloc, aimapper, UBWC swapchain usage) run
too and are allowed to warn, since the files they target are not compiled in a Wayland build.

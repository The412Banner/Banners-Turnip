# Combined Android + Wayland Turnip - Progress Log

## 2026-09-28 - TEST: ONE Turnip .so for X11 + Wayland compositor + Wayland game (branch `test/combined-android-wayland-so`) - PROVEN

**Branch** `test/combined-android-wayland-so` off A8xx `34541b0`, tip `49bab134`. Files: `build_turnip_combined_so.sh`,
`.github/workflows/turnip_combined_so_test.yml` (push-triggered on the branch + dispatch; regular + A8xx; artifacts only,
nothing published). Mesa `9f1e484` (= r4's commit).

**Why the 2026-09-12 combined build (run 34713704642) failed:** Mesa's Android version script `src/vulkan/vulkan-android.sym`
exports ONLY `HMI`, so the Khronos loader inside the Wine container found no `vk_icd*` entry point and skipped the driver
(`VK_ERROR_INCOMPATIBLE_DRIVER`). The functions are compiled on every platform; only the export list hid them. Found by this
build's own export check (run 36446225790).

**What the combined build changes vs the Android release recipe:**
- `vulkan-android.sym` (+ `vulkan-icd-android-symbols.txt`): add `vk_icdGetInstanceProcAddr`, `vk_icdGetPhysicalDeviceProcAddr`,
  `vk_icdNegotiateLoaderICDInterfaceVersion` to the exports.
- `-Dplatforms=android,wayland -Dandroid-strict=false` (strict hides VK_KHR_wayland_surface) `-Dfreedreno-kmds=kgsl,msm`
  (kgsl alone drops libdrm and wsi_common_drm.c).
- Wayland-leg patches: `banner_ahb_wsi.py`, the KGSL wait assert, `patches/common`.
- Old-libwayland compatibility: `-DHAVE_WL_DISPATCH_QUEUE_TIMEOUT` / `-DHAVE_WL_CREATE_QUEUE_WITH_NAME` left off (Mesa's
  loader_wayland_helper fallbacks), `MESA_WL_FIXES_VERSION` block removed. BannerHub/GameHub puts its own older
  libwayland-client first on the library path; it lacks `wl_display_dispatch_queue_timeout` + `wl_fixes_interface`, so the
  dlopen failed and gamescope aborted ("Failed to load Vulkan driver").
- `patchelf --set-rpath '$ORIGIN'`; zip is flat: libvulkan_freedreno.so + libwayland-client + libdrm + libffi +
  libandroid-support + meta.json (`libraryName`, no `kind`) -> both Bannerlator importers accept the same zip.
- Build checks (fail the build): RUNPATH $ORIGIN, HMI + 3 vk_icd* exported, >10 wl_ imports, VK_KHR_wayland_surface +
  banner_ahb_v1 strings, none of the 3 newer-libwayland symbols imported.

**Runs:** 36446225790 (red: export check) -> 36446823692 (green) -> 36447490660 (green, + libandroid-support) ->
36453440568 (green, old-libwayland compat, headSha 49bab134). Final zips: `Turnip-Combined-TEST-9f1e484.zip`
sha256 `c56238cc...` and `Turnip-Combined-TEST-A8xx-9f1e484.zip` sha256 `ccb89790...` (staged `/sdcard/Download/Wayland/`).

**Device results (AYANEO Pocket FIT, Adreno 750, Bannerlator 3.1.3):**
- X11: DiRT Showdown runs through libvulkan_wrapper -> AdrenoTools -> combined .so (its bundled libs loaded from the driver dir).
- Wayland compositor driver = combined: OK. Wayland game driver = combined: DiRT Showdown zero-copy UBWC, ~143 fps (vsync).
- BannerHub v6 (GameHub 6.3.1): DOOM (GOG) runs on the combined .so after the old-libwayland fix.
- Fold 8 (A840) with the A8xx zip: works per the user (pre-libwayland-fix build; logs not pulled).
- AIO Vulkan test on Wayland with vsync off closes "Present mode unsupported": AIO asks IMMEDIATE, Mesa's Wayland WSI only
  offers it with wp_tearing_control, which the compositor lacks (AIO bug: cube.c ERR_EXITs instead of falling back).

**Next (not started):** user direction is now a thin in-app Wayland wrapper so ANY community Android driver works with one
pick (see Bannerlator PROGRESS_LOG). The combined .so stays as the no-middleman option; a release leg for it is on hold.

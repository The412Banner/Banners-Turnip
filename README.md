<p align="center">
  <img src="logo.png" alt="Banners-Turnip" width="600"/>
</p>

# Banners-Turnip
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/n8S4G2WZQ4)


> Automated, bleeding-edge builds of the [Mesa Turnip](https://docs.mesa3d.org/drivers/freedreno.html) Vulkan driver — compiled directly from the latest upstream Mesa commits and packaged for [AdrenoTools](https://github.com/K11MCH1/AdrenoToolsDrivers)-compatible apps on Qualcomm Adreno GPUs.

[![Build Turnip (Combined)](https://github.com/The412Banner/Banners-Turnip/actions/workflows/turnip_build_combined.yml/badge.svg?branch=A8xx)](https://github.com/The412Banner/Banners-Turnip/actions/workflows/turnip_build_combined.yml)
[![Latest Release](https://img.shields.io/github/v/release/The412Banner/Banners-Turnip?label=latest%20release&color=blue)](https://github.com/The412Banner/Banners-Turnip/releases/latest)

---

## What Is This?

[Turnip](https://docs.mesa3d.org/drivers/freedreno.html) is the open-source Mesa Vulkan driver for Qualcomm Adreno GPUs — developed as part of the [Mesa](https://gitlab.freedesktop.org/mesa/mesa) project and maintained by the Freedreno community. Unlike the proprietary Qualcomm driver, Turnip is fully open-source and often ships fixes and feature support ahead of official Qualcomm releases.

This repo automatically builds Turnip from the absolute latest commit on `mesa/main` — no waiting for official Mesa releases. A [Mesa upstream watcher](.github/workflows/mesa-watcher.yml) polls for new commits every hour and triggers a fresh build automatically whenever `mesa/main` advances. The result is an [AdrenoTools](https://github.com/K11MCH1/AdrenoToolsDrivers)-compatible ZIP you can drop straight into any compatible app (BannerHub/BCI, Winlator, etc.) to get the most up-to-date driver available.

---

## Driver Variants & Downloads

Each release ships three driver ZIPs — pick the one matching your GPU.

[**Download latest →**](https://github.com/The412Banner/Banners-Turnip/releases/latest) · [**Full build history →**](Mesa-commit-history.md)

### A6xx / A7xx — Standard

Pure Mesa `main`, no source patches. Compatible with Adreno 600–700 series GPUs (Snapdragon 600–800 series, including 7 Gen and 8 Gen 1–3).

### A710 / A720 / A722 — Experimental / Work in Progress

Injects hardware-specific GPU entries and magic registers for Adreno 710, 720, and 722 on top of Mesa `main` via [`a710-720.py`](patches/a710-720.py) — based on community research by [Vauzi-17](https://github.com/Vauzi-17/710). No upstream Mesa support exists for these GPUs yet. Early results are promising. Recommended: force sysmem mode via `TU_DEBUG=sysmem` until GMEM is confirmed stable. Winlator users: set `WRAPPER_BLIT=1`.

### A8xx — Experimental

Targets Adreno 800-series (Snapdragon 8 Elite — A810, A825, A829, A830). Built from Mesa `main` with the following patches on top:

| Patch | What it does |
| :--- | :--- |
| `tu8_kgsl_26.patch` | 9 commits from [whitebelyash/mesa-tu8](https://github.com/whitebelyash/mesa-tu8): UBWC gralloc detection, `disable_gmem` GPU property, A8xx magic regs, A810/A825/A829/A830 GPU configs, gmem cache fixes |
| `fix_a8xx_dev_info.py` | Re-adds `disable_gmem` to `freedreno_dev_info.h` and `tu_cmd_buffer.cc` — safeguard if the patch hunk drifts on a new Mesa commit |
| `apply_a8xx_gpus.py` | Ensures A810/A825/A829 GPU entries are present in `freedreno_devices.py` — safeguard if the patch hunk drifts on a new Mesa commit |

**Use at your own risk.**

---

## Workflows

| Workflow | Trigger | What it builds |
| :--- | :--- | :--- |
| **Build Turnip (Combined)** | Auto (mesa-watcher) or manual | Standard + A8xx + A710/A720/A722 in parallel; published as a single tagged release |
| **Build Turnip A8xx (Experimental)** | Manual | Standalone A8xx test build — faster iteration outside the release cycle |
| **Build Turnip (Perf 6xx/7xx)** | Manual | A6xx/A7xx only, compiled with `-O3` + ThinLTO for performance testing |

---

## Installation

- **BannerHub / BCI:** Component Manager → Add New Component → select the ZIP
- **AdrenoTools-compatible apps (Winlator, etc.):** load the ZIP in GPU driver settings

---

## Latest Build

<!-- LATEST_BUILD_START -->
| | |
| :--- | :--- |
| **Mesa version** | 26.2.0 |
| **Vulkan version** | Vulkan 1.4.354 |
| **Commit** | [`16ba3cf`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/16ba3cf32a8d7fffd5854e3ffdc190098146caef) |
| **Commit date** | 2026-06-30 |
| **Commit title** | d3d12: d3d12_create_fence_raw to lazily register fence event on waits |
| **Build date** | 20260630 |
| **Release** | [v26.2.0-20260630-r10](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r10) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.2.0-20260630-r10](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r10) | 2026-06-30 | [`16ba3cf`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/16ba3cf32a8d7fffd5854e3ffdc190098146caef) | d3d12: d3d12_create_fence_raw to lazily register fence event on waits | Vulkan 1.4.354 |
| [v26.2.0-20260630-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r9) | 2026-06-30 | [`fa8fa25`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/fa8fa25d6077eac3d0206495b5ecb1ddc5066a1c) | glx: fix per-display drawHash / zombieGLXDrawable / dri2Hash leak on GLX_USE_APPLE builds | Vulkan 1.4.354 |
| [v26.2.0-20260630-r8](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r8) | 2026-06-30 | [`c053340`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/c05334058d5417b0986578c94b9aa6ab601f3ba8) | pco: allow non-pure integer formats for image xchg atomics | Vulkan 1.4.354 |
| [v26.2.0-20260630-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r7) | 2026-06-30 | [`57f136e`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/57f136ebc95c48b51e75c0892e27896d43f379a2) | docs/perfetto: panfrost now supports render stages | Vulkan 1.4.354 |
| [v26.2.0-20260630-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r6) | 2026-06-30 | [`7fb22ad`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/7fb22ad1a0c51b76eab7f7d122caa816135af289) | panfrost/ci: turn bifrost / valhall rules into per-kernel driver | Vulkan 1.4.354 |
| [v26.2.0-20260630-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r5) | 2026-06-30 | [`0eeb51a`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/0eeb51a58d9abf5d48212b6b7ffe01d9085bffbd) | anv: Support VK_ANDROID_native_buffer older than version 11 | Vulkan 1.4.354 |
| [v26.2.0-20260630-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r4) | 2026-06-30 | [`7fa1b48`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/7fa1b48755647b9468f5c603810260edea9de996) | radv: disable AMD_device_coherent_memory on gfx12 due to out of order behavior | Vulkan 1.4.354 |
| [v26.2.0-20260630-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r3) | 2026-06-30 | [`f5e4233`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/f5e423312d3a9f8b653d2b41ff48195fdea91020) | lavapipe: lower array-deref-of-vec for mesh shader outputs | Vulkan 1.4.354 |
| [v26.2.0-20260630-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r2) | 2026-06-30 | [`8ad054c`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/8ad054ce867161d01cfdd70c01248e32ecc9e7f4) | radv: remove the deprecated warning for RADV_FORCE_FAMILY | Vulkan 1.4.354 |
| [v26.2.0-20260630](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630) | 2026-06-30 | [`9710884`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/97108842afd4a56885e51e596024514a880928a2) | anv: Compile init RT shader with Jay | Vulkan 1.4.354 |
| [v26.2.0-20260629-r8](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260629-r8) | 2026-06-29 | [`b0050c4`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/b0050c4e754172c1c986f34e4ac0333d3d01479b) | meson: drop misleading `-D egl-native-platform` values | Vulkan 1.4.354 |
| [v26.2.0-20260629-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260629-r7) | 2026-06-29 | [`f39e380`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/f39e380bd1aa5a340f60f05d6ec96caf2811972a) | ci/windows: Update WARP to 1.0.20 | Vulkan 1.4.354 |
| [v26.2.0-20260629-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260629-r6) | 2026-06-29 | [`e9115e4`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e9115e448f7bf1ee36d162be36b009f031e9821d) | freedreno/drm: Fix uninitialized read of BO metadata on import | Vulkan 1.4.354 |
| [v26.2.0-20260629-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260629-r5) | 2026-06-29 | [`a5d96cd`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/a5d96cd6cda0bd1b358468f00530bb6535e6ef14) | r300: move r500 FS derivative fixup to nir_to_rc translation | Vulkan 1.4.354 |
<!-- RECENT_BUILDS_END -->

---

## Release Tags

Tags follow the format `v{mesa-version}-{YYYYMMDD}`:

| Tag | Meaning |
| :--- | :--- |
| `v26.2.0-20260427` | First build of the day |
| `v26.2.0-20260427-r2` | Second build of the same day |
| `v26.2.0-20260427-r3` | Third build of the same day |

The `-r` counter starts fresh each day. Multiple builds on the same day happen when Mesa receives more than one commit within 24 hours — each new upstream commit triggers a new build.

---

## Forking / Self-Hosting

You can fork this repo and get fully automated builds running with minimal setup — no custom secrets or external accounts required. All CI uses the built-in `GITHUB_TOKEN`.

**After forking:**

1. **Enable Actions** — GitHub disables Actions on forks by default. Go to **Settings → Actions → General** and set it to *Allow all actions*.

2. **Enable write permissions for Actions** — Under **Settings → Actions → General → Workflow permissions**, select *Read and write permissions*. This is required for the watcher to commit hash files, update the README, and trigger builds.

3. **Reset state files** — The repo ships with state files that track upstream positions. Reset them so your fork starts clean:
   - `mesa_hash.txt` — clear or delete (watcher records the current Mesa HEAD here; a stale value skips the first build trigger)
   - `steven_last_tag.txt` — clear or delete (same, for the StevenMXZ release watcher)
   - `perf_build_number.txt` — set to `1` (incremented and committed by the perf build workflow; leaving it at the current value just means your first perf build gets a higher number, which is harmless but confusing)

4. **Keep the branch named `A8xx`** — The README auto-update step in `turnip_build_combined.yml` has `A8xx` hardcoded in four places (`git fetch/checkout/pull/push origin A8xx`). If you rename the branch, that step will fail and your README won't auto-update. Either keep the branch as `A8xx` or do a find-and-replace in `.github/workflows/turnip_build_combined.yml` to match your branch name.

5. **Update cosmetic repo references** *(optional)* — A few strings in the workflows reference the original repo: patch links in release note bodies and `"author"` in `meta.json`. Search for `The412Banner` in `.github/workflows/` and update to your own username/repo if desired. These don't affect build functionality.

6. **Kick off your first build** — GitHub Actions schedules don't fire automatically on forks until the repo sees some activity. Manually trigger either:
   - **Mesa Upstream Watcher** → *Run workflow* — records the current Mesa HEAD and fires a combined build if it's new
   - **Build Turnip (Combined)** → *Run workflow* — builds and publishes a release immediately without waiting for the watcher

Once those steps are done, the watcher polls Mesa upstream every hour and triggers a fresh build automatically — no further maintenance needed.

---

## Credits

This project wouldn't exist without the hard work and dedication of these community members. A huge thank you to each of them for sharing their knowledge, publishing their work openly, and being available to help — they're the reason any of this is possible.

| | |
| :--- | :--- |
| [**Mesa / Freedreno**](https://gitlab.freedesktop.org/mesa/mesa) | The open-source project that Turnip is part of — without Mesa and the Freedreno community's ongoing development, none of this exists. |
| [**whitebelyash**](https://github.com/whitebelyash) | Author of the [mesa-tu8](https://github.com/whitebelyash/mesa-tu8) A8xx patchset — the foundation of our A8xx driver variant. His research into A810/A825/A829/A830 GPU enablement, KGSL support, and UBWC fixes made Snapdragon 8 Elite Turnip support possible. |
| [**Vauzi**](https://github.com/Vauzi-17) | Author of the [A710/A720/A722 GPU enablement work](https://github.com/Vauzi-17/710) — hardware-specific magic registers, tuned GPU properties, and chip ID research that our experimental 710/720/722 test build is built on. |
| [**bylaws**](https://github.com/bylaws) | Creator of [libadrenotools](https://github.com/bylaws/libadrenotools) — the driver loading framework that makes all of this usable on Android without root. Without libadrenotools, custom Turnip builds would have no delivery mechanism. |
| [**Kimchi**](https://github.com/K11MCH1) | Maintainer of [AdrenoToolsDrivers](https://github.com/K11MCH1/AdrenoToolsDrivers) — one of the most well-established and trusted custom driver repositories in the Android GPU community, built on top of libadrenotools. |
| [**StevenMXZ**](https://github.com/StevenMXZ) | For his ongoing Turnip builds and releases that the community relies on, and for making his work openly available for others to build upon. |

Also thanks to anyone I forgot and not listed — the Android GPU community is full of people whose contributions quietly make things work, and they deserve recognition too.

---

<sub>☕ [Support on Ko-fi](https://ko-fi.com/the412banner)</sub>


## Community

Join our Discord: https://discord.gg/n8S4G2WZQ4

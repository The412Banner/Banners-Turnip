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
| **Commit** | [`4309489`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/43094891c9ba32e862eefc85b042e331d2b0bd59) |
| **Commit date** | 2026-07-01 |
| **Commit title** | docs: add sha sum for 26.1.4 |
| **Build date** | 20260701 |
| **Release** | [v26.2.0-20260701-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260701-r6) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.2.0-20260701-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260701-r6) | 2026-07-01 | [`4309489`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/43094891c9ba32e862eefc85b042e331d2b0bd59) | docs: add sha sum for 26.1.4 | Vulkan 1.4.354 |
| [v26.2.0-20260701-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260701-r5) | 2026-07-01 | [`58b14a6`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/58b14a6f563c7e75f798c7ceacc832dea1de9bcc) | kk: refold combined image/sampler packing after vars_to_ssa | Vulkan 1.4.354 |
| [v26.2.0-20260701-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260701-r4) | 2026-07-01 | [`c2e02de`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/c2e02de11b6cb231a8a5ce6e2b5398f350ab8b4c) | ci/panfrost: add piglit OpenCL testing for G610 | Vulkan 1.4.354 |
| [v26.2.0-20260701-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260701-r3) | 2026-07-01 | [`2726653`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/272665305264d27600dcf7838eb0257324ad9ab4) | nir/opt_copy_prop_vars: kill stale entries when source deref is written | Vulkan 1.4.354 |
| [v26.2.0-20260701-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260701-r2) | 2026-07-01 | [`0c195a0`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/0c195a01b06d693274b51af58d921071643fb5a7) | drm-shim: Fix racy initialization. | Vulkan 1.4.354 |
| [v26.2.0-20260701](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260701) | 2026-07-01 | [`a6bb4bb`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/a6bb4bbd1eaa8b1b8ba9e5df98ed2c9958393e40) | intel/brw: Factor out combinable_ordered_pipe() helper | Vulkan 1.4.354 |
| [v26.2.0-20260630-r16](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r16) | 2026-06-30 | [`d02b251`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/d02b25157c68804c4e6da613faf0f38a3bcca6d3) | vulkan/android: force linear for mutable format | Vulkan 1.4.354 |
| [v26.2.0-20260630-r15](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r15) | 2026-06-30 | [`8cf9a06`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/8cf9a06e154dec3854d3bdc1d050769e3d560423) | st/pbo_compute: account for drivers failing to create cs shaders | Vulkan 1.4.354 |
| [v26.2.0-20260630-r14](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r14) | 2026-06-30 | [`fd16393`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/fd16393e56ac4b3fe213048f45e4f2477cbb43c1) | intel/ci: Remove nightly CML jobs, retire runner | Vulkan 1.4.354 |
| [v26.2.0-20260630-r13](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r13) | 2026-06-30 | [`0983c72`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/0983c72a7ed9907cb494079260f1e15dd695ea42) | anv: fix push pointer optimization with DGC | Vulkan 1.4.354 |
| [v26.2.0-20260630-r12](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r12) | 2026-06-30 | [`a472df7`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/a472df72eb67591454756c522c2eacbc69b65088) | intel/executor: inform oa not available if that's the case | Vulkan 1.4.354 |
| [v26.2.0-20260630-r11](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r11) | 2026-06-30 | [`45b8dfc`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/45b8dfc0b8d350cc797c085a0e0ed26a40d87be2) | freedreno: Add some gen8 control registers | Vulkan 1.4.354 |
| [v26.2.0-20260630-r10](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r10) | 2026-06-30 | [`16ba3cf`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/16ba3cf32a8d7fffd5854e3ffdc190098146caef) | d3d12: d3d12_create_fence_raw to lazily register fence event on waits | Vulkan 1.4.354 |
| [v26.2.0-20260630-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260630-r9) | 2026-06-30 | [`fa8fa25`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/fa8fa25d6077eac3d0206495b5ecb1ddc5066a1c) | glx: fix per-display drawHash / zombieGLXDrawable / dri2Hash leak on GLX_USE_APPLE builds | Vulkan 1.4.354 |
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

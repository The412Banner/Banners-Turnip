<p align="center">
  <img src="logo.png" alt="Banners-Turnip" width="600"/>
</p>

# Banners-Turnip

> Automated, bleeding-edge builds of the [Mesa Turnip](https://docs.mesa3d.org/drivers/freedreno.html) Vulkan driver — compiled directly from the latest upstream Mesa commits and packaged for [AdrenoTools](https://github.com/K11MCH1/AdrenoToolsDrivers)-compatible apps on Qualcomm Adreno GPUs.

[![Build Turnip (Combined)](https://github.com/The412Banner/Banners-Turnip/actions/workflows/turnip_build_combined.yml/badge.svg?branch=A8xx)](https://github.com/The412Banner/Banners-Turnip/actions/workflows/turnip_build_combined.yml)
[![Latest Release](https://img.shields.io/github/v/release/The412Banner/Banners-Turnip?label=latest%20release&color=blue)](https://github.com/The412Banner/Banners-Turnip/releases/latest)

---

## What Is This?

[Turnip](https://docs.mesa3d.org/drivers/freedreno.html) is the open-source Mesa Vulkan driver for Qualcomm Adreno GPUs — developed as part of the [Mesa](https://gitlab.freedesktop.org/mesa/mesa) project and maintained by the Freedreno community. Unlike the proprietary Qualcomm driver, Turnip is fully open-source and often ships fixes and feature support ahead of official Qualcomm releases.

This repo automatically builds Turnip from the absolute latest commit on `mesa/main` — no waiting for official Mesa releases. A [Mesa upstream watcher](.github/workflows/mesa-watcher.yml) polls for new commits every hour and triggers a fresh build automatically whenever `mesa/main` advances. The result is an [AdrenoTools](https://github.com/K11MCH1/AdrenoToolsDrivers)-compatible ZIP you can drop straight into any compatible app (BannerHub/BCI, Winlator, etc.) to get the most up-to-date driver available.

---

## Driver Variants & Downloads

Each release ships two driver ZIPs — pick the one matching your GPU.

[**Download latest →**](https://github.com/The412Banner/Banners-Turnip/releases/latest)

### A6xx / A7xx — Standard

Pure Mesa `main`, no source patches. Compatible with Adreno 600–700 series GPUs (Snapdragon 600–800 series, including 7 Gen and 8 Gen 1–3).

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
| **Build Turnip (Combined)** | Auto (mesa-watcher) or manual | Standard + A8xx in parallel; published as a single tagged release |
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
| **Vulkan version** | Vulkan 1.4.348 |
| **Commit** | [`a78634c`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/a78634ccb07354b26406f7803e98d32412a872b5) |
| **Commit date** | 2026-04-28 |
| **Commit title** | jay/to_binary: rename grf -> phys_reg |
| **Build date** | 20260428 |
| **Release** | [v26.2.0-20260428-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260428-r9) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.2.0-20260428-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260428-r9) | 2026-04-28 | [`a78634c`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/a78634ccb07354b26406f7803e98d32412a872b5) | jay/to_binary: rename grf -> phys_reg | Vulkan 1.4.348 |
| [v26.2.0-20260428-r8](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260428-r8) | 2026-04-28 | [`6b8d934`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/6b8d9344075630d3dc6893fd6a9379aa8ba833d2) | CODEOWNERS: update owners for Android components | Vulkan 1.4.348 |
| [v26.2.0-20260428-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260428-r7) | 2026-04-28 | [`11399b1`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/11399b15e0ef64bb5563eae9ac3ec8d15986e9d5) | pan/bi: Improve swizzle propagation | Vulkan 1.4.348 |
| [v26.2.0-20260428-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260428-r6) | 2026-04-28 | [`76a3951`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/76a3951e03281acc8f5cd1093726d85f581b97ff) | kk: Fix issues with maximal reconvergence | Vulkan 1.4.348 |
| [v26.2.0-20260428-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260428-r5) | 2026-04-28 | [`669d391`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/669d3915c69a20f4d9d9e86f28236ff69466e800) | radv: slightly rework initializing the default graphics state | Vulkan 1.4.348 |
| [v26.2.0-20260428-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260428-r4) | 2026-04-28 | [`b205c7d`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/b205c7d592d08e485b0b2deb6e1cb94141ca97db) | pvr: Enable shaderImageGatherExtended | Vulkan 1.4.348 |
| [v26.2.0-20260428-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260428-r3) | 2026-04-28 | [`35f57a2`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/35f57a27396c116fc5e9984ac1254d26b83ad2c4) | pvr: increase value of maxPerStageDescriptorStorageBuffers | Vulkan 1.4.348 |
| [v26.2.0-20260428-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260428-r2) | 2026-04-28 | [`7d59c62`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/7d59c62fded7638dbe8b7e0737a8ba491bf6438c) | panvk: Wire up VK_EXT_conservative_rasterization on v11+ | Vulkan 1.4.348 |
| [v26.2.0-20260428](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260428) | 2026-04-28 | [`4b66258`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/4b662587170196783ae0abd10fb34161d30db394) | nak: call nir_opt_algebraic_distribute_src_mods | Vulkan 1.4.348 |
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

<sub>☕ [Support on Ko-fi](https://ko-fi.com/the412banner)</sub>

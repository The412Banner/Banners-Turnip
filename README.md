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

This repo automatically builds Turnip from the absolute latest commit on `mesa/main` — no waiting for official Mesa releases. Every time a new commit lands upstream, a fresh build is compiled and published as a release within minutes. The result is an [AdrenoTools](https://github.com/K11MCH1/AdrenoToolsDrivers)-compatible ZIP you can drop straight into any compatible app (BannerHub/BCI, Winlator, etc.) to get the most up-to-date driver available.

A [Mesa upstream watcher](.github/workflows/mesa-watcher.yml) polls for new Mesa commits every hour and triggers a fresh build automatically whenever `mesa/main` advances — so the latest build listed here is always as close to bleeding-edge as possible.

---

## Driver Variants & Downloads

Each release ships two driver ZIPs — pick the one matching your GPU:

### A6xx / A7xx — Standard

Pure Mesa `main`, no source patches. Compatible with Adreno 600–700 series GPUs (Snapdragon 600–800 series, including 7 Gen and 8 Gen 1–3).

[**Download latest →**](https://github.com/The412Banner/Banners-Turnip/releases/latest)

### A8xx — Experimental

Targets Adreno 800-series (Snapdragon 8 Elite — A810, A825, A829, A830). Built from Mesa `main` with the following patches on top:

| Patch | What it does |
| :--- | :--- |
| `tu8_kgsl_26.patch` | 9 commits from [whitebelyash/mesa-tu8](https://github.com/whitebelyash/mesa-tu8): UBWC gralloc detection, `disable_gmem` GPU property, A8xx magic regs, A810/A825/A829/A830 GPU configs, gmem cache fixes |
| `fix_a8xx_dev_info.py` | Idempotent: re-adds `disable_gmem` to `freedreno_dev_info.h` and `tu_cmd_buffer.cc` if the patch hunk drifts |
| `apply_a8xx_gpus.py` | Idempotent: ensures A810/A825/A829 GPU entries are present in `freedreno_devices.py` if the patch hunk drifts |

**Use at your own risk.**

[**Download latest →**](https://github.com/The412Banner/Banners-Turnip/releases/latest)

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
- **Winlator / adrenotools:** load the ZIP in GPU driver settings
- **Other adrenotools apps:** load the ZIP in driver settings

---

## Latest Build

<!-- LATEST_BUILD_START -->
| | |
| :--- | :--- |
| **Mesa version** | 26.2.0 |
| **Vulkan version** | Vulkan 1.4.348 |
| **Commit** | [`642bed9`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/642bed9eba724132c5e0802fac99af11b9ef7841) |
| **Commit date** | 2026-04-25 |
| **Commit title** | kk: Fix VK_CULL_MODE_FRONT_AND_BACK with points and lines. |
| **Build date** | 20260426 |
| **Release** | [v26.2.0-20260426-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260426-r4) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.2.0-20260426-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260426-r4) | 2026-04-26 | [`642bed9`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/642bed9eba724132c5e0802fac99af11b9ef7841) | kk: Fix VK_CULL_MODE_FRONT_AND_BACK with points and lines. | Vulkan 1.4.348 |
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

<sub>☕ [Support on Ko-fi](https://ko-fi.com/the412banner)</sub>

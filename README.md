# Banners-Turnip

> Automated builds of the Mesa Turnip Vulkan driver as an [AdrenoTools](https://github.com/K11MCH1/AdrenoToolsDrivers) package for Adreno GPUs.

[![Build Turnip (Combined)](https://github.com/The412Banner/Banners-Turnip/actions/workflows/turnip_build_combined.yml/badge.svg?branch=A8xx)](https://github.com/The412Banner/Banners-Turnip/actions/workflows/turnip_build_combined.yml)
[![Latest Release](https://img.shields.io/github/v/release/The412Banner/Banners-Turnip?label=latest%20release&color=blue)](https://github.com/The412Banner/Banners-Turnip/releases/latest)

Each release ships two driver ZIPs — pick the one for your GPU:

| GPU Series | Download | Notes |
| :--- | :--- | :--- |
| **A6xx / A7xx** | [Latest release →](https://github.com/The412Banner/Banners-Turnip/releases/latest) | Snapdragon 600–800 series · 7/8 Gen 1–3 |
| **A8xx** | [Latest release →](https://github.com/The412Banner/Banners-Turnip/releases/latest) | Experimental · Snapdragon 8 Elite (A810 / A825 / A829 / A830) |

---

## Latest Build

<!-- LATEST_BUILD_START -->
| | |
| :--- | :--- |
| **Mesa version** | 26.2.0 |
| **Commit** | [`642bed9`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/642bed9eba724132c5e0802fac99af11b9ef7841) |
| **Commit date** | 2026-04-25 |
| **Commit title** | kk: Fix VK_CULL_MODE_FRONT_AND_BACK with points and lines. |
| **Build date** | 20260426 |
| **Release** | [v26.2.0-20260426](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260426) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description |
| :--- | :--- | :--- | :--- |
| [v26.2.0-20260426](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260426) | 2026-04-26 | [`642bed9`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/642bed9eba724132c5e0802fac99af11b9ef7841) | kk: Fix VK_CULL_MODE_FRONT_AND_BACK with points and lines. | |
| [v26.2.0-20260426-r376](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260426-r376) | 2026-04-26 | [`642bed9`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/642bed9eba724132c5e0802fac99af11b9ef7841) | kk: Fix VK_CULL_MODE_FRONT_AND_BACK with points and lines. | |
| [v26.2.0-20260425](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260425) | 2026-04-25 | [`5bfbb7b`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/5bfbb7b1a792e3cc79afb3a5d8464c2623e9aced) | ir3/ra: fix killed src detection while spilling | |
<!-- RECENT_BUILDS_END -->

---

## What Is This?

[Turnip](https://docs.mesa3d.org/drivers/freedreno.html) is the open-source Mesa Vulkan driver for Qualcomm Adreno GPUs. This repo provides automated, pre-packaged builds ready to load in any [AdrenoTools](https://github.com/K11MCH1/AdrenoToolsDrivers)-compatible app (BannerHub/BCI, Winlator, etc.).

A [Mesa upstream watcher](.github/workflows/mesa-watcher.yml) polls for new Mesa commits every hour and triggers a fresh build automatically whenever `mesa/main` advances.

---

## Driver Variants

### A6xx / A7xx — Standard

Pure Mesa `main`, no source patches. Compatible with Adreno 600–700 series GPUs (Snapdragon 600–800 series, including 7 Gen and 8 Gen 1–3).

### A8xx — Experimental

Includes the [whitebelyash/mesa-tu8](https://github.com/whitebelyash/mesa-tu8) patchset on top of Mesa `main`, targeting Adreno 800-series (Snapdragon 8 Elite — A810, A825, A829, A830). **Use at your own risk.**

---

## Installation

- **BannerHub / BCI:** Component Manager → Add New Component → select the ZIP
- **Winlator / adrenotools:** load the ZIP in GPU driver settings

---

## Building Locally

If you prefer to build yourself, grab the upstream script:

- Download [`turnip_builder.sh`](https://raw.githubusercontent.com/Weab-chan/freedreno_turnip-CI/main/turnip_builder.sh) on a Linux environment
- Run: `bash ./turnip_builder.sh`

---

## References

- [XDA — Freedreno/Turnip on Poco F3](https://forum.xda-developers.com/t/getting-freedreno-turnip-mesa-vulkan-driver-on-a-poco-f3.4323871/)
- [ilhan-athn7/freedreno_turnip-CI](https://github.com/ilhan-athn7/freedreno_turnip-CI)
- [Mesa issue #6802](https://gitlab.freedesktop.org/mesa/mesa/-/issues/6802)

---

<sub>☕ [Support on Ko-fi](https://ko-fi.com/the412banner)</sub>
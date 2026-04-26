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

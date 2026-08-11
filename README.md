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
| **Mesa version** | 26.3.0 |
| **Vulkan version** | Vulkan 1.4.358 |
| **Commit** | [`64dbbfe`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/64dbbfe03429ee4e3b80e3d88ef8000084d15ff8) |
| **Commit date** | 2026-08-11 |
| **Commit title** | radv: run nir_opt_dead_cf before nir_vk_lower_ycbcr_tex |
| **Build date** | 20260811 |
| **Release** | [v26.3.0-20260811-r10](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r10) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.3.0-20260811-r10](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r10) | 2026-08-11 | [`64dbbfe`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/64dbbfe03429ee4e3b80e3d88ef8000084d15ff8) | radv: run nir_opt_dead_cf before nir_vk_lower_ycbcr_tex | Vulkan 1.4.358 |
| [v26.3.0-20260811-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r9) | 2026-08-11 | [`94073fb`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/94073fb459293cebe10c4e74ee28e7d2879cc917) | pan/genxml/v14: Clean up format list | Vulkan 1.4.358 |
| [v26.3.0-20260811-r8](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r8) | 2026-08-11 | [`e1ef8f0`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e1ef8f046c6e37ec1e2a13229560fbb824e5118f) | pvr: advertise KHR_shader_fma | Vulkan 1.4.358 |
| [v26.3.0-20260811-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r7) | 2026-08-11 | [`4e66d3c`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/4e66d3ca29458c0c749c199255e348b09e81c514) | broadcom/compiler: handle 16-bit fsat | Vulkan 1.4.358 |
| [v26.3.0-20260811-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r6) | 2026-08-11 | [`811ebbd`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/811ebbd43c24ead247c19a792eae55b4a3162d21) | pco, pvr: add support for VK_EXT_inline_uniform_block | Vulkan 1.4.358 |
| [v26.3.0-20260811-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r5) | 2026-08-11 | [`28285e6`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/28285e672f37407afce95adafcb9218bc7c2faeb) | docs/features: v3d and panfrost supports GL_EXT_color_buffer_half_float and GL_EXT_texture_norm16 | Vulkan 1.4.358 |
| [v26.3.0-20260811-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r4) | 2026-08-11 | [`0df67d4`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/0df67d43c8159854ef5e1b45155542a977666b72) | radv: add a workaround for broken multi viewport with UE5 | Vulkan 1.4.358 |
| [v26.3.0-20260811-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r3) | 2026-08-11 | [`e060f20`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e060f20717a311059ba2ccc34cd52516c1c8865d) | kk: Disable workaround 8 and 11 on macOS 27 | Vulkan 1.4.358 |
| [v26.3.0-20260811-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r2) | 2026-08-11 | [`194c22e`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/194c22e871235e16033ccac2a29ed4e7d2e822de) | kk: Implement buffer marker AMD | Vulkan 1.4.358 |
| [v26.3.0-20260811](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811) | 2026-08-11 | [`1b2e70d`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/1b2e70de00f68f8cf32dca8cd1a64fba9b6410a8) | nak: improve implementation of global_bounded | Vulkan 1.4.358 |
| [v26.3.0-20260810-r14](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260810-r14) | 2026-08-10 | [`fc8b192`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/fc8b1928cbc21099d1428299bf7d0c86da9f7b65) | intel/compiler: Don't vectorize URB access to vec8 in SIMD32 | Vulkan 1.4.358 |
| [v26.3.0-20260810-r13](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260810-r13) | 2026-08-10 | [`62585e8`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/62585e8940a6ccb920e7b5bd8bc1235e6cabedc2) | anv: Close shader dump archive on device destruction | Vulkan 1.4.358 |
| [v26.3.0-20260810-r12](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260810-r12) | 2026-08-10 | [`e408d9a`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e408d9abd32d0f3f7621fd7cbcc018f635d24531) | iris: Initialize source hash in program data | Vulkan 1.4.358 |
| [v26.3.0-20260810-r11](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260810-r11) | 2026-08-10 | [`b587ce6`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/b587ce63f66f0a6b5136bd5d27d6f793410629ad) | brw: Respect execution mask when resetting GS control data | Vulkan 1.4.358 |
| [v26.3.0-20260810-r10](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260810-r10) | 2026-08-10 | [`74d4e41`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/74d4e41b2bb1e77ef4e022a6a1329d6cc782c4c6) | tu: Use correct pointer for vis stream patchpoint cs fence | Vulkan 1.4.358 |
| [v26.3.0-20260810-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260810-r9) | 2026-08-10 | [`9bbf48e`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/9bbf48eed3cf5ec67d7cf44de9f4fb46e629bc27) | mediafoundation: shut down the event queue. | Vulkan 1.4.358 |
| [v26.3.0-20260810-r8](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260810-r8) | 2026-08-10 | [`34b78fb`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/34b78fb26b9b1b3f52c81de538ebbad1c994b293) | freedreno/a2xx: fix the window scissor losing a row and a column | Vulkan 1.4.358 |
| [v26.3.0-20260810-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260810-r7) | 2026-08-10 | [`742af79`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/742af792775f21e29e154a4e35b8c1a2e3103de4) | radv/meta: fix resolving to 3D color images | Vulkan 1.4.358 |
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

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
| **Vulkan version** | Vulkan 1.4.359 |
| **Commit** | [`bb63b17`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/bb63b1797b657b64dac605391d251a22e1c9cefc) |
| **Commit date** | 2026-08-26 |
| **Commit title** | amd/virtio: request deferred mapping for blob BOs |
| **Build date** | 20260826 |
| **Release** | [v26.3.0-20260826-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260826-r3) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.3.0-20260826-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260826-r3) | 2026-08-26 | [`bb63b17`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/bb63b1797b657b64dac605391d251a22e1c9cefc) | amd/virtio: request deferred mapping for blob BOs | Vulkan 1.4.359 |
| [v26.3.0-20260826-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260826-r2) | 2026-08-26 | [`28ce274`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/28ce274f4e5b0da78025b36c32f239549e09d012) | spirv: Fix bounds check in OpSpecConstantOp CompositeExtract/Insert | Vulkan 1.4.359 |
| [v26.3.0-20260826](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260826) | 2026-08-26 | [`5244626`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/52446262113329de9cdaab59de8713a2215b2f5e) | spirv: Narrow the VectorShuffle undef marker to the component bit size | Vulkan 1.4.359 |
| [v26.3.0-20260825-r15](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r15) | 2026-08-25 | [`8cc4fe5`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/8cc4fe51fe781163d0345320a7a04520ecfcdb8d) | panvk/android: avoid pNext injection of caller ANB info | Vulkan 1.4.359 |
| [v26.3.0-20260825-r14](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r14) | 2026-08-25 | [`d286f87`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/d286f87b1641abce126337f99caa13b11ae8ef5b) | freedreno/fdl: Fix gen8 multi-plane descriptor base | Vulkan 1.4.359 |
| [v26.3.0-20260825-r13](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r13) | 2026-08-25 | [`d88f9b7`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/d88f9b74d4f2cb43ea95e80951ade99381339d3a) | gfxstream/meson: drop unused include_directories() | Vulkan 1.4.359 |
| [v26.3.0-20260825-r12](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r12) | 2026-08-25 | [`27bf3ee`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/27bf3ee4c2b2993f2a513b12c0d81f91e6e0a529) | kk: Connect VK_EXT_debug_utils labels to Metal | Vulkan 1.4.359 |
| [v26.3.0-20260825-r11](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r11) | 2026-08-25 | [`ab4a67a`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/ab4a67a17a6402417343076f98131460ddbf2e92) | radv: fix and improve vkCmdSetEvent2 / vkCmdResetEvent2 | Vulkan 1.4.359 |
| [v26.3.0-20260825-r10](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r10) | 2026-08-25 | [`7403042`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/74030424e6ed5cc404055bb1afb3221bdec07897) | broadcom/compiler: fill the old value when spilling a partial write | Vulkan 1.4.359 |
| [v26.3.0-20260825-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r9) | 2026-08-25 | [`dc33057`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/dc330577adb9e98363ef6061e09062f171d0d053) | amd/common: update TRUNC_COORD documentation | Vulkan 1.4.359 |
| [v26.3.0-20260825-r8](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r8) | 2026-08-25 | [`1eb29b2`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/1eb29b2f2f0f8a7c0a0d1251d9f26c5fb5d26902) | v3dv: keep CPU mapping alive for the cached BOs | Vulkan 1.4.359 |
| [v26.3.0-20260825-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r7) | 2026-08-25 | [`630840b`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/630840b3333ac6eafce6029ad153a47db97dd091) | amd/common/virtio: fix import/free race that detaches a live res_id | Vulkan 1.4.359 |
| [v26.3.0-20260825-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r6) | 2026-08-25 | [`e79595e`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e79595e37b64d6c84b1962f5adc1bb61fa2ef165) | radeonsi/ci: update expectations | Vulkan 1.4.359 |
| [v26.3.0-20260825-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r5) | 2026-08-25 | [`2aa64dc`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/2aa64dcf1ceb523aca350a25ef64adb3437d35ab) | radv: enable HTILE for mips+layers on GFX10+ | Vulkan 1.4.359 |
| [v26.3.0-20260825-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r4) | 2026-08-25 | [`9bb9a74`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/9bb9a74414d69c18eadc5a01b1efe04a6928da51) | freedreno, tu: Limit XFB streams on GPUs lacking multi-stream query support | Vulkan 1.4.359 |
| [v26.3.0-20260825-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r3) | 2026-08-25 | [`7fa9a25`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/7fa9a25398a75fb7ef3c0656e4667ff9f6e9f2c1) | kk: Add feature check when setting depth bounds test | Vulkan 1.4.359 |
| [v26.3.0-20260825-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260825-r2) | 2026-08-25 | [`4412e09`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/4412e0924c9440910f3f25c5585b34d03cba9748) | mesa/st: don't pass stale VBO offsets as user pointers in core profiles | Vulkan 1.4.359 |
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

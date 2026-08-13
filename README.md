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
| **Commit** | [`70fec01`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/70fec0194d4a271003182f806ee06eb159967ce0) |
| **Commit date** | 2026-08-13 |
| **Commit title** | v3d: fix data in get UBO size |
| **Build date** | 20260813 |
| **Release** | [v26.3.0-20260813-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260813-r6) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.3.0-20260813-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260813-r6) | 2026-08-13 | [`70fec01`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/70fec0194d4a271003182f806ee06eb159967ce0) | v3d: fix data in get UBO size | Vulkan 1.4.359 |
| [v26.3.0-20260813-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260813-r5) | 2026-08-13 | [`771ade1`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/771ade18e3f5068e59a523d7a5538b0160acb750) | anv: flush L1/L2 caches on end of command buffer | Vulkan 1.4.359 |
| [v26.3.0-20260813-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260813-r4) | 2026-08-13 | [`15fd588`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/15fd588bae91a937a96ed3af6432ccf9ee6e891a) | radv: fix cmdbuf alignment with DGC when queues aren't enabled | Vulkan 1.4.359 |
| [v26.3.0-20260813-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260813-r3) | 2026-08-13 | [`b69016a`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/b69016a721dbcb9d0ba96c4917f68d91e935bc49) | radeonsi: Enable NV_timeline_semaphore with userq | Vulkan 1.4.359 |
| [v26.3.0-20260813-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260813-r2) | 2026-08-13 | [`c3105f2`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/c3105f2cf210deb2f6df71d5ff7b7241991c2359) | panfrost: allow explicit layout for array images | Vulkan 1.4.359 |
| [v26.3.0-20260813](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260813) | 2026-08-13 | [`ac021d1`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/ac021d175341483cd267111d5cc160a4a8fa7c16) | subprojects: Use CDN URLs for crates.io | Vulkan 1.4.359 |
| [v26.3.0-20260812-r15](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r15) | 2026-08-12 | [`175e1f3`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/175e1f3cf5347c8a9a104dfcd64d32d7583642b2) | nir: Set info->fs.color_is_dual_source for DUAL_SRC_BLEND var locations | Vulkan 1.4.359 |
| [v26.3.0-20260812-r14](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r14) | 2026-08-12 | [`769b2d6`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/769b2d6ab13ca509487ff38f12a0bdb892343c17) | anv: fix upload of shader kernels spanning more than one heap BO | Vulkan 1.4.359 |
| [v26.3.0-20260812-r13](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r13) | 2026-08-12 | [`127e7cb`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/127e7cb8ca0bbafe915095db872e1a0a96b19de5) | tu: CmdSetRenderingInputAttachmentIndices should dirty LRZ | Vulkan 1.4.359 |
| [v26.3.0-20260812-r12](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r12) | 2026-08-12 | [`e2c33e7`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e2c33e79025d7bc2eb6cdce21353cee71bb63491) | pvr: fix sampler handle dereference with immutable samplers | Vulkan 1.4.359 |
| [v26.3.0-20260812-r11](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r11) | 2026-08-12 | [`e651fb7`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e651fb738a6110049c8546b23796d40ec454e323) | brw: Vectorize URB for task and mesh shaders after SIMD is set | Vulkan 1.4.359 |
| [v26.3.0-20260812-r10](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r10) | 2026-08-12 | [`c5138d5`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/c5138d5f2bfbb41b787ab6cf87525b6dbe2d6cdc) | mesa/shader_query: Handle SPIR-V built-ins in validate_io | Vulkan 1.4.359 |
| [v26.3.0-20260812-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r9) | 2026-08-12 | [`61f62f5`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/61f62f590d026f80d22976371719ff8bb7d9e66c) | gfxstream: default unknown AHB dataspace to BT.709 (sRGB) | Vulkan 1.4.359 |
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

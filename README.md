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
| **Commit** | [`724bffd`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/724bffde435bd1055a07db34cd8252d809d37a4f) |
| **Commit date** | 2026-08-12 |
| **Commit title** | radv/ci: use all drm-shim devices in radv-validate-cache |
| **Build date** | 20260812 |
| **Release** | [v26.3.0-20260812-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r7) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.3.0-20260812-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r7) | 2026-08-12 | [`724bffd`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/724bffde435bd1055a07db34cd8252d809d37a4f) | radv/ci: use all drm-shim devices in radv-validate-cache | Vulkan 1.4.358 |
| [v26.3.0-20260812-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r6) | 2026-08-12 | [`976b8f4`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/976b8f4754520fa3434b0f3a0bac97468da42fc7) | ac/uvd: Make create cmd work with duplicate handle on UVD < 6.3 | Vulkan 1.4.358 |
| [v26.3.0-20260812-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r5) | 2026-08-12 | [`5af4976`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/5af4976e23a6dd361f5a1e0d26595b47d228c191) | radeonsi/mm: Don't use HEVC per slice loop filter across slices on old FW | Vulkan 1.4.358 |
| [v26.3.0-20260812-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r4) | 2026-08-12 | [`2c4ebcd`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/2c4ebcdef8ebf72a6296d62b7c04b63f0469bb18) | nir/opt_cse: CSE subgroup ops per block | Vulkan 1.4.358 |
| [v26.3.0-20260812-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r3) | 2026-08-12 | [`faf1cd2`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/faf1cd2de8f05fe7fcfce2d0ffdb8fb1f933a579) | radv: fix redundant WSI destroy | Vulkan 1.4.358 |
| [v26.3.0-20260812-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812-r2) | 2026-08-12 | [`b7314ee`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/b7314eec75b007efd0569cbd1df046e6da3b6e90) | kk: Move kk_buffer Metal members into its own struct | Vulkan 1.4.358 |
| [v26.3.0-20260812](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260812) | 2026-08-12 | [`eb03131`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/eb03131ca07be8a8f4abd09fcae66686007afd13) | brw/rt: Accept hit directly based on condition | Vulkan 1.4.358 |
| [v26.3.0-20260811-r18](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r18) | 2026-08-11 | [`064cbe8`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/064cbe8aabe117766b59fc7bf4745598c75bbf90) | freedreno/a2xx: let nir lower fsign | Vulkan 1.4.358 |
| [v26.3.0-20260811-r17](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r17) | 2026-08-11 | [`aa6f912`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/aa6f9121f0fb76446f1fb48cb9284380a64f9686) | anv: let's not crash everywhere | Vulkan 1.4.358 |
| [v26.3.0-20260811-r16](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r16) | 2026-08-11 | [`76e9e97`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/76e9e975a4f530a160efcb86fb8bf62ebe5dfc77) | anv: fix binding mode flush | Vulkan 1.4.358 |
| [v26.3.0-20260811-r15](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r15) | 2026-08-11 | [`47bc087`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/47bc0871f64477bf2d013bfab1c0774a221ef5cf) | freedreno/ci: Switch a200 to gfx-ci/linux kernel | Vulkan 1.4.358 |
| [v26.3.0-20260811-r14](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r14) | 2026-08-11 | [`fdaeb5a`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/fdaeb5a757599841ec9c95a548f8849066bd2fc3) | etnaviv: reorder state emission to optimize loads | Vulkan 1.4.358 |
| [v26.3.0-20260811-r13](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r13) | 2026-08-11 | [`58f6bc5`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/58f6bc5eab77cd818d0a0e20d32c6859b67ed174) | anv: remove all code related to INTEL_performance_query not using metrics_library | Vulkan 1.4.358 |
| [v26.3.0-20260811-r12](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r12) | 2026-08-11 | [`56f473c`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/56f473cc63e86c74e815c5f44e3cdc7ddd6d665f) | freedreno/a2xx: read gl_FragCoord from the component asked for | Vulkan 1.4.358 |
| [v26.3.0-20260811-r11](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r11) | 2026-08-11 | [`b061696`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/b0616965331138387d63402f1d17f4ecc5245511) | kk: Fix disable of workaround 8 | Vulkan 1.4.358 |
| [v26.3.0-20260811-r10](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r10) | 2026-08-11 | [`64dbbfe`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/64dbbfe03429ee4e3b80e3d88ef8000084d15ff8) | radv: run nir_opt_dead_cf before nir_vk_lower_ycbcr_tex | Vulkan 1.4.358 |
| [v26.3.0-20260811-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r9) | 2026-08-11 | [`94073fb`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/94073fb459293cebe10c4e74ee28e7d2879cc917) | pan/genxml/v14: Clean up format list | Vulkan 1.4.358 |
| [v26.3.0-20260811-r8](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260811-r8) | 2026-08-11 | [`e1ef8f0`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e1ef8f046c6e37ec1e2a13229560fbb824e5118f) | pvr: advertise KHR_shader_fma | Vulkan 1.4.358 |
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

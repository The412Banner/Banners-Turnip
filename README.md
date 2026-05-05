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
| **Vulkan version** | Vulkan 1.4.350 |
| **Commit** | [`ec42f87`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/ec42f873e9f6dfc52bb5ea33c80c91780b236ce6) |
| **Commit date** | 2026-05-05 |
| **Commit title** | tu: Fix tu_bo_make_zombie without queues |
| **Build date** | 20260505 |
| **Release** | [v26.2.0-20260505-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260505-r6) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.2.0-20260505-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260505-r6) | 2026-05-05 | [`ec42f87`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/ec42f873e9f6dfc52bb5ea33c80c91780b236ce6) | tu: Fix tu_bo_make_zombie without queues | Vulkan 1.4.350 |
| [v26.2.0-20260505-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260505-r5) | 2026-05-05 | [`27c870a`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/27c870a28359644363547cdc0b18e36fc230e4ba) | st/mesa: fix implicit conversion warning in st_atom_framebuffer | Vulkan 1.4.350 |
| [v26.2.0-20260505-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260505-r4) | 2026-05-05 | [`49c6589`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/49c658972f7614e9660fb86fe4303798b129f5b9) | ir3: mark __alias_n as UNUSED in foreach_src_in_alias_group_n | Vulkan 1.4.350 |
| [v26.2.0-20260505-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260505-r3) | 2026-05-05 | [`87be392`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/87be392251ce04a7755dc05d2d186c2cbffc295f) | radv: fix determining needed dynamic states when rasterization is disabled | Vulkan 1.4.350 |
| [v26.2.0-20260505-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260505-r2) | 2026-05-05 | [`a9b28b9`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/a9b28b9838745814a2eead1e34c60b536c2cf099) | pan/nir: Lower texel buffers in nir_lower_tex() | Vulkan 1.4.350 |
| [v26.2.0-20260505](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260505) | 2026-05-05 | [`1883f30`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/1883f3094fdf4bb4498fb0e778f96577b86342ea) | ci: uprev virglrenderer | Vulkan 1.4.350 |
| [v26.2.0-20260504-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260504-r7) | 2026-05-04 | [`af746cc`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/af746cc2a6498fd7acbbe8fc3b632d6f58d7ac86) | radv/rt: Use 64-bit keys for gfx11- | Vulkan 1.4.350 |
| [v26.2.0-20260504-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260504-r6) | 2026-05-04 | [`a2175b7`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/a2175b7ec365e1c52756f91e45fef3c3bd9af549) | iris: Improve and standardize the behavior of madvice in i915 | Vulkan 1.4.350 |
| [v26.2.0-20260504-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260504-r5) | 2026-05-04 | [`352a8d6`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/352a8d6beb61767406026b2e2db6628210115e80) | pan/compiler: Clamp fp16 ldexp exponent range | Vulkan 1.4.348 |
| [v26.2.0-20260504-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260504-r4) | 2026-05-04 | [`0ff1650`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/0ff16506628216e06d876aab5cc498f71067b2af) | ac/nir/lower_tex_coord: fix moving wqm coordinates | Vulkan 1.4.348 |
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

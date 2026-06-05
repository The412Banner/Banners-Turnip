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
| **Vulkan version** | Vulkan 1.4.353 |
| **Commit** | [`6a16319`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/6a16319133d3d172f1c8fe5e213394ef831805e0) |
| **Commit date** | 2026-06-05 |
| **Commit title** | radv/rt: Cache stack sizes of ahit/isec shaders from imported NIR |
| **Build date** | 20260605 |
| **Release** | [v26.2.0-20260605-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260605-r5) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.2.0-20260605-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260605-r5) | 2026-06-05 | [`6a16319`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/6a16319133d3d172f1c8fe5e213394ef831805e0) | radv/rt: Cache stack sizes of ahit/isec shaders from imported NIR | Vulkan 1.4.353 |
| [v26.2.0-20260605-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260605-r4) | 2026-06-05 | [`9f7f5a2`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/9f7f5a27a7edc49487af3cd10633896934a47295) | mesa/main: Auto-generate MESA_VERBOSE=api trace dispatch | Vulkan 1.4.352 |
| [v26.2.0-20260605-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260605-r3) | 2026-06-05 | [`b6661df`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/b6661df5f055ae66898e5a4facb5d4e1b501a1ec) | vulkan: Enable GOOGLE_display_timing on KHR_display across multiple drivers. | Vulkan 1.4.352 |
| [v26.2.0-20260605-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260605-r2) | 2026-06-05 | [`e984014`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e984014d56f55b5d9f8b641e10ad3cc43e1b4e0c) | turnip: declare common VK drirc options using the helper | Vulkan 1.4.352 |
| [v26.2.0-20260605](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260605) | 2026-06-05 | [`e84e9dc`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e84e9dc582797b5e586ea4ff3ae7b5f3656968ee) | gallivm: Fix armhf build against LLVM 22 | Vulkan 1.4.352 |
| [v26.2.0-20260604-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260604-r9) | 2026-06-04 | [`a6172f1`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/a6172f19a0915fc690104a02e894b263d982e247) | vtn/opencl: fix edge case behavior for tanpi | Vulkan 1.4.352 |
| [v26.2.0-20260604-r8](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260604-r8) | 2026-06-04 | [`3a815a5`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/3a815a596935c2ec9ba218829861d948ce2a17d1) | nir: preserve infinities and signed zero during atan2 | Vulkan 1.4.352 |
| [v26.2.0-20260604-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260604-r7) | 2026-06-04 | [`c634bf1`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/c634bf11ce0124a87405ff196fc953799a365e0b) | drm-shim/freedreno: Report VM_BIND support. | Vulkan 1.4.352 |
| [v26.2.0-20260604-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260604-r6) | 2026-06-04 | [`1375ba2`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/1375ba209d9ec225f65a0f0ccd9e824304c39b4f) | ac: add basic HTILE dword printing | Vulkan 1.4.352 |
| [v26.2.0-20260604-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260604-r5) | 2026-06-04 | [`364b5f8`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/364b5f806ccc7f27e97caef6a5abf995fb6c2b7f) | compiler/rust/smallvec: Optimize extend() | Vulkan 1.4.352 |
| [v26.2.0-20260604-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.2.0-20260604-r4) | 2026-06-04 | [`bea1212`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/bea1212ee710d36bddb08b720734cc2eefc871b1) | anv/video: Change size of the cached array of recently decoded AV1 frames. | Vulkan 1.4.352 |
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

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
| **Commit** | [`fcee81a`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/fcee81a38d8e4b4c77c3d45261e2d50205b6400f) |
| **Commit date** | 2026-08-18 |
| **Commit title** | spirv: Discard excess image coordinate components |
| **Build date** | 20260818 |
| **Release** | [v26.3.0-20260818-r19](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r19) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.3.0-20260818-r19](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r19) | 2026-08-18 | [`fcee81a`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/fcee81a38d8e4b4c77c3d45261e2d50205b6400f) | spirv: Discard excess image coordinate components | Vulkan 1.4.359 |
| [v26.3.0-20260818-r18](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r18) | 2026-08-18 | [`7cee821`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/7cee821cdec35e68d46c5313db19488b9bbe116e) | rusticl: fix wrong destination offset in Image::copy_to_buffer | Vulkan 1.4.359 |
| [v26.3.0-20260818-r17](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r17) | 2026-08-18 | [`3c56bd8`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/3c56bd8ded62ba90a766254b4d985ef8197d8787) | etnaviv: Cache the shader key and variant lookup | Vulkan 1.4.359 |
| [v26.3.0-20260818-r16](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r16) | 2026-08-18 | [`ecbc99d`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/ecbc99d70862f3f4d842657558e1ec51abc09033) | gfxstream: map DRM_FORMAT_ARGB8888/XRGB8888 to VK_FORMAT_B8G8R8A8_UNORM | Vulkan 1.4.359 |
| [v26.3.0-20260818-r15](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r15) | 2026-08-18 | [`7f760b8`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/7f760b878f2686de303b5d07512ad3a2ca1ab441) | ir3: Handle sparse loads in ir3_nir_lower_64b_image | Vulkan 1.4.359 |
| [v26.3.0-20260818-r14](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r14) | 2026-08-18 | [`b87749b`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/b87749b99a30ffab4cf2bd1d7e1d85feccf7428b) | tool/gamma: Add virtual destructor for gamma_file_view | Vulkan 1.4.359 |
| [v26.3.0-20260818-r13](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r13) | 2026-08-18 | [`0f06239`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/0f062397ced784087ad1e1de3b886402e8a1d5d8) | nak: call nir_opt_move_discards_to_top | Vulkan 1.4.359 |
| [v26.3.0-20260818-r12](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r12) | 2026-08-18 | [`dcb4727`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/dcb47270b483a3e9c34847dcdc31d0fa74a3414f) | radv/gamma: Fix geometry counts | Vulkan 1.4.359 |
| [v26.3.0-20260818-r10](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r10) | 2026-08-18 | [`d22b355`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/d22b355f035c57d2051575cd93c05bb98dbb455e) | panvk/utrace: handle clone CS heap exhaustion gracefully | Vulkan 1.4.359 |
| [v26.3.0-20260818-r9](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r9) | 2026-08-18 | [`1a12d71`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/1a12d7188b46703d433f4d909b0e8e0d6c5bbe5d) | radv: disable nir_opt_reassociate_for_fma for VS if it's not the last pre FS shader | Vulkan 1.4.359 |
| [v26.3.0-20260818-r8](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r8) | 2026-08-18 | [`f38b05e`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/f38b05eaaf2d4f570fa417c6ac3fe80939d71c47) | radv/meta: fix using aspects for blits | Vulkan 1.4.359 |
| [v26.3.0-20260818-r7](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r7) | 2026-08-18 | [`ec9f041`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/ec9f0419f530119537d822b206c40c4b9f4cb873) | tu: Allow multi-layer images with explicit DRM format modifiers | Vulkan 1.4.359 |
| [v26.3.0-20260818-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r6) | 2026-08-18 | [`9075f69`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/9075f69cd0cb55e126d88ab91e547ecec0cba560) | radv/ci: add khronos link to the bfloat16 dequant failures. | Vulkan 1.4.359 |
| [v26.3.0-20260818-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r5) | 2026-08-18 | [`2c6740b`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/2c6740b0394cccdaad916052f17eddf9e7534ba9) | anv: Add drirc option to disable dynamicStackIDControl | Vulkan 1.4.359 |
| [v26.3.0-20260818-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r4) | 2026-08-18 | [`85d08fe`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/85d08fe5557c755e628e36ff31c242499c749c96) | radv: Wait for L2 cache writeback on ACE for SDMA+ACE gangs | Vulkan 1.4.359 |
| [v26.3.0-20260818-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r3) | 2026-08-18 | [`728fd22`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/728fd222ce70b0e5415e39d1a796b9b60b8a4679) | kraid: Drop support for load_layer_id | Vulkan 1.4.359 |
| [v26.3.0-20260818-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818-r2) | 2026-08-18 | [`e1c6bf8`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/e1c6bf8d20713261c2cba57b59b93cc5e75d08e4) | nir/search: reset FP state for commutative match attempts | Vulkan 1.4.359 |
| [v26.3.0-20260818](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20260818) | 2026-08-18 | [`c14545d`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/c14545d36aff5f21b3174ed6b4514926fff23606) | radv: tidy up declaring CS_TASK_DRAW_ID for task shaders | Vulkan 1.4.359 |
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

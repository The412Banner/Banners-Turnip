<p align="center">
  <img src="logo.png" alt="Banners-Turnip" width="600"/>
</p>

# Banners-Turnip
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/n8S4G2WZQ4)


> Automated, bleeding-edge builds of the [Mesa Turnip](https://docs.mesa3d.org/drivers/freedreno.html) Vulkan driver, compiled directly from the latest upstream Mesa commits. Every release ships each driver three times: for [AdrenoTools](https://github.com/K11MCH1/AdrenoToolsDrivers)-compatible apps (X11), for Bannerlator Wayland containers, and as a glibc ICD for Bannerlator's Linux runtime and native Steam client.

[![Build Turnip (Combined)](https://github.com/The412Banner/Banners-Turnip/actions/workflows/turnip_build_combined.yml/badge.svg?branch=A8xx)](https://github.com/The412Banner/Banners-Turnip/actions/workflows/turnip_build_combined.yml)
[![Latest Release](https://img.shields.io/github/v/release/The412Banner/Banners-Turnip?label=latest%20release&color=blue)](https://github.com/The412Banner/Banners-Turnip/releases/latest)

---

## What Is This?

[Turnip](https://docs.mesa3d.org/drivers/freedreno.html) is the open-source Mesa Vulkan driver for Qualcomm Adreno GPUs — developed as part of the [Mesa](https://gitlab.freedesktop.org/mesa/mesa) project and maintained by the Freedreno community. Unlike the proprietary Qualcomm driver, Turnip is fully open-source and often ships fixes and feature support ahead of official Qualcomm releases.

This repo automatically builds Turnip from the absolute latest commit on `mesa/main` — no waiting for official Mesa releases. A [Mesa upstream watcher](.github/workflows/mesa-watcher.yml) polls for new commits every hour and triggers a fresh build automatically whenever `mesa/main` advances. Each driver comes as three ZIPs from the same Mesa commit and patches:

- an [AdrenoTools](https://github.com/K11MCH1/AdrenoToolsDrivers)-compatible ZIP you can drop straight into any compatible app (BannerHub/BCI, Winlator, Bannerlator X11, etc.);
- a **Wayland** ZIP for Bannerlator Wayland containers;
- a **Linux** ZIP for Bannerlator's Linux runtime — the gamescope session that runs Valve's native ARM64 Steam client.

The three differ in what they link against, which is what decides where each one can be loaded: the first two are **bionic** (Android) objects, the Linux one is **glibc**. A process can only load its own.

---

## Driver Variants & Downloads

Each release ships four drivers, each as three ZIPs built from the same Mesa commit and patches. Pick the driver for your GPU, then the ZIP for where you use it:

| Driver | GPUs | X11 / AdrenoTools ZIP | Bannerlator Wayland ZIP | Linux runtime ZIP |
| :--- | :--- | :--- | :--- | :--- |
| **Standard** | Adreno 6xx / 7xx (Snapdragon 8 Gen 3 and older) | `Turnip-<tag>.zip` | `Turnip-<tag>-Wayland.zip` | `Turnip-<tag>-Linux.zip` |
| **A8xx** (experimental) | Adreno 810 / 825 / 829 / 830 / 840 (Snapdragon 8 Elite) | `Turnip-<tag>-A8xx.zip` | `Turnip-<tag>-A8xx-Wayland.zip` | `Turnip-<tag>-A8xx-Linux.zip` |
| **A710 / A720 / A722** (experimental) | Adreno 710 / 720 / 722 | `Turnip-<tag>-710-720-Test.zip` | `Turnip-<tag>-710-720-Test-Wayland.zip` | `Turnip-<tag>-710-720-Test-Linux.zip` |
| **8 Gen 2 One UI** | Adreno 740 (Snapdragon 8 Gen 2) whose UI glitches with Standard, e.g. Samsung One UI | `Turnip-<tag>-8G2-OneUI.zip` | `Turnip-<tag>-8G2-OneUI-Wayland.zip` | `Turnip-<tag>-8G2-OneUI-Linux.zip` |

- **X11 / AdrenoTools ZIP:** BannerHub/BCI, Winlator, Bannerlator X11 containers and any other AdrenoTools app. This is also the driver that **puts the finished frame on the screen** on every path below — it is the only one with the Android surface WSI.
- **Wayland ZIP:** Bannerlator **Wayland containers** only. It's a Linux-style Vulkan driver (KGSL, Wayland, bionic) with Bannerlator's zero-copy patch, built by [`build_turnip_wayland.sh`](build_turnip_wayland.sh). It doesn't load as an AdrenoTools driver, and an X11 ZIP doesn't work as a Wayland game driver.
- **Linux runtime ZIP:** Bannerlator's **Linux runtime** — the gamescope session running Valve's native ARM64 Steam client. It's a **glibc** Vulkan ICD (KGSL, Wayland + X11 WSI) built by [`build_turnip_linux.sh`](build_turnip_linux.sh) against the same Arch Linux ARM packages that runtime is made of, plus the two KGSL fixes it needs ([`patches/linux/`](patches/linux)) and the fixes every ZIP carries ([`patches/common/`](patches/common)). It draws the Steam client's own UI (OpenGL → Zink → Vulkan) and every game the client launches (D3D → DXVK/VKD3D → Vulkan). The client and its games are glibc processes, so neither bionic ZIP can be loaded by them at all — and this one can't be loaded by an Android app or a Wine container. It ships the ICD and its manifest only; the libraries are the runtime's own.
- CI checks every ZIP before it's attached. If a Wayland or Linux build fails, the release still ships its X11 ZIPs and the release notes say which ZIP is missing.

[**Download latest →**](https://github.com/The412Banner/Banners-Turnip/releases/latest) · [**Full build history →**](Mesa-commit-history.md)

### Fixes in every driver

These are bugs in Turnip's Adreno (KGSL) code that are **still in Mesa `main`**, so every ZIP carries a fix: Standard, A8xx, A710/720/722 and 8 Gen 2 One UI, for X11, Wayland and Linux alike. They live in [`patches/common/`](patches/common) and are applied by [`apply_common.sh`](patches/common/apply_common.sh), which fails the build if a fix goes missing. Each one is dropped once Mesa carries its own fix. Full notes: [`patches/common/SOURCE`](patches/common/SOURCE). Max's WinNative series (mesh shaders, wave32, A8xx hang fixes) is [A8xx only](#a8xx--experimental).

| Fix | What was wrong | What it changes |
| :--- | :--- | :--- |
| [`kgsl-zero-timeout-poll.patch`](patches/common/kgsl-zero-timeout-poll.patch) — *DirectX 12 no longer waits on the GPU every frame* | A quick "has the GPU finished yet?" check was sent to the kernel as a wait with a zero time limit, and the Adreno kernel driver reads zero as "wait forever". VKD3D-Proton makes that check on every frame, so the CPU and GPU took turns instead of working at the same time. | The check now reads the GPU's last finished job and answers at once. On an Adreno 750, a DirectX 12 demo went from 378 to 1422 fps on X11 and from 588 to 3449 fps on Bannerlator's Wayland. [Full report](docs/KGSL_ZERO_TIMEOUT_POLL.md). |
| [`kgsl-syncobj-merge-ts-fd.patch`](patches/common/kgsl-syncobj-merge-ts-fd.patch) — *no crash when a frame waits on two kinds of sync* | When a submit waited on a GPU timestamp and a sync file together, the driver converted the wrong one and crashed. Cemu does that on every frame, so it crashed on its first frame. | The timestamp side is turned into the sync file and merged correctly. Proven with Cemu, RPCS3 and Dolphin in DroidDeck. |

### A6xx / A7xx — Standard

Mesa `main` plus the [fixes every driver carries](#fixes-in-every-driver), with no GPU-specific patches. No mesh shaders or wave32: on A7xx those can steer DirectX 12 games onto slower emulated paths, so they stay on the A8xx driver. Compatible with Adreno 600–700 series GPUs (Snapdragon 600–800 series, including 7 Gen and 8 Gen 1–3).

### 8 Gen 2 One UI

Standard plus [`8g2_oneui.py`](patches/8g2_oneui.py), which turns on `enable_tp_ubwc_flag_hint` for the Adreno 740. That setting has to match between every driver on the device, or scaled copies come out corrupted. Mesa leaves it off to match the older system driver most 8 Gen 2 devices ship. Newer firmware such as recent Samsung One UI turns it on, so with the Standard driver the phone's UI glitches or flickers. Use this driver only if you see that; on other 8 Gen 2 devices it causes the same glitch. To try it without changing driver, set `FD_DEV_FEATURES=enable_tp_ubwc_flag_hint=1` (Bannerlator has this as a checkbox in the container's graphics driver settings). Other GPUs are unaffected.

### A710 / A720 / A722 — Experimental / Work in Progress

Injects hardware-specific GPU entries and magic registers for Adreno 710, 720, and 722 on top of Mesa `main` via [`a710-720.py`](patches/a710-720.py) — based on community research by [Vauzi-17](https://github.com/Vauzi-17/710). No upstream Mesa support exists for these GPUs yet. Early results are promising. Recommended: force sysmem mode via `TU_DEBUG=sysmem` until GMEM is confirmed stable. Winlator users: set `WRAPPER_BLIT=1`.

### A8xx — Experimental

Targets Adreno 800-series (Snapdragon 8 Elite — A810, A825, A829, A830, A840). Built from Mesa `main` with the [fixes every driver carries](#fixes-in-every-driver) and the following on top (the same for the X11, Wayland and Linux ZIPs). Max's WinNative series ([`patches/a8xx-winnative/`](patches/a8xx-winnative), from [WinNative-Emu/Drivers](https://github.com/WinNative-Emu/Drivers)) is applied by `apply_common.sh` for this driver only:

| Patch | What it does |
| :--- | :--- |
| [`a8xx_gen8.patch`](patches/a8xx_gen8.patch) | 12 commits from whitebelyash's [`turnip/gen8`](https://github.com/whitebelyash/mesa-unified) stack (as shipped in tu_v29 / StevenMXZ v33): A8xx GPU configs, UBWC gralloc detection, `disable_gmem` GPU property, Steam Deck spoof (`TU_DEBUG=deck_emu`), A810 fixes |
| [`a8xx_shared_mem.py`](patches/a8xx_shared_mem.py) | `cs_shared_mem_size` 32 KiB → 64 KiB on every device entry |
| [`a8xx-winnative/0001`](patches/a8xx-winnative/0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch), [`0002`](patches/a8xx-winnative/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch) — *DirectX 12 Ultimate: mesh shaders + wave32* | Turnip has no `VK_EXT_mesh_shader`, so VKD3D-Proton can't offer DX12 mesh shaders, and it rejects `WaveSize(32)` shaders on A8xx's 64-wide waves. Games that need them (FINAL FANTASY VII REBIRTH, Alan Wake 2) render wrong or not at all. Task and mesh shaders run as compute into a ring that a generated vertex shader draws; render passes with mesh draws use sysmem. (Upstream it would also switch on for A7xx; this repo builds it into the A8xx driver only.) A required subgroup size of 32 works on A8xx (each half-wave is a subgroup). From Max (MaxsTechReview) in [WinNative-Emu/Drivers](https://github.com/WinNative-Emu/Drivers). |
| [`a8xx-winnative/0003`](patches/a8xx-winnative/0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch), [`0004`](patches/a8xx-winnative/0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch), [`0005`](patches/a8xx-winnative/0005-tu-kgsl-Fetch-A8XX-command-streams-through-a-virtual.patch) — *A8xx GPU hangs* | Three Adreno 8xx hangs found in FINAL FANTASY VII REBIRTH: a cube-map lookup with an empty direction, stale bindless descriptors, and freeing command memory. Each fix only takes effect on Adreno 8xx; older GPUs are unchanged. Max's IB cache (0006) is left out: it broke the Linux driver on some Adreno 840s. From Max, as above. |

Tips: `TU_DEBUG=sysmem` if an A830 looks glitchy; `TU_DEBUG=deck_emu` if a game won't start. **Use at your own risk.**

---

## Workflows

| Workflow | Trigger | What it builds |
| :--- | :--- | :--- |
| **Build Turnip (Combined)** | Auto (mesa-watcher) or manual | Standard + A8xx + A710/A720/A722, Android, Wayland and Linux builds in parallel from one Mesa commit; each ZIP is checked in CI, then published as a single tagged release with notes written from what built (manual runs can set `dry_run` to build and verify without publishing) |
| **Build Turnip A8xx (Experimental)** | Manual | Standalone A8xx test build — faster iteration outside the release cycle |
| **Build Turnip (Perf 6xx/7xx)** | Manual | A6xx/A7xx only, compiled with `-O3` + ThinLTO for performance testing |

---

## Installation

- **BannerHub / BCI:** Component Manager → Add New Component → select the X11 / AdrenoTools ZIP
- **AdrenoTools-compatible apps (Winlator, Bannerlator X11, etc.):** load the X11 / AdrenoTools ZIP in GPU driver settings
- **Bannerlator Wayland containers:** *Import Wayland game driver (.zip)* → select the `-Wayland.zip`, then pick it as the container's Wayland game driver
- **Bannerlator Linux runtime (native Steam client):** import the `-Linux.zip` as the Linux shortcut's driver; it replaces the runtime's own `usr/lib/libvulkan_freedreno.so`

---

## Latest Build

<!-- LATEST_BUILD_START -->
| | |
| :--- | :--- |
| **Mesa version** | 26.3.0 |
| **Vulkan version** | Vulkan 1.4.363 |
| **Commit** | [`d2c670a`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/d2c670a02f540024806bd68e07fd442bb43c2bc8) |
| **Commit date** | 2026-10-06 |
| **Commit title** | intel/dev: Add assert to ensure stage is not MESA_SHADER_NONE in intel_use_jay_for_stage |
| **Build date** | 20261006 |
| **Downloads** | X11 / AdrenoTools: 4 ZIPs · Bannerlator Wayland: 4 ZIPs · Linux runtime: 4 ZIPs |
| **Release** | [v26.3.0-20261006-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20261006-r6) |
<!-- LATEST_BUILD_END -->

---

## Recent Builds (Last 24 Hours)

<!-- RECENT_BUILDS_START -->
| Tag | Date | Commit | Description | Vulkan |
| :--- | :--- | :--- | :--- | :--- |
| [v26.3.0-20261006-r6](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20261006-r6) | 2026-10-06 | [`d2c670a`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/d2c670a02f540024806bd68e07fd442bb43c2bc8) | intel/dev: Add assert to ensure stage is not MESA_SHADER_NONE in intel_use_jay_for_stage | Vulkan 1.4.363 |
| [v26.3.0-20261006-r5](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20261006-r5) | 2026-10-06 | [`c2188da`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/c2188da5409b8dcf574480365202f25562856a8d) | pan/nir: Rework b2i/b2f lowering | Vulkan 1.4.363 |
| [v26.3.0-20261006-r4](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20261006-r4) | 2026-10-06 | [`2c5d7f4`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/2c5d7f4362225748a5de78e4469b22888ddd75bb) | radv: force exact GLSLstd450Fma for No Man Sky | Vulkan 1.4.363 |
| [v26.3.0-20261006-r3](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20261006-r3) | 2026-10-06 | [`21500c6`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/21500c65d69387f927c8d0a0b737d6edaead1535) | crnm: group argument definitions | Vulkan 1.4.363 |
| [v26.3.0-20261006-r2](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20261006-r2) | 2026-10-06 | [`755de2b`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/755de2b7768f702d7e867656cc15359e4f8b26f9) | kraid: Set lower_hadd64 | Vulkan 1.4.363 |
| [v26.3.0-20261006](https://github.com/The412Banner/Banners-Turnip/releases/tag/v26.3.0-20261006) | 2026-10-06 | [`7e33240`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/7e33240734c26168ef36b39754d2fba81931459f) | kraid: Properly handle OpCopy of 64-bit FAU pre-v12 | Vulkan 1.4.363 |
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

5. **Update cosmetic repo references** *(optional)* — A few strings in the workflows reference the original repo: patch links in release note bodies and `"author"` in `meta.json`. Search for `The412Banner` in `.github/` and in `build_turnip*.sh`, and update to your own username/repo if desired. These don't affect build functionality.

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

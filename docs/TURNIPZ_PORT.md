# TurnipZ 0.3.0 port for Banners-AIO (lab branch `feat/aio-tz`)

[TurnipZ](https://github.com/AlexSanz0902/turnip-sd865-z) by **AlexSanz0902** is a Turnip fork for the
Adreno 650 (Snapdragon 865/870) aimed at Switch emulation. It ships binaries only. This port rebuilds
what TurnipZ 0.3.0 does from its driver binary and adds it to Banners-AIO, each part behind a switch,
so other GPUs keep the AIO driver they have today.

Status: lab build, CI-green. Not tested on an Adreno 650. Nothing here is merged or released.

## How it was found

1. DriverLab decompiled TurnipZ 0.3.0 (7,313 functions).
2. A clean Turnip was built the way TurnipZ was built (Mesa `6e4a77089e1`, NDK r27c, API 30, plus
   TurnipZ's one new NIR intrinsic), lab branch `lab/tz-ref`, CI runs 42316303076 and 42318506117.
3. Every TurnipZ function was matched to the clean build (unwind tables for function bounds, normalised
   instruction hashes, call graph and code order): 6,946 identical, 246 changed, 86 new.
4. TurnipZ keeps its own settings in one fixed block in the binary. Changes that its defaults switch
   off were left out; the rest were decoded and rewritten for current Mesa.

Vauzi-17's `710` repo has his own "Turnip-Z port" scripts (mutable images, texture, BGRA). They were
used only as a map of what to look for; none of that code is used here.

## What is ported

### Mutable images and colour fix (TurnipZ's Eden/Switch speed change)

| Part | What it does |
| :--- | :--- |
| Mutable images (level 4) | Images created with the mutable-format flag stay tiled instead of falling back to linear. They keep UBWC only for a fixed list of formats (32/16/8-bit UINT/SINT, RG16/RGBA16/RG8/RGBA8 UNORM, BGRA8 UNORM, the RG8/RGBA8/BGRA8 SRGB formats, 8-bit single channel; SNORM only where the GPU allows it). |
| Swapped views | A view that differs from the stored image only by red/blue order samples through a swizzle that swaps them back. |
| Render targets | Fragment shaders get a per-draw mask (new `load_rt_swap_mask_ir3` driver parameter) and swap red/blue on those outputs. |
| Clears | Clear colours of those views are swapped (render pass, dynamic rendering, `vkCmdClearAttachments`). |
| Learning cache | Images seen with any other swapped view (or written as storage through a swapped view) are remembered by their create parameters and size, and fall back to linear the next time. |

TurnipZ 0.3.0 runs this only on A6xx (its A7xx/A8xx code paths keep upstream behaviour).

### Adreno 650 only

| Part | What it does |
| :--- | :--- |
| Sysmem by default | Autotune prefers sysmem rendering when `TU_AUTOTUNE_ALGO` is not set. |
| Fewer waits | Barriers between GPU stages skip the wait-for-idle on A6xx; "all graphics/commands" barriers no longer make the command processor wait unless it reads the data itself (indirect draws, conditional rendering, FDM). |
| Textures | Anisotropic filtering at most 4x, LOD bias +0.45, nearest mip level. Faster, slightly blurrier at a distance. |
| GPU context flags | KGSL contexts are created with `NO_SNAPSHOT` and `FAULT_INFO` (plain flags if the kernel refuses). |
| GPU-hang recovery | A context lost to a GPU fault is replaced; waits on it count as done; a submission refused because its context is gone is dropped instead of ending the app. |
| Shader cache | If the app does not set the Mesa cache variables, the cache goes to `/data/data/<package>/cache/mesa_shader_cache` (256 MB). |
| Memory | Reports at most 3584 MiB of GPU memory. |
| Compression metadata | UBWC metadata of a newly bound image is cleared. |

One deliberate difference: after a context is replaced, the queue's last timestamp is reset, so no
later wait pairs an old timestamp with the new context (TurnipZ does this on one of its two paths).

## Switches

| Variable | Values | Default |
| :--- | :--- | :--- |
| `TU_TZ_MUTABLE` | 0 (upstream) - 4 (TurnipZ 0.3.0) | 4 on A6xx, 0 elsewhere |
| `TU_TZ_BGRA` | 0 (upstream) or 3 (TurnipZ 0.3.0) | 3 on A6xx, 0 elsewhere |
| `TU_TZ_A650` | 0 or 1 | 1 on the Adreno 650 |
| `TU_TZ_SAFE` | 0 or 1 | 0 (not in TurnipZ: UBWC only for view formats with the image's channel layout, MSAA images with swapped views fall back) |

Turning `TU_TZ_MUTABLE`/`TU_TZ_BGRA` on for A7xx or A8xx goes beyond what TurnipZ does. The mutable
logic never applies where `ubwc_all_formats_compatible` is set (A7xx gen3, e.g. the Adreno 750): there
Mesa already keeps such images tiled and a second swap would be wrong.

CTS `dEQP-VK.image.mutable.*` (10,646 tests) on an Adreno 722 with TurnipZ's levels forced on: 600 Fail
(r4: 0). About 540 are views with a different channel layout (RGBA8 seen as R32 or R16G16) while UBWC
stays on; 60 are MSAA resolves through red/blue-swapped views. The A6xx path is the same code, so
TurnipZ 0.3.0 most likely shows these on the Adreno 650 too.

## Files

- `patches/tz/tz_port.patch`, applied by `patches/tz/apply_tz.py` after the AIO recipe (fails the
  build if it does not apply exactly).
- `.github/workflows/lab_aio_tz.yml`: Android AIO zip only, Mesa pinned to the r4 release commit.

## Credits

TurnipZ: AlexSanz0902. Vauzi-17 for showing which TurnipZ parts matter for Eden.

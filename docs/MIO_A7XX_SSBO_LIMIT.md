# MIO: Memories in Orbit on Adreno 7xx: level geometry missing (128 MiB storage-buffer limit)

**Status:** fixed in every driver built from `A8xx` 22ed1e9e (2026-11-04) on: `apply_common.sh` adds a
per-game entry for `mio.exe` to Mesa's `00-turnip-defaults.conf`. Not in Mesa upstream yet.
**Found:** 2026-11-03 on an AYANEO Pocket FIT (Snapdragon 8 Gen 3, Adreno 750) and a Pocket FIT Elite
(Snapdragon 8 Elite, Adreno 830), Bannerlator 3.1.8, Wayland display backend, VKD3D-Proton 3.1.

## For users of other drivers

Add this environment variable to the game (or container):

```
tu_enable_ssbo_emulation=true
```

It needs a Turnip built from Mesa after 2026-06-10 (when the option was added). It only does
something on Adreno 7xx; Adreno 8xx does not need it, and it does not help Adreno 6xx or Qualcomm's
own driver.

## Summary

MIO is a DirectX 12 game on its own engine. On Adreno 8xx it renders fully; on Adreno 7xx most of the
level is missing: the floor and platforms are not drawn, and large areas show as flat slabs of fog
colour. The same happens with the Switch version in Eden on the same chips.

MIO keeps the whole world's geometry in one large buffer and reads it through storage-buffer views
larger than 128 MiB. Turnip limits a storage buffer (SSBO) range to 128 MiB on A7xx, so everything
past that offset reads back as zero. A8xx allows 2 GiB, which is why only 8 Elite devices worked.

## Evidence

MIO's own log (`AppData/Local/MIO/Logs/<date>.txt`, build `pc-ship/patch2-rc2 … r21665`) on the
Adreno 750:

```
best adapter found: Wrapper(Adreno (TM) 750)
shader model support: 6.6
[assets] initializing global mesh buffers: 650 MB
static view 1: Bindable_buffer { bind_type = Bind_type(9), stride = 4, count = 134217728, offset = 0 }
static view 2: Bindable_buffer { bind_type = Bind_type(9), stride = 4, count = 36175872, offset = 536870912 }
```

View 1 is 134217728 x 4 B = 512 MiB, view 2 is 36175872 x 4 B = 138 MiB. Both are larger than A7xx's
limit.

Mesa source:

- `src/freedreno/common/freedreno_devices.py`: A7xx `max_storage_buffer_range_bytes = 1 << 27`
  (128 MiB); `a8xx_base` sets `(1 << 31) - 1`.
- `tu_enable_ssbo_emulation` (Mesa 9b322347, Job Noorman, 2026-06-10) and
  `tu_enable_texel_buffer_emulation` (Mesa dc1bb7bb, Danylo Piliaiev, 2026-06-10): driconf options,
  default off, A7xx only (`tu_device.cc` `tu_physical_device_compiler_options_init`). Mesa turns them
  on per game in `00-turnip-defaults.conf`, e.g. DOOM Eternal ("All enemies are invisible without
  tu_enable_ssbo_emulation") and Ratchet & Clank: Rift Apart. MIO was not on that list.
- Mesa reads any driconf option from an environment variable of the same name
  (`src/util/xmlconfig.c`), which is how the option was tested before it was built in.
- VKD3D-Proton passes the exe name as the Vulkan application name (`libs/vkd3d/device.c`,
  `vkd3d_get_program_name`), so `application_name_match` can match `mio.exe`.

## Tests (Adreno 750, same save, Turnip v27.0.0-20261029-r2 unless noted)

| Run | Setting | Result |
| :--- | :--- | :--- |
| A | `tu_enable_ssbo_emulation=true` + `tu_enable_texel_buffer_emulation=true` | full scene, 120 fps |
| B | none | broken: no floor, flat slabs |
| C | `tu_enable_ssbo_emulation=true` only | full scene |
| D | `tu_enable_texel_buffer_emulation=true` only | broken |
| E | driver built with this repo's entry (dry run 41744685840, Mesa 98a55f4), no setting | full scene; the game's environment had no `tu_enable_ssbo_emulation` |
| F | same driver + `tu_enable_ssbo_emulation=false` | broken, so the entry is what fixes it |

Reference: the same save on the Adreno 830 shows the same scene as runs A, C and E.

## The change in this repo

`patches/common/apply_common.sh` (commit 22ed1e9e) runs in every leg (Android, Wayland, Linux; all
variants). It appends before `</device>` in `src/freedreno/vulkan/00-turnip-defaults.conf`:

```xml
<application name="MIO: Memories in Orbit" application_name_match="^mio\.exe$">
    <option name="tu_enable_ssbo_emulation" value="true" />
</application>
```

and fails the build if the entry is not in the tree afterwards. It is skipped when the same entry is
already there. Mesa's static driconf generator stores the pattern as `^mio.exe$` (the backslash is
dropped); it still matches `mio.exe`.

Bannerlator sets the same variable for `mio.exe` on its own (`core/TurnipGameOptions.kt`, Bannerlator
main 47e31014), so it also works there with drivers that do not carry this entry.

## Related

- Switch-port analysis of MIO's renderer (GPU-driven visibility buffer, indirect-count multi-draws):
  [seedds/nxnative#941](https://github.com/seedds/nxnative/issues/941).
- Upstream Mesa entry: not sent yet.

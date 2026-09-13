# whitebelyash/freedreno_turnip-CI, release tu_v31 ("Mainline Turnip v31")

- Repository: https://github.com/whitebelyash/freedreno_turnip-CI
- Release: `tu_v31`, published 2026-08-07T12:06:28Z, assets `mainline-turnip-V31.zip` and
  `mainline-turnip-sync-V31.zip`. Notes: "Built from whitebelyash/mesa-unified (turnip/gen8
  branch)", 8xx 840/830/829/825/812/810, 7xx incl. 710/720/722 (sysmem only), `TU_DEBUG=deck_emu`,
  `TU_DEBUG=sysmem` advised on A830.
- Tag commit: `258fc21943dc3cab448bc53d1566a5f699283cf4`. Files here are verbatim copies from that
  commit: `turnip_builder.sh`, `turnip_builder_upstream.sh`, `README.md`, the two workflows,
  `patches/39751.diff`.

What the job applies: `turnip_builder.yml` runs `turnip_builder.sh`, which clones
`whitebelyash/mesa-unified`, checks out `origin/turnip/gen8`, writes
`src/freedreno/vulkan/tu_version.h` = `#define TUGEN8_DRV_VERSION "v31"` (the fork appends it to
the device name), and builds twice: `mainline-turnip` as is, and `mainline-turnip-sync` with every
file in `patches/` applied by `git apply` (only `39751.diff`: Mesa MR 39751, binary/timeline sync
rework in `tu_knl_kgsl.cc`, `tu_queue.h`, `tu_device.h`, `tu_common.h`, `vk_semaphore.c`).

Mesa pin: the recipe IS the fork branch. Both released binaries embed
`Mesa 26.3.0-devel (git-9c475fc367)`; `9c475fc367a7283a7eee58501fb48149780f2c1e` is the
`turnip/gen8` head at release time (2026-08-07T12:00:44Z, "freedreno/common: change a810/a812
depth ccu fraction"): upstream main rebased at 2026-08-07 plus ~28 commits (whitebelyash tu8
hacks: DECK_EMU, gralloc UBWC, disable_gmem, A825, VK1.3 w/o multiview, a8xx configs, A810 cuts,
nocb, 710/720 support, adrenotools driver versioning, Adreno 812, shared mem 64K, Connor Abbott's
ir3 speculatability series). The Wayland build fetches that commit from the fork and mirrors the
primary asset (`mainline-turnip-V31`: no `39751.diff`); the `-sync` variant is not built.
Markers unique to this driver: `Adreno (TM) 812` in the device table and ` (v31)` on the device
name.

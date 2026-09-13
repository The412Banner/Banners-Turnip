# StevenMXZ/Adreno-Tools-Drivers, release v36 ("Turnip Gen8 V36")

- Repository: https://github.com/StevenMXZ/Adreno-Tools-Drivers
- Release: `v36`, published 2026-09-08T11:07:59Z, asset `Turnip_Gen8_V36.zip`. Notes: "build from:
  whitebelyash/mesa-unified turnip/gen8 + Mesa Upstream", "for A8xx GPUs (a840, a830, a829, a825,
  810)", "Vulkan Version 1.4.359". The zip's `meta.json`: "from mesa main".
- Tag commit: `50cbd613e7f6f10e6bc36cfde51e9c76c23a441d` (branch `A8xx`). Files here are verbatim
  copies from that commit: `build_turnip.sh`, `.github/workflows/turnip_build.yml`, `tu_gen8.patch`,
  `tu8_kgsl_26.patch`, `39751.patch`, `patches/*.patch`.

What the job applies: `turnip_build.yml` runs `build_turnip.sh`, which clones
`whitebelyash/mesa-tu8`, checks out its `gen8` branch and applies only `sed`s: strip ` (%s)` from
`tu_device.cc`, insert `has_early_preamble = False` right after `a7xx_gen1 = GPUProps(` in
`freedreno_devices.py`, and the NDK r29 fixes to Android-only files; it writes an empty
`TUGEN8_DRV_VERSION`. None of the `.patch` files in the repo are used by the job at this tag.

Mesa pin: the job pins nothing (fork branch head at run time), and the fork's `gen8` head is
`d185f62a24` (2026-04-25, Mesa 26.1-devel with the whitebelyash hacks, including "don't append git
hash") - that cannot be what V36 shipped: the released `libvulkan_freedreno.so` embeds
`Mesa 26.3.0-devel (git-c501e1d16e)` (the git-hash suffix the fork removes is still there), and
`c501e1d16e` is mesa/mesa `main` at 2026-09-08T05:54Z ("r300: respect unnormalized sampler
coordinates"), not present in mesa-tu8. So the shipped V36 is upstream main at that commit, as the
meta.json says. The Wayland build therefore pins `c501e1d16e11c256610cd5922b1afa5660f2f5ea` and
applies the job's `sed`s on top. Upstream at that commit has no ` (%s)` in `tu_device.cc`, so the
effective recipe is upstream + `has_early_preamble = False` on a7xx_gen1 (its A8xx support is
upstream's: 810/829/830/840/X2, no 825). There is no textual marker for that change; the Wayland
build asserts it at source level and that the binary differs from every other driver.

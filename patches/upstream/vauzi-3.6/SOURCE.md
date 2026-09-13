# Vauzi-17/710, release 3.6 (Turnip for Adreno 710 / 720 / 722)

- Repository: https://github.com/Vauzi-17/710
- Release: `3.6`, published 2026-08-29T10:09:03Z, asset `Turnip-710-720-722-v3.6.zip` (uploaded
  2026-08-29T10:07:43Z). Notes: "Synced with the latest Mesa main branch", "Recommended memory
  mode: sysmem".
- Tag commit: `5db89bde562d2bb89d39b016ddf8b25f6d3bf309` (2026-08-01, "freedreno/a7xx: adjust CCU
  count for Adreno 720 and 722"). Files here are verbatim copies from that commit:
  `add_710_720_722.py`, `turnip_builder.sh`, `turnip_builder_upstream.sh`, `README.md`.

Mesa pin: the release notes name no commit. The shipped `libvulkan_freedreno.so` embeds
`Mesa 26.3.0-devel (git-25219437df)`; that commit exists neither on gitlab mesa/mesa nor anywhere
on the `Vauzi-17/mesa-tu8` fork (the `turnip_builder.sh` at the tag clones that fork's
`gen8-clean-26` branch, whose head is from March 2026, so it is not what 3.6 was built with), i.e.
it was a local commit. The files inside the zip are dated 2026-08-27 07:01-07:03 (the builder's
local clock). The pin is therefore the newest mesa/mesa `main` commit before that time read as
UTC: `7631b5254f1a0a4371f5594e630ce2f2b8394e73` (2026-08-27T05:57:30Z, "intel/ci: Update relevant
tests."). If the builder's clock was UTC+7 the newest commit would instead have been
`d45779b345cc183527bc0db91865977b088cb4b4` (2026-08-26T19:38:11Z); nothing in Turnip changed between
the two.

The recipe: `add_710_720_722.py`, run from the Mesa root. It removes any existing FD710/FD720/FD722
`add_gpus` blocks (upstream carries an A722 entry) and inserts its own three, with per-GPU magic
registers and `num_ccu` 1 / 2 / 2, before the FD725 block. This repo's own `patches/a710-720.py`
is the same script with `num_ccu = 3` for all three; 3.6 is the upstream author's current values.
Their README recommends `TU_DEBUG=sysmem` on these GPUs; the Wayland build does not bake that in.

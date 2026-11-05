# Fixes taken from DroidDeck's Turnip (DD-Turnip)

Copied unchanged from [Droid-Deck/Drivers](https://github.com/Droid-Deck/Drivers) at
`c437d891164c5e31a65219a5451005875fab74ac` (2026-11-02), same folder layout, so the scripts
find `mesa_edit.py` and `aimapper/` the same way. Used with the authors' permission.
`patches/one/one_fixes.py` applies them; that script also says which GPUs each one reaches.

| File | What it fixes | GPUs | Author |
|---|---|---|---|
| tu/0001-tu-flush-before-suspended-render-pass-chain.patch | barrier flushes lost at a suspended render pass chain (UE5 Nanite / virtual shadow maps) | all | K11MCH1 |
| nir/0001-nir-lower-explicit-io-keep-32bit-offset-wrap.patch | 32-bit SSBO offset wrap (vkd3d-proton UE5 Nanite) | all | K11MCH1 |
| scripts/process_heap_usage.py | memory budget counts the whole process (D3D12 / DXGI) | all | Charles DuBose |
| scripts/add_aimapper_gralloc.py + aimapper/u_gralloc_aimapper.c | IMapper5 stable-C gralloc backend | all (Android) | Leb-Sun |
| scripts/add_ubwc_swapchain_usage.py | UBWC-compressed swapchain buffers | all (Android) | Leb-Sun |
| lrz/0001-tu-a8xx-lrz-reset-cntl-after-flush.patch | LRZ controls reset after the end-of-pass flush (hang) | A8xx | Gustash |
| fdl/0001-fdl-a8xx-buffer-num-elements.patch | buffer descriptors of 1 GiB and more keep their size | A8xx | airidosas252 |
| scripts/a8xx_resolve_cr_cntl.py | RB_RESOLVE_CR_CNTL = 1 as the Qualcomm driver | A8xx | adapted from Vauzi-17/710 |
| scripts/a8xx_sp_hysteresis.py | VS / PS hysteresis as the Qualcomm driver | A8xx | adapted from Vauzi-17/710 |
| scripts/a8xx_lrz_color_mask.py | GRAS_LRZ_COLOR_COMP_MASK from the MRT write masks | A8xx | adapted from Vauzi-17/710 |
| scripts/apply_a8xx_cat4_rpt.py | no category-4 repeat (grayscale DXVK / Unity 2D) | A845, A850 | misakayuuki |
| scripts/apply_a7xx_gen1_quirks.py | early preamble and scalar predicates off | A710, A720, A722, A725, A730 | DroidDeck |

Droid-Deck/Drivers is GPL-3.0 as a repository; `aimapper/u_gralloc_aimapper.c` carries
`SPDX-License-Identifier: MIT`.

# Wayland zero-copy fps ceiling — progress log

Branch `fix/wayland-zero-copy-ceiling` (off A8xx 10497a9). Test workflow `zcfix_wayland_test.yml`
exists only here, push-triggered, one regular Wayland zip as an artifact, publishes nothing.

## Symptom (device, 2026-09-28, Pocket FIT / Adreno 750, 120 Hz panel)
Zero-copy ON with current-Mesa Wayland Turnip: AIO uncapped mailbox tops out at ~240-320 fps on
every API (D3D11 cube 274 vs 3423 with zero-copy off), GPU ~27 % busy. The Pipetto wrapper port of
the same WSI patch has no ceiling (D3D11 3632).

## Root cause
- Compositor (read-only, bannerlators feat/linux-gamescope-runtime):
  `ahb_swapchain.c` handle_released() imports SurfaceFlinger's previous-release fence into the
  dma-buf (DMA_BUF_IOCTL_IMPORT_SYNC_FILE, READ) and then sends wl_buffer.release. The release fence
  signals only when the display stops scanning the buffer out (~one refresh later). Log of a capped
  run: "release 6.76/17.66 ms (2393, 1200 held)" — half of all frames were on the layer.
- Mesa main `wsi_wl_swapchain_acquire_next_image_implicit()` returns the LOWEST-numbered non-busy
  image, and `wsi_common_acquire_next_image2()` -> `wsi_signal_semaphore_for_image()` ->
  `wsi_create_sync_for_dma_buf_wait()` exports every fence of that dma-buf into the acquire
  semaphore. So a buffer freshly back from the layer is handed out at once and the game's GPU queue
  waits on the display, once per refresh, while other free images sit idle -> throughput ~2x refresh.
- Why the wrapper has no ceiling: its vk_physical_device never sets `supported_sync_types`
  (wrapper_physical_device.c), so `wsi_signal_semaphore_for_image()` returns early and the acquire
  never waits on the dma-buf at all.

## Fix
`patches/wayland/banner_ahb_wsi.py`: on a gralloc (banner) chain the implicit acquire polls each free
image's dma-buf (poll timeout 0: POLLOUT = all fences done, POLLIN = writers done) and picks
idle > only-our-own-render-pending > display-held. The semaphore still carries every fence, so no
buffer is ever rendered into while the display scans it (tear-free kept); only the choice changes.

## Runs / results
- CI run 36505095265 started for a21b38c (headSha verified), Mesa 9f1e484.
- CI 36505095265 SUCCESS (headSha a21b38c verified). Zip Turnip-Wayland-ZCFIX-TEST-a21b38c.zip
  sha256 2fb7177c1a63a0f0c8cd7708c327f12024c0aad0a38973f97237e9e02fc1c673, staged in /sdcard/Download/Wayland/,
  installed on device as imported:Turnip-ZCFIX-TEST-a21b38c.
- Device baseline (harness copy cube-zc.sh that waits for the NEW session log), combined 9f1e484, zc on:
  297 / 261 / 312 / 270 / 326 / 252 / 254 / 239; log: ~2500-3000 releases per 10 s, ~1200 of them held (= 120 Hz).
- Device run zcfix-zc (a21b38c, zc on): 464 / 268 / 404 / 483 / 359 / 243 / 243 / 239.
  D3D12 (404 vs zc-off 397) and D3D10 (359 vs 356) now match the copy path; Vulkan 297 -> 464 (zc-off 535);
  D3D11 cube 270 -> 483 but zc-off does 3423. Still "presenting ... without a copy".
  Note: OpenGL / D3D9 / D3D8 / DDraw are ~240 = 2x120 Hz with EVERY driver and with zero-copy OFF too
  (wrapper run a1 log: 2362-2424 GPU frames / 10 s in those slots) -> not part of the zero-copy ceiling.
- Remaining D3D11 limit: images. 5 images; the layer holds up to 3 (displayed, pending in SurfaceFlinger,
  released-but-display-fenced), the surface's current buffer 1, the one being rendered 1 -> after each
  compositor tick the game waits for the display. The wrapper gets 3600+ only because it ignores the
  display fence (renders into a buffer the display may still scan out). Correct fix: more images for
  gralloc chains in MAILBOX/IMMEDIATE (default +2, BANNER_WSI_AHB_EXTRA_IMAGES=0..4 to tune on device).
- Pushed image-count change f7ac07e; CI 36505744731 SUCCESS (headSha verified). Zip Turnip-Wayland-ZCFIX-TEST-f7ac07e.zip sha256 13db8fe6bb39119b4cf42dd705ed435ad288e756e94b18055afe44a4ee4aec44, installed as imported:Turnip-ZCFIX-TEST-f7ac07e.
- Device run zcfix-nozc (a21b38c, zc OFF, copy path, banner code inactive): 501 / 240 / 381 / 3377 / 358 / 241 / 241 / 228 (= bundled-nozc, no regression).

# Adreno 830: subgroup math in compute shaders gave wrong results (double threadsize)

**Status:** fixed in the A8xx and Banners-AIO drivers from `A8xx` 23292620 (2026-11-05) on, first release
v27.0.0-20261105-r4: [`patches/a8xx_no_double_threadsize.py`](../patches/a8xx_no_double_threadsize.py).
Not reported to the gen8 stack's authors yet.
**Found:** 2026-11-05 on an AYANEO Pocket FIT Elite (Snapdragon 8 Elite, Adreno 830), Android 16.

## Summary

On the Adreno 830, both of our Elite drivers (A8xx and Banners-AIO) gave wrong results for subgroup operations
in compute shaders: `subgroupAdd` and the other arithmetic, shuffle and rotate, clustered operations, ballot
broadcast, and the subgroup uniform control flow tests. DirectX 12 games use these "wave" operations through
VKD3D-Proton. Mesa's own driver and the Qualcomm driver give the right results.

The cause is one setting in one commit of the gen8 stack ([`a8xx_gen8.patch`](../patches/a8xx_gen8.patch)):
"freedreno/common: update a8xx family configs" (DVD, 2026-04-15) changes `a8xx_base`
`supports_double_threadsize` from `False` (Mesa's value) to `True`. With Mesa's value the tests pass and speed is
unchanged, so both Elite drivers now put it back to `False` after the gen8 stack.

## How it was found

1. **Overnight Vulkan CTS** (3.2 million tests per device, DriverLab's dEQP build, 2026-11-04/05): about 13,900
   tests failed on the Adreno 830 with both Elite drivers. About 4,800 of them pass on the Qualcomm driver; the
   biggest groups were `dEQP-VK.subgroups.arithmetic.compute` (1,420), the two
   `reconvergence.subgroup_uniform_control_flow_*.compute` groups (1,710), `subgroups.shuffle.compute` (616),
   `subgroups.clustered.compute` and `subgroups.ballot_broadcast.compute`.
2. **A 660-test sample** of those six groups (110 each, all failing on both Elite drivers, all passing on Qualcomm)
   was run on lab builds from one Mesa commit (`2008a72ead`), one test process at a time:

| Driver (Adreno 830) | Pass | Fail | Not supported |
| :--- | ---: | ---: | ---: |
| A8xx (gen8 stack + Max's WinNative 0001-0005) | 0 | 660 | 0 |
| A8xx without WinNative 0002 (half-wave subgroups) | 0 | 660 | 0 |
| A8xx without any WinNative patch | 0 | 660 | 0 |
| **Standard** (Mesa `main`, no gen8 stack) | **629** | 20 | 11 |

3. **Bisect of the gen8 stack:** the A8xx driver built 14 times, each time with one of the 14 gen8 commits left
   out (commit 3, `disable_gmem`, does not build without it). Every build failed all 660 tests except the one
   without commit 6, "update a8xx family configs": **629 pass, 20 fail, 11 not supported**, the same as Mesa.
4. **The single setting:** commit 6 changes many A8xx values (GMEM / CCU sizes, tile alignment, quirks). Putting
   back only `a8xx_base supports_double_threadsize = False` gives the same result:

| Driver (Adreno 830) | Pass | Fail | Not supported |
| :--- | ---: | ---: | ---: |
| A8xx, `supports_double_threadsize = False` | 629 | 20 | 11 |
| Banners-AIO, `supports_double_threadsize = False` | 629 | 20 | 11 |

The 20 tests that still fail also fail with Mesa's own driver.

## Speed with the fix

GPU at 1100 MHz in every run, no GPU page faults.

- **DriverLab speed test** (10 scenes, 3 rounds each, before → after): A8xx within −0.1 % … +1.0 % on every scene
  (card 5108 → 5106 fps, compute 93.4 → 93.4 fps); Banners-AIO within −0.2 % … +1.5 %.
- **AIO Graphics Test in Bannerlator** (Banners-AIO, 8 APIs, before → after, average fps): Vulkan 3690 → 3719,
  OpenGL 6847 → 6777, D3D12 8963 → 8948, D3D11 6186 → 6230, D3D10 6224 → 6279, D3D9 7111 → 7140, D3D8 7122 → 7136,
  D3D7 9038 → 9097. All within ±1 %, pictures correct.

## The fix

[`patches/a8xx_no_double_threadsize.py`](../patches/a8xx_no_double_threadsize.py) runs after the gen8 stack in
the A8xx and Banners-AIO recipes (Android, Wayland and Linux zips). It changes only the `a8xx_base` block of
`freedreno_devices.py` and stops the build if that block does not have exactly one
`supports_double_threadsize = True,`, so a future change in the gen8 stack is noticed.

## Also found the same day: A8xx hysteresis registers (Banners-AIO)

Banners-AIO's `dd/scripts/a8xx_sp_hysteresis.py` (Droid-Deck/Drivers `b6cbfb43`, values from Vauzi-17/710) sets
`SP_PS_HYSTERESIS` / `SP_VS_HYSTERESIS` to the Qualcomm driver's values. Leaving each Banners-AIO fix out in turn
showed it made the DriverLab "card" scene 6 % slower (4744 → 5028 fps without it), with no difference in AIO
(8 APIs, ±1 %) and no known bug it fixes; Mesa writes these registers only in its ray-tracing workaround. It is
no longer applied since `A8xx` 4ccd4e92.

## Credits

- The gen8 stack: whitebelyash ([mesa-unified](https://github.com/whitebelyash/mesa-unified) `turnip/gen8`),
  with commits by DVD and Karmjit Mahil. The setting comes from DVD's "update a8xx family configs".
- Max's WinNative series (MaxsTechReview, [WinNative-Emu/Drivers](https://github.com/WinNative-Emu/Drivers)) was
  tested and is not involved.
- Test harness: DriverLab (dEQP-VK + speed scenes), run as root on the device.

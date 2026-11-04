# Wayland builds stopped after Mesa 159aec41 (vk_android_native_buffer.h guard)

**Status:** fixed on `A8xx` 80fd599c (2026-11-04).
**Affected releases:** v27.0.0-20261101-r5 through v27.0.0-20261103-r4 shipped without Wayland ZIPs
(the last release with them was v27.0.0-20261101-r4). The X11 and Linux ZIPs were not affected.

## What happened

Every Wayland leg stopped right after fetching Mesa with:

```
[wayland regular] vk_android_native_buffer.h: Android guard not found
```

`build_turnip_wayland.sh` builds Turnip Linux-style on bionic, so it turns off Mesa's Android code.
One step rewrote this line in `include/vulkan/vk_android_native_buffer.h`:

```c
#if defined(__ANDROID__) || defined(ANDROID)
```

because bionic defines `__ANDROID__` and the header would otherwise include `cutils/native_handle.h`.
Mesa 159aec41ca (Yiwei Zhang, 2026-11-01, "vulkan: native handle is tied to
VK_USE_PLATFORM_ANDROID_KHR") changed that guard to:

```c
#ifdef VK_USE_PLATFORM_ANDROID_KHR
```

so the rewrite found nothing and the check after it stopped the build.

## The fix

`src/vulkan/meson.build` defines `VK_USE_PLATFORM_ANDROID_KHR` only when `with_platform_android` is
set, and the Wayland build uses `-Dplatforms=wayland`, so with the new guard the header already takes
the non-Android branch and needs no edit. `build_turnip_wayland.sh` now:

- rewrites the old `__ANDROID__` guard as before (older Mesa);
- accepts the new guard after checking that `src/vulkan/meson.build` still ties the macro to
  `with_platform_android`;
- stops the build on any other form.

Tested on the headers of Mesa 8f6e054ab4 (old form), 98a55f454d (new form) and an unknown form (stops).
Dry run 41747722949: all 13 legs green, including the four Wayland legs. Device check on an Adreno
830 (Pocket FIT Elite): the A8xx Wayland ZIP, imported in Bannerlator as a Wayland game driver, loaded
in the game process and rendered MIO: Memories in Orbit fully.

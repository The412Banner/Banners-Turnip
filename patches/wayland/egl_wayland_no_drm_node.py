#!/usr/bin/env python3
"""EGL on Wayland without a usable DRM render node: zink + kopper on the Vulkan device, not swrast.

OpenGL on the Bannerlator compositor is Zink (MESA_LOADER_DRIVER_OVERRIDE=zink, set by
winewayland) presenting through kopper, i.e. a real VK_KHR_wayland_surface swapchain on the Turnip
next to it. Neither rendering nor presenting needs a DRM device. EGL's Wayland DRM initialiser
still insists on one: it takes a render node out of the compositor's dma-buf feedback
(main_device) and hands it to dri2_setup_device(disp, false), which fails the whole display when
there is none.

Retail Android phones commonly give apps no DRM node at all (the compositor then advertises
main_device 0:0 and loader_get_render_node() resolves nothing), or one that libdrm cannot describe
because an enforcing SELinux policy hides its sysfs entry. Stock Mesa then fails the display,
eglInitialize retries with ForceSoftware, and the software path in this build has no rasteriser
(gallium = zink only, -Dllvm=disabled): the game runs with sound behind a black window
(Adreno 830/840 reports, 2026-09-14). The same display on a device whose node works (the Pocket
FIT's /dev/dri/renderD128) renders fine.

What this changes, in dri2_initialize_wayland_drm() only: when the display is going to be kopper
and there is no render node it can use - none from the feedback, or one that
loader_is_device_render_capable() / _eglFindDevice() cannot place, which is exactly when stock
dri2_setup_device(disp, false) would fail - drop the fd and build the kopper screen without one.
kopper_init_screen() already takes fd -1 as "no DRM" (pipe_loader_vk_probe_dri ->
zink_create_screen -> choose_pdev() without a DRM match -> the only Vulkan device), which is how
X11's LIBGL_KOPPER_DRI2 path runs Zink. Such a display has no EGLDevice to name, so it is left
without one, as Android's pure-swrast path leaves it (eglQueryDisplayAttribEXT(EGL_DEVICE_EXT)
gives EGL_NO_DEVICE_EXT). Deliberately NOT the software EGLDevice X11 uses there: that one carries
EGL_MESA_device_software, and Wine's win32u then reports the display unaccelerated although every
frame is drawn by the GPU. A node that works keeps the stock path untouched, and nothing changes
for a display that is not kopper.

Plus one warning line where each path is decided, so a report's wine_debug.log says which one ran:
  "wayland-egl: ... running zink on the Vulkan device without one"   (this path)
  "wayland-egl: OpenGL is on Mesa's wl_shm software path ... black"  (the software fallback)
The working DRM path prints nothing new.

Written against exact source text rather than diff context so it survives Mesa line drift; every
anchor and every premise the reasoning above depends on is asserted, so a Mesa ref that changed
any of them fails the build instead of shipping a driver whose GL path nobody has read.

Usage: egl_wayland_no_drm_node.py <Mesa checkout>
"""
import os
import sys

path = os.path.join(sys.argv[1], 'src/egl/drivers/dri2/platform_wayland.c')
s = open(path).read()


def need(text, why):
    if s.count(text) != 1:
        sys.exit("egl: platform_wayland.c: expected exactly one %r (%s), found %d - establish which "
                 "path a Zink display takes at this Mesa ref before shipping it"
                 % (text[:80], why, s.count(text)))


# Premises. The stock two-way dispatcher: a Zink display that is not forced into software goes to
# the DRM initialiser, and only that one reads dma-buf feedback (bound at MIN2(version, 4), so our
# version 4 global is seen).
need("   if (disp->Options.ForceSoftware)\n"
     "      return dri2_initialize_wayland_swrast(disp);\n"
     "   else\n"
     "      return dri2_initialize_wayland_drm(disp);",
     "the stock dispatcher")
need("zwp_linux_dmabuf_v1_get_default_feedback(", "the DRM path asks for default feedback")
need("MIN2(version, ZWP_LINUX_DMABUF_V1_GET_DEFAULT_FEEDBACK_SINCE_VERSION)",
     "dma-buf bound at version 4 so the feedback is read")
# An unresolvable main_device leaves fd_render_gpu at -1 instead of failing anything itself.
need("   node = loader_get_render_node(dev);\n"
     "   if (!node)\n"
     "      return;\n",
     "main_device without a render node is ignored")

drm_old = ("   dri2_detect_swrast_kopper(disp);\n"
           "\n"
           "   dri2_dpy->loader_extensions = dri2_dpy->kopper ? kopper_loader_extensions\n"
           "                                                  : dri2_loader_extensions;\n"
           "\n"
           "   if (!dri2_create_screen(disp))\n"
           "      goto cleanup;\n"
           "\n"
           "   if (!dri2_setup_device(disp, false)) {\n"
           "      _eglError(EGL_NOT_INITIALIZED, \"DRI2: failed to setup EGLDevice\");\n"
           "      goto cleanup;\n"
           "   }\n")
need(drm_old, "the DRM initialiser's screen + EGLDevice setup")

drm_new = ("   dri2_detect_swrast_kopper(disp);\n"
           "\n"
           "   /* Bannerlator: zink + kopper renders and presents through Vulkan; a DRM render node\n"
           "    * only names the Vulkan device, and there is one. Android phones often give apps no\n"
           "    * node (main_device 0:0) or one libdrm cannot describe, and dri2_setup_device() would\n"
           "    * then fail the display into the software retry, which this build cannot draw. Without\n"
           "    * a usable node, build the kopper screen with fd -1 (pipe_loader_vk_probe_dri ->\n"
           "    * zink_create_screen, as X11's LIBGL_KOPPER_DRI2 path does) and leave the display\n"
           "    * without an EGLDevice, as Android's pure-swrast path does. */\n"
           "   const bool kopper_without_drm =\n"
           "      dri2_dpy->kopper &&\n"
           "      (dri2_dpy->fd_render_gpu < 0 ||\n"
           "       !loader_is_device_render_capable(dri2_dpy->fd_render_gpu) ||\n"
           "       !_eglFindDevice(dri2_dpy->fd_render_gpu, false));\n"
           "   if (kopper_without_drm) {\n"
           "      if (dri2_dpy->fd_render_gpu < 0)\n"
           "         _eglLog(_EGL_WARNING, \"wayland-egl: the compositor names no DRM render node \"\n"
           "                 \"this process can open; running zink on the Vulkan device without one\");\n"
           "      else\n"
           "         _eglLog(_EGL_WARNING, \"wayland-egl: render node %s cannot be described here \"\n"
           "                 \"(libdrm/sysfs); running zink on the Vulkan device without one\",\n"
           "                 dri2_dpy->device_name ? dri2_dpy->device_name : \"(unnamed)\");\n"
           "      if (dri2_dpy->fd_display_gpu >= 0 &&\n"
           "          dri2_dpy->fd_display_gpu != dri2_dpy->fd_render_gpu)\n"
           "         close(dri2_dpy->fd_display_gpu);\n"
           "      if (dri2_dpy->fd_render_gpu >= 0)\n"
           "         close(dri2_dpy->fd_render_gpu);\n"
           "      dri2_dpy->fd_render_gpu = dri2_dpy->fd_display_gpu = -1;\n"
           "      dri2_dpy->is_render_node = false;\n"
           "   }\n"
           "\n"
           "   dri2_dpy->loader_extensions = dri2_dpy->kopper ? kopper_loader_extensions\n"
           "                                                  : dri2_loader_extensions;\n"
           "\n"
           "   if (!dri2_create_screen(disp))\n"
           "      goto cleanup;\n"
           "\n"
           "   if (!kopper_without_drm && !dri2_setup_device(disp, false)) {\n"
           "      _eglError(EGL_NOT_INITIALIZED, \"DRI2: failed to setup EGLDevice\");\n"
           "      goto cleanup;\n"
           "   }\n")

swrast_old = ("   dri2_dpy->driver_name = strdup(disp->Options.Zink ? \"zink\" : \"swrast\");\n"
              "   dri2_detect_swrast_kopper(disp);\n")
need(swrast_old, "the swrast initialiser's driver choice")
swrast_new = (swrast_old +
              "   if (dri2_dpy->swrast)\n"
              "      _eglLog(_EGL_WARNING, \"wayland-egl: OpenGL is on Mesa's wl_shm software path, \"\n"
              "              \"and this build has no CPU rasteriser (zink only, no LLVM): the window \"\n"
              "              \"will stay black\");\n")

s = s.replace(drm_old, drm_new, 1).replace(swrast_old, swrast_new, 1)
assert s.count("kopper_without_drm") == 3 and s.count("wl_shm software path") == 1
open(path, 'w').write(s)
print("egl: Zink on Wayland takes the DRM path; with no usable render node it runs kopper on the "
      "Vulkan device without one (no EGLDevice) instead of failing into swrast")

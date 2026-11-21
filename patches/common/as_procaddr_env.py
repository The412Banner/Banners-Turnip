#!/usr/bin/env python3
"""TEST ONLY (branch test/doom-as-procaddr, 2026-11-21): with BANNER_AS_ALWAYS=1 in the
environment, vkGetDeviceProcAddr also returns VK_KHR_acceleration_structure entry points when
the app did not enable the extension, as long as the device supports it.

Why: DOOM: The Dark Ages turns ray tracing off on Turnip (no VK_KHR_ray_tracing_pipeline), so it
does not enable VK_KHR_acceleration_structure, but its render setup still calls
vkGetAccelerationStructureBuildSizesKHR through a pointer it loaded with vkGetDeviceProcAddr.
The pointer is NULL and the game jumps to address 0. Without the variable nothing changes.
Run from the Mesa source root.
"""
import sys
from pathlib import Path

p = Path("src/vulkan/runtime/vk_device.c")
s = p.read_text()
marker = "BANNER_AS_ALWAYS"
if marker in s:
    print("[as_procaddr] already applied")
    sys.exit(0)

old = """   struct vk_instance *instance = device->physical->instance;
   return vk_device_dispatch_table_get_if_supported(&device->dispatch_table,
                                                    name,
                                                    instance->app_info.api_version,
                                                    &instance->enabled_extensions,
                                                    &device->enabled_extensions);
}"""
new = """   struct vk_instance *instance = device->physical->instance;
   PFN_vkVoidFunction func =
      vk_device_dispatch_table_get_if_supported(&device->dispatch_table,
                                                name,
                                                instance->app_info.api_version,
                                                &instance->enabled_extensions,
                                                &device->enabled_extensions);
   /* Banners-Turnip test: BANNER_AS_ALWAYS=1 hands out VK_KHR_acceleration_structure entry
    * points the app did not enable (DOOM: The Dark Ages builds a TLAS on its no-ray-tracing
    * path). Only when the device supports the extension.
    */
   if (func == NULL &&
       device->physical->supported_extensions.KHR_acceleration_structure &&
       strstr(name, "AccelerationStructure") != NULL &&
       debug_get_bool_option("BANNER_AS_ALWAYS", false))
      func = vk_device_dispatch_table_get(&device->dispatch_table, name);
   return func;
}"""
if s.count(old) != 1:
    sys.exit("[as_procaddr] vk_device_get_proc_addr body not found as expected; check Mesa")
s = s.replace(old, new)
if "#include <string.h>" not in s:
    s = s.replace('#include "vk_device.h"', '#include "vk_device.h"\n\n#include <string.h>', 1)
    if "#include <string.h>" not in s:
        sys.exit("[as_procaddr] could not add #include <string.h>")
p.write_text(s)
if marker not in p.read_text():
    sys.exit("[as_procaddr] patch did not land")
print("[as_procaddr] vk_device_get_proc_addr: BANNER_AS_ALWAYS fallback added")

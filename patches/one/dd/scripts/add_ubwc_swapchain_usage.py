from mesa_edit import replace

replace(
    'src/vulkan/runtime/vk_android.c',
    """   if (ahb_usage_props)
      ahb_usage_props->androidHardwareBufferUsage = ahb_usage;""",
    """   if (ahb_usage_props) {
      uint64_t alloc_usage = ahb_usage;

      if (!(alloc_usage & (AHARDWAREBUFFER_USAGE_CPU_READ_MASK |
                           AHARDWAREBUFFER_USAGE_CPU_WRITE_MASK)))
         alloc_usage |= pdevice->ahb_vendor_usage_compressed;

      ahb_usage_props->androidHardwareBufferUsage = alloc_usage;
   }""",
    'vendor UBWC bit on the AHB usage answer',
)
replace(
    'src/vulkan/runtime/vk_physical_device.h',
    """   const struct vk_pipeline_cache_object_ops *const *pipeline_cache_import_ops;
};""",
    """   const struct vk_pipeline_cache_object_ops *const *pipeline_cache_import_ops;

   uint64_t ahb_vendor_usage_compressed;
};""",
    'vk_physical_device vendor-usage field',
)
replace(
    'src/freedreno/vulkan/tu_device.cc',
    '   device->vk.supported_sync_types = device->sync_types;',
    '   device->vk.supported_sync_types = device->sync_types;\n'
    '   device->vk.ahb_vendor_usage_compressed = 0x10000000ull;',
    'turnip sets the vendor usage bit',
)

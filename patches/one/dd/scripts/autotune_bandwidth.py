from mesa_edit import replace

replace(
    'src/freedreno/vulkan/tu_autotune.cc',
    'gmem_bandwidth = (gmem_bandwidth * 11 + total_draw_call_bandwidth) / 10;',
    'gmem_bandwidth = (gmem_bandwidth * 10 + total_draw_call_bandwidth) / 10;',
    'GMEM bandwidth multiplier 11 -> 10',
)

"""Experiment: GMEM tile layout always stays below the CCU depth+color carve-outs
(tu_pass.cc normally does this only for TU_GMEM_LAYOUT_AVOID_CCU). Affects every GPU."""
p = "src/freedreno/vulkan/tu_pass.cc"
s = open(p).read()
old = """      if (layout == TU_GMEM_LAYOUT_AVOID_CCU) {
         gmem_size = MIN2(gmem_size, phys_dev->config_gmem.color_ccu_offset);
         if (custom_resolve_depth_stencil)
            gmem_size = MIN2(gmem_size, phys_dev->config_gmem.depth_ccu_offset);
      }"""
assert s.count(old) == 1
s = s.replace(old, """      gmem_size = MIN2(gmem_size, phys_dev->config_gmem.color_ccu_offset);
      gmem_size = MIN2(gmem_size, phys_dev->config_gmem.depth_ccu_offset);""")
open(p, "w").write(s)
print("[avoidccu] tiles always below the CCU carve-outs")

"""Experiment: A722 GMEM-mode CCU depth cache fraction = FULL (a7xx_base: EIGHTH, size code 3,
which Mesa notes reads as THREE_QUARTER on some GPUs). Needs own722 first."""
p = "src/freedreno/common/freedreno_devices.py"
s = open(p).read()
old = "GPUProps(enable_tp_ubwc_flag_hint = False, has_eolm_eogm = False)"
assert s.count(old) == 1, "own722 step must run first"
s = s.replace(old, "GPUProps(enable_tp_ubwc_flag_hint = False, has_eolm_eogm = False,\n                  gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.FULL.value)")
open(p, "w").write(s)
print("[gmemdepthfull] A722 gmem_ccu_depth_cache_fraction = FULL")

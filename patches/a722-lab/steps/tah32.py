"""A722 tile_align_h 16 -> 32 (upstream A710/A720 use 32)."""
import re
p = "src/freedreno/common/freedreno_devices.py"
s = open(p).read()
blk = re.search(r"add_gpus\(\[\n\s+GPUId\(chip_id=0x43020100, name=\"Adreno \(TM\) 722\"\),.*?\n    \)\)\n", s, re.S)
assert blk
b = blk.group(0)
assert b.count("tile_align_h = 16,") == 1
s = s[:blk.start()] + b.replace("tile_align_h = 16,", "tile_align_h = 32,") + s[blk.end():]
open(p, "w").write(s)
print("[tah32] A722 tile_align_h = 32")

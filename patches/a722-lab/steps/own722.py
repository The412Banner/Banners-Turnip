"""Own Adreno 722 entry for freedreno_devices.py, from Qualcomm driver captures on a Retroid
Pocket Duo (DriverLab / freedreno .rd, Vulkan CTS, driver V@0800.73).

Starts from upstream's a720_raw_magic_regs (Mesa MR 44466) and changes only the values the
Qualcomm driver writes differently on A722 (every Vulkan capture agrees):
  UCHE_CACHE_WAYS      0x00040004 -> 0
  SP_CHICKEN_BITS      0x00001400 -> 0x00000400
  SP_CHICKEN_BITS_2    0          -> 0x00000010
  SP_UNKNOWN_AB01      1          -> 0          (1 is the GLES value)
  RB_CCU_DBG_ECO_CNTL  0          -> 0x00080000
Turnip ORs two bits into these registers from GPUProps; the Qualcomm driver sets neither:
  TPL1_DBG_ECO_CNTL1.TP_UBWC_FLAG_HINT (enable_tp_ubwc_flag_hint = False)
  SP_CHICKEN_BITS.EOLM_ENABLE           (has_eolm_eogm = False)
num_ccu = 2: the Qualcomm driver's GMEM color CCU offset is 0xFC000 (1 MB - 2 x 64 KB / 8).
"""
import re

p = "src/freedreno/common/freedreno_devices.py"
s = open(p).read()

m = re.search(r"^a720_raw_magic_regs = \[\n(.*?)^    \]\n", s, re.S | re.M)
assert m, "a720_raw_magic_regs not found"
body = m.group(1)

def setval(body, reg, new):
    pat = re.compile(r"(\[A6XXRegs\.REG_A[67]XX_" + reg + r",\s*)0x[0-9a-fA-F]+\]")
    assert len(pat.findall(body)) == 1, reg
    return pat.sub(lambda mm: mm.group(1) + new + "]", body)

body = setval(body, "UCHE_CACHE_WAYS", "0x00000000")
body = setval(body, "SP_CHICKEN_BITS", "0x00000400")
body = setval(body, "SP_CHICKEN_BITS_2", "0x00000010")
body = setval(body, "SP_UNKNOWN_AB01", "0x00000000")
body = setval(body, "RB_CCU_DBG_ECO_CNTL", "0x00080000")
a722 = "a722_raw_magic_regs = [\n" + body + "    ]\n"

blk = re.search(r"add_gpus\(\[\n\s+GPUId\(chip_id=0x43020100, name=\"Adreno \(TM\) 722\"\),.*?\n    \)\)\n", s, re.S)
assert blk, "A722 add_gpus block not found"
b = blk.group(0)
for old, new in [
    ("[a7xx_base, a7xx_gen1],", "[a7xx_base, a7xx_gen1,\n         GPUProps(enable_tp_ubwc_flag_hint = False, has_eolm_eogm = False)],"),
    ("num_ccu = 1,", "num_ccu = 2,"),
    ("raw_magic_regs = a730_raw_magic_regs,", "raw_magic_regs = a722_raw_magic_regs,"),
]:
    assert b.count(old) == 1, old
    b = b.replace(old, new)
s = s[:blk.start()] + a722 + "\n" + b + s[blk.end():]
open(p, "w").write(s)
compile(s, p, "exec")
print("[own722] A722: a722_raw_magic_regs (5 values from captures), num_ccu 2, UBWC hint + EOLM off")

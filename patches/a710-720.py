#!/usr/bin/env python3
"""
Idempotent Adreno 722 override for freedreno_devices.py.

Adreno 710 and 720 are in upstream Mesa (4db0b15c, 2026-09-23) with the same
per-GPU raw magic regs Vauzi-17/710 captured, so they are no longer patched
here. Mesa's A722 entry still reuses the A730 regs with num_ccu = 1; this
script replaces it with Vauzi-17/710's A722 regs (captured from real A722
blob command streams as .rd traces, decoded with cffdump) and num_ccu = 2
(Vauzi-17/710 5db89bd, tested on A720/A722 hardware).

2026-11-01: four values corrected to what the Qualcomm driver (V@0800.73,
Retroid Pocket Duo) writes, from DriverLab .rd captures of the same CTS tests
on both drivers:
  PC_MODE_CNTL        0x3f -> 0x1f1f
  SP_UNKNOWN_AB01     1    -> 0      (1 is the GLES value; Vulkan writes 0)
  TPL1_DBG_ECO_CNTL1  UBWC flag hint off (enable_tp_ubwc_flag_hint = False);
                      a7xx_gen1 turned it on, giving 0x40700 instead of 0x700.
                      Mesa notes this bit must match the system driver.
  SP_CHICKEN_BITS     EOLM bit off (has_eolm_eogm = False): 0x402 -> 0x400.
num_ccu = 2 is confirmed by the blob's GMEM CCU color offset (0xFC000 =
1 MB - 2 CCUs x 64 KB / 8).

Chip IDs:
  A722: 0x43020100 + wildcard 0xffff43020100

magic_regs no longer exists in Mesa (17ca6174, 2026-10-05); the values it
held are raw_magic_regs now.

Safe to run multiple times.
"""

from pathlib import Path
import sys

DEVICES_PY = Path("src/freedreno/common/freedreno_devices.py")

MARKER_BEGIN = "# BEGIN FD722_CUSTOM"
MARKER_END = "# END FD722_CUSTOM"

CUSTOM_BLOCK = r'''# BEGIN FD722_CUSTOM

a722_raw_magic_regs = [
        [A6XXRegs.REG_A6XX_UCHE_CACHE_WAYS, 0x00000000],
        [A6XXRegs.REG_A6XX_TPL1_DBG_ECO_CNTL, 0x03000000],
        [A6XXRegs.REG_A6XX_TPL1_DBG_ECO_CNTL1, 0x00000700],

        [A6XXRegs.REG_A6XX_SP_CHICKEN_BITS, 0x00000400],
        [A6XXRegs.REG_A7XX_SP_CHICKEN_BITS_1, 0x01400400],
        [A6XXRegs.REG_A7XX_SP_CHICKEN_BITS_2, 0x00000010],
        [A6XXRegs.REG_A7XX_SP_CHICKEN_BITS_3, 0x00000000],

        [A6XXRegs.REG_A7XX_UCHE_UNKNOWN_0E10, 0x00000000],
        [A6XXRegs.REG_A7XX_UCHE_UNKNOWN_0E11, 0x00000000],
        [A6XXRegs.REG_A7XX_SP_HLSQ_DBG_ECO_CNTL, 0x00000000],
        [A6XXRegs.REG_A6XX_SP_DBG_ECO_CNTL, 0x11000000],

        [A6XXRegs.REG_A6XX_PC_MODE_CNTL, 0x00001f1f],
        [A6XXRegs.REG_A6XX_PC_DBG_ECO_CNTL, 0x20100000],
        [A6XXRegs.REG_A7XX_PC_UNKNOWN_9E24, 0x01fc7f00],

        [A6XXRegs.REG_A7XX_VFD_DBG_ECO_CNTL, 0x00000000],
        [A6XXRegs.REG_A7XX_SP_ISDB_CNTL, 0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_AE6A, 0x00000000],
        [A6XXRegs.REG_A7XX_SP_HLSQ_TIMEOUT_THRESHOLD_DP, 0x00000080],
        [A6XXRegs.REG_A7XX_SP_HLSQ_DBG_ECO_CNTL_1, 0x00000000],
        [A6XXRegs.REG_A7XX_SP_HLSQ_MODE_CNTL, 0x00000000],

        [A6XXRegs.REG_A7XX_SP_UNKNOWN_AB01, 0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_AB22, 0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_B310, 0x00000000],

        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE2,   0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE2+1, 0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE4,   0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE4+1, 0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE6,   0x00000000],
        [A6XXRegs.REG_A7XX_SP_UNKNOWN_0CE6+1, 0x00000000],

        [A6XXRegs.REG_A7XX_GRAS_ROTATION_CNTL, 0x00000000],
        [A6XXRegs.REG_A6XX_GRAS_DBG_ECO_CNTL,  0x00000800],

        [A6XXRegs.REG_A7XX_RB_UNKNOWN_8E79, 0x00000000],
        [A6XXRegs.REG_A7XX_RB_LRZ_CNTL2, 0x00000000],
        [A6XXRegs.REG_A7XX_RB_CCU_DBG_ECO_CNTL, 0x00080000],
        [A6XXRegs.REG_A6XX_VPC_DBG_ECO_CNTL, 0x02000000],
        [A6XXRegs.REG_A6XX_UCHE_UNKNOWN_0E12, 0x03200000],

        # Were magic_regs (RB_DBG_ECO_CNTL / RB_RBP_CNTL = 0) before Mesa 17ca6174.
        [A6XXRegs.REG_A6XX_RB_RBP_CNTL,     0x0],
        [A6XXRegs.REG_A6XX_RB_DBG_ECO_CNTL, 0x0],
]

add_gpus([
        GPUId(chip_id=0x43020100, name="FD722"),
        GPUId(chip_id=0xffff43020100, name="FD722"),
    ], A6xxGPUInfo(
        CHIP.A7XX,
        [a7xx_base, a7xx_gen1,
         # Match the Qualcomm driver: UBWC flag hint off, no EOLM/EOGM.
         GPUProps(enable_tp_ubwc_flag_hint = False, has_eolm_eogm = False)],
        num_ccu = 2,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 1024,
        tile_max_h = 1024,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        highest_bank_bit = 16,
        raw_magic_regs = a722_raw_magic_regs,
    ))

# END FD722_CUSTOM

'''


def find_call_end(text: str, start: int) -> int:
    depth = 0
    started = False
    quote = None
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            continue

        if ch in ("'", '"'):
            quote = ch
            continue

        if ch == "(":
            depth += 1
            started = True
        elif ch == ")":
            depth -= 1
            if started and depth == 0:
                j = i + 1
                while j < len(text) and text[j] in " \t\r\n":
                    j += 1
                return j

    raise RuntimeError("Could not find end of add_gpus block")


def remove_marker_block(text: str) -> str:
    begin = text.find(MARKER_BEGIN)
    if begin < 0:
        return text

    end = text.find(MARKER_END, begin)
    if end < 0:
        raise RuntimeError("Found custom begin marker but missing end marker")

    end = text.find("\n", end)
    if end < 0:
        end = len(text)
    else:
        end += 1

    while end < len(text) and text[end] in "\r\n":
        end += 1

    return text[:begin] + text[end:]


def remove_existing_add_gpus_for_chip(text: str, chip_id: str) -> tuple[str, int]:
    removed = 0
    needle = f"chip_id={chip_id}"

    while True:
        idx = text.find(needle)
        if idx < 0:
            break

        start = text.rfind("add_gpus([", 0, idx)
        if start < 0:
            raise RuntimeError(f"Found {needle}, but could not find add_gpus start")

        end = find_call_end(text, start)
        text = text[:start] + text[end:]
        removed += 1

    return text, removed


def find_add_gpus_block_start(text: str, anchor_str: str) -> int:
    idx = text.find(anchor_str)
    if idx < 0:
        return -1
    return text.rfind("add_gpus([", 0, idx)


def main() -> int:
    if not DEVICES_PY.exists():
        print(f"ERROR: {DEVICES_PY} not found. Run this from Mesa repo root.", file=sys.stderr)
        return 1

    content = DEVICES_PY.read_text()
    original = content

    content = remove_marker_block(content)

    total_removed = 0
    for chip in ("0x43020100", "0xffff43020100"):
        content, removed = remove_existing_add_gpus_for_chip(content, chip)
        total_removed += removed

    anchor = "chip_id=0x07030002"
    block_start = find_add_gpus_block_start(content, anchor)

    if block_start < 0:
        print("ERROR: could not find FD725 anchor chip_id=0x07030002", file=sys.stderr)
        return 1

    content = content[:block_start] + CUSTOM_BLOCK + content[block_start:]

    if content != original:
        DEVICES_PY.write_text(content)
        print(f"✓ removed old A722 add_gpus blocks: {total_removed}")
        print("✓ inserted FD722 custom block")
        print(f"✓ wrote {DEVICES_PY}")
    else:
        print("No changes needed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

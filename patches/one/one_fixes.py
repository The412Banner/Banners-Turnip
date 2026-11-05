#!/usr/bin/env python3
"""
Fixes for the One driver, each limited to the GPUs it is meant for. Run from the Mesa tree
after one_gpu_gates.py.

All GPUs (generic code, no chip check):
  dd/tu/0001   barrier flushes kept at a suspended render pass chain
  dd/nir/0001  32-bit SSBO offset wrap
  dd/scripts/process_heap_usage.py   memory budget counts the whole process
Android, all Adreno (u_gralloc and vk_android.c are only built for -Dplatforms=android):
  dd/scripts/add_aimapper_gralloc.py   IMapper5 gralloc backend
  dd/scripts/add_ubwc_swapchain_usage.py   UBWC swapchain buffers
A8xx only (code runs under CHIP >= A8XX, or edits A8xx entries):
  dd/lrz/0001, dd/fdl/0001, dd/scripts/a8xx_resolve_cr_cntl.py, a8xx_sp_hysteresis.py,
  a8xx_lrz_color_mask.py; apply_a8xx_cat4_rpt.py (A845 / A850 chip IDs only);
  chip IDs A829 0x44030A00, A845 0x44041430, A850 0x44051431; disable_gmem on A810 and A829.
A7xx gen1 only (A710, A720, A722, A725, A730): dd/scripts/apply_a7xx_gen1_quirks.py
A722 only: disable_gmem (GMEM gives CCU write page faults on A722 in every Turnip build).

Every step must change the tree or find its change already in Mesa; anything else stops the
build. Sources and authors: dd/SOURCE.md.
"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DD = HERE / "dd"
DEVICES = Path("src/freedreno/common/freedreno_devices.py")


def die(msg):
    sys.exit(f"one_fixes.py: {msg}")


# LAB ONLY (branch lab/aio-a8xx-ab, never merged): ONE_FIXES_SKIP="rel,rel" leaves those steps out for A/B builds.
SKIP = {x.strip() for x in __import__("os").environ.get("ONE_FIXES_SKIP", "").split(",") if x.strip()}


def skipped(rel):
    if rel in SKIP:
        print(f"  {rel}: SKIPPED (ONE_FIXES_SKIP, lab build)")
        return True
    return False


def run_patch(rel):
    if skipped(rel):
        return
    p = DD / rel
    if subprocess.run(["git", "apply", "--check", str(p)], capture_output=True).returncode == 0:
        subprocess.run(["git", "apply", "--whitespace=nowarn", str(p)], check=True)
        print(f"  {rel}: applied")
    elif subprocess.run(["git", "apply", "-R", "--check", str(p)], capture_output=True).returncode == 0:
        print(f"  {rel}: already in Mesa")
    else:
        r = subprocess.run(["git", "apply", "--check", str(p)], capture_output=True, text=True)
        die(f"{rel} does not apply: {r.stderr.strip()}")


def run_script(rel):
    if skipped(rel):
        return
    r = subprocess.run([sys.executable, str(DD / rel)], capture_output=True, text=True)
    for line in (r.stdout + r.stderr).strip().splitlines():
        print(f"  {rel}: {line}")
    if r.returncode:
        die(f"{rel} failed")


def entry_block(content, anchor):
    """Text of the add_gpus() entry holding `anchor`: from the anchor to the next add_gpus(."""
    m = re.search(re.escape(anchor), content, re.IGNORECASE)
    if not m:
        die(f"entry {anchor!r} not found")
    start = content.rfind("add_gpus(", 0, m.start())
    end = content.find("add_gpus(", m.end())
    return start, (len(content) if end < 0 else end)


def set_disable_gmem(content, anchor, what):
    start, end = entry_block(content, anchor)
    block = content[start:end]
    if re.search(r"disable_gmem\s*=\s*True", block):
        print(f"  {what}: disable_gmem already on")
        return content
    if re.search(r"disable_gmem\s*=\s*False", block):
        block = re.sub(r"disable_gmem\s*=\s*False", "disable_gmem = True", block, count=1)
    elif "GPUProps(\n" in block:
        block = block.replace("GPUProps(\n", "GPUProps(\n            disable_gmem = True,\n", 1)
    else:
        n = block.count("[a7xx_base, a7xx_gen1],")
        if n != 1:
            die(f"{what}: no GPUProps to extend")
        block = block.replace("[a7xx_base, a7xx_gen1],",
                              "[a7xx_base, a7xx_gen1, GPUProps(disable_gmem = True)],")
    print(f"  {what}: disable_gmem = True")
    return content[:start] + block + content[end:]


def add_ids_before(content, anchor, ids, what):
    if all(re.search(rf"chip_id=0x{i}\b", content, re.IGNORECASE) for i, _ in ids):
        print(f"  {what}: already present")
        return content
    m = re.search(re.escape(anchor), content, re.IGNORECASE)
    if not m:
        die(f"{what}: anchor {anchor!r} not found")
    line_start = content.rfind("\n", 0, m.start()) + 1
    new = "".join(f'        GPUId(chip_id=0x{i}, name="Adreno (TM) {n}"),{" # KGSL" if not i.startswith("ffff") else ""}\n'
                  for i, n in ids if not re.search(rf"chip_id=0x{i}\b", content, re.IGNORECASE))
    print(f"  {what}: added")
    return content[:line_start] + new + content[line_start:]


def devices_edits():
    c = DEVICES.read_text()
    c = add_ids_before(c, 'GPUId(chip_id=0x44030a20, name="Adreno (TM) 829")',
                       [("44030A00", "829"), ("ffff44030A00", "829")], "A829 chip IDs 0x44030A00")
    # A845 / A850 ride on the 3-slice A840 entry (as DD-Turnip).
    c = add_ids_before(c, 'GPUId(chip_id=0xffff44050A31, name="Adreno (TM) 840")',
                       [("44041430", "845"), ("44051431", "850")], "A845 / A850 KGSL chip IDs")
    c = set_disable_gmem(c, 'GPUId(chip_id=0xffff44010000, name="Adreno (TM) 810")', "A810")
    c = set_disable_gmem(c, 'GPUId(chip_id=0xffff44030a20, name="Adreno (TM) 829")', "A829")
    if not re.search(r"# BEGIN FD722_CUSTOM", c):
        die("FD722_CUSTOM entry (patches/a710-720.py) missing")
    c = set_disable_gmem(c, "GPUId(chip_id=0x43020100,", "A722")
    if len(re.findall(r"chip_id=0x43020100\b", c)) != 1:
        die("A722 chip ID 0x43020100 is in more than one entry")
    compile(c, str(DEVICES), "exec")
    DEVICES.write_text(c)


def main():
    if not DEVICES.is_file():
        die("run from the Mesa source tree")
    for rel in ("tu/0001-tu-flush-before-suspended-render-pass-chain.patch",
                "nir/0001-nir-lower-explicit-io-keep-32bit-offset-wrap.patch"):
        run_patch(rel)
    run_script("scripts/process_heap_usage.py")
    run_script("scripts/add_aimapper_gralloc.py")
    run_script("scripts/add_ubwc_swapchain_usage.py")
    for rel in ("lrz/0001-tu-a8xx-lrz-reset-cntl-after-flush.patch",
                "fdl/0001-fdl-a8xx-buffer-num-elements.patch"):
        run_patch(rel)
    for rel in ("scripts/a8xx_resolve_cr_cntl.py", "scripts/a8xx_sp_hysteresis.py",
                "scripts/a8xx_lrz_color_mask.py", "scripts/apply_a7xx_gen1_quirks.py"):
        run_script(rel)
    devices_edits()
    # cat4 workaround keys on the A845 / A850 KGSL chip IDs added above.
    run_script("scripts/apply_a8xx_cat4_rpt.py")
    print("one_fixes.py: done")


main()

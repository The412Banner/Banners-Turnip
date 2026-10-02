#!/usr/bin/env python3
"""Check a Turnip driver zip before the combined workflow attaches it to a release.

  android  the AdrenoTools zip build_turnip.sh + the "Rename ZIP" step make: exactly
           libvulkan_freedreno.so + meta.json, meta.json named for this release, an AArch64
           Android HAL-style driver (exports HMI).
  wayland  the zip build_turnip_wayland.sh makes for Bannerlator's "Import Wayland game driver":
           libvulkan_freedreno.so + libdrm.so + meta.json at the zip root (what
           WaylandGameDriverManager.installDriver accepts), and a Linux-style Vulkan ICD on bionic:
           exports vk_icdGetInstanceProcAddr, links libc.so + libwayland-client.so + libdrm.so and
           nothing Android-platform (libhardware / libnativewindow / libsync) or glibc, has wl_
           symbols, and every libwayland-client / libdrm symbol it imports exists in the libraries
           Bannerlator's Wayland layer ships (patches/wayland/layer-abi/*.exports).
  linux    the zip build_turnip_linux.sh makes for Bannerlator's Linux runtime (gamescope + the
           native ARM64 Steam client): libvulkan_freedreno.so + freedreno_icd.aarch64.json +
           meta.json at the zip root, and a GLIBC Vulkan ICD - exports vk_icdGetInstanceProcAddr,
           links libc.so.6 and the runtime's libdrm.so.2 / libwayland-client.so.0 / libxcb.so.1,
           nothing bionic and nothing Android-platform, and carries the two KGSL fixes the runtime
           needs (patches/linux). The minimum glibc it asks for is recorded in the report.

Both kinds also check the per-variant markers (the recipe really reached the binary).
Any failed check exits 1. The facts are written to --report as JSON for the release body.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

# Strings the recipe puts into the binary. Presence only: upstream Mesa taking one of these
# over must not fail a build, a recipe that did not land must.
VARIANT_MARKERS = {
    "regular": [],
    "a8xx": ["Adreno (TM) 825", "deck_emu"],
    "710-720-test": ["FD710", "FD720", "FD722"],
    # A boolean in the device table: no string to look for. patches/8g2_oneui.py fails the build if it cannot apply.
    "8g2-oneui": [],
}
WAYLAND_MARKERS = [
    "banner_ahb_v1",                                            # banner_ahb_wsi.py protocol
    "gralloc answered the UBWC request with a linear buffer",   # its UBWC request
]
WAYLAND_NEEDED_REQUIRED = {"libc.so", "libwayland-client.so", "libdrm.so"}
WAYLAND_NEEDED_ALLOWED = WAYLAND_NEEDED_REQUIRED | {"libm.so", "libdl.so", "libz.so", "liblog.so"}
WAYLAND_NEEDED_FORBIDDEN = {"libhardware.so", "libnativewindow.so", "libsync.so", "libc.so.6",
                            "libm.so.6", "libdl.so.2", "libpthread.so.0", "libstdc++.so.6", "libgcc_s.so.1"}
# The glibc build. Sonames are versioned on a Linux distribution, which is the cheapest proof this
# is not a bionic object with a renamed libc: bionic has no libc.so.6 and no versioned sonames.
LINUX_NEEDED_REQUIRED = {"libc.so.6", "libdrm.so.2", "libwayland-client.so.0", "libxcb.so.1"}
LINUX_NEEDED_ALLOWED = LINUX_NEEDED_REQUIRED | {
    "libm.so.6", "libdl.so.2", "libpthread.so.0", "librt.so.1", "libstdc++.so.6", "libgcc_s.so.1",
    "libz.so.1", "libzstd.so.1", "libexpat.so.1", "libxcb-dri3.so.0", "libxcb-present.so.0",
    "libxcb-shm.so.0", "libxcb-sync.so.1", "libxcb-xfixes.so.0", "libxcb-randr.so.0",
    "libxcb-dri2.so.0", "libX11-xcb.so.1", "libxshmfence.so.1", "libatomic.so.1",
    # Arch's libc.so is a linker script that names the dynamic loader AS_NEEDED, so a glibc build
    # against that sysroot carries it as a DT_NEEDED entry. Normal, and it is the loader itself.
    "ld-linux-aarch64.so.1"}
# Anything from the Android side means the build picked up the wrong sysroot.
LINUX_NEEDED_FORBIDDEN = {"libc.so", "libm.so", "libdl.so", "liblog.so", "libsync.so",
                          "libhardware.so", "libnativewindow.so", "libc++_shared.so", "libz.so"}
# Strings that only exist because patches/common/mesa-44838 (Danil's KGSL sync series) was applied.
LINUX_MARKERS = ["KGSL timestamp %s failed: context %u, timestamp %u, errno %d (%s)",
                 "KGSL sync FD wait failed: fd %d, errno %d (%s)"]
GPU_NAME_RE = re.compile(rb"(?<=\x00)(FD[0-9]{3}|Adreno \(TM\) [0-9X][0-9X-]*|Adreno X[0-9][0-9-]*)(?=\x00)")


class Checks:
    def __init__(self):
        self.items = []

    def check(self, ok, what):
        self.items.append({"ok": bool(ok), "check": what})
        print(("  PASS  " if ok else "  FAIL  ") + what)
        return ok

    @property
    def failed(self):
        return [c["check"] for c in self.items if not c["ok"]]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"{' '.join(cmd)} failed ({r.returncode}): {r.stderr.strip()}")
    return r.stdout


def elf_header_ok(data):
    # ELF magic, 64-bit, little-endian, e_machine 0xB7 (AArch64), as the Bannerlator importer checks.
    return (len(data) >= 20 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
            and int.from_bytes(data[18:20], "little") == 0xB7)


def dynamic(readelf, path):
    out = run([readelf, "-d", "-W", path])
    needed = re.findall(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]", out)
    soname = re.findall(r"\(SONAME\)\s+Library soname: \[([^\]]+)\]", out)
    return needed, (soname[0] if soname else "")


def dyn_syms(readelf, path):
    """[(name, type, bind, ndx)] from the dynamic symbol table."""
    syms = []
    for line in run([readelf, "--dyn-syms", "-W", path]).splitlines():
        if not re.match(r"^\s*\d+:", line):
            continue
        tok = [t for t in line.split() if not (t.startswith("[") and t.endswith("]"))]
        if len(tok) < 8:
            continue
        name = tok[7].split("@")[0]
        syms.append((name, tok[3], tok[4], tok[6]))
    return syms


def load_exports(path):
    with open(path) as f:
        return {l.strip() for l in f if l.strip() and not l.startswith("#")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["android", "wayland", "linux"], required=True)
    ap.add_argument("--zip", required=True)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--expect-name", required=True, help="meta.json name")
    ap.add_argument("--expect-package-version", default="")
    ap.add_argument("--layer-abi", default="", help="dir with libwayland-client.so.exports / libdrm.so.exports")
    ap.add_argument("--build-report", default="", help="JSON facts from the build to merge in")
    ap.add_argument("--report", required=True)
    ap.add_argument("--readelf", default="readelf")
    a = ap.parse_args()

    report = {}
    if a.build_report:
        with open(a.build_report) as f:
            report = json.load(f)

    zname = os.path.basename(a.zip)
    print(f"== verifying {a.kind} zip {zname} (variant {a.variant})")
    c = Checks()
    zdata = open(a.zip, "rb").read()

    with zipfile.ZipFile(a.zip) as z:
        infos = z.infolist()
        entries = sorted(i.filename for i in infos)
        files = {i.filename: z.read(i) for i in infos if not i.is_dir()}
    c.check(zipfile.is_zipfile(a.zip), "is a zip archive")

    if a.kind == "android":
        expected = ["libvulkan_freedreno.so", "meta.json"]
    elif a.kind == "linux":
        expected = ["freedreno_icd.aarch64.json", "libvulkan_freedreno.so", "meta.json"]
    else:
        expected = ["libdrm.so", "libvulkan_freedreno.so", "meta.json"]
    c.check(entries == expected, f"zip entries are exactly {expected} (got {entries})")

    so = files.get("libvulkan_freedreno.so", b"")
    c.check(elf_header_ok(so), "libvulkan_freedreno.so is a 64-bit little-endian AArch64 ELF")

    try:
        meta = json.loads(files.get("meta.json", b"{}").decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        meta = {}
        c.check(False, f"meta.json parses ({e})")
    c.check(meta.get("schemaVersion") == 1, "meta.json schemaVersion 1")
    c.check(meta.get("name") == a.expect_name, f"meta.json name == '{a.expect_name}' (got '{meta.get('name')}')")
    c.check(re.fullmatch(r"Vulkan 1\.\d+\.\d+", str(meta.get("driverVersion", ""))) is not None,
            f"meta.json driverVersion looks like 'Vulkan 1.x.y' (got '{meta.get('driverVersion')}')")
    if a.expect_package_version:
        c.check(str(meta.get("packageVersion")) == a.expect_package_version,
                f"meta.json packageVersion == {a.expect_package_version} (got {meta.get('packageVersion')})")

    with tempfile.TemporaryDirectory() as td:
        sop = os.path.join(td, "libvulkan_freedreno.so")
        open(sop, "wb").write(so)
        needed, soname = dynamic(a.readelf, sop)
        syms = dyn_syms(a.readelf, sop)
        versions = run([a.readelf, "-V", "-W", sop])
        drm_soname = ""
        if a.kind == "wayland" and "libdrm.so" in files:
            dp = os.path.join(td, "libdrm.so")
            open(dp, "wb").write(files["libdrm.so"])
            c.check(elf_header_ok(files["libdrm.so"]), "libdrm.so is a 64-bit little-endian AArch64 ELF")
            _, drm_soname = dynamic(a.readelf, dp)
            c.check(drm_soname == "libdrm.so", f"libdrm.so SONAME is libdrm.so (got '{drm_soname}')")

    defined = {n: (t, b) for n, t, b, ndx in syms if ndx != "UND" and n}
    imported = sorted({n for n, t, b, ndx in syms if ndx == "UND" and n})
    wl_symbols = sorted({n for n, t, b, ndx in syms if n.startswith("wl_")})
    xcb_symbols = sorted({n for n, t, b, ndx in syms if n.startswith("xcb_")})
    # The highest glibc symbol version asked for: the floor the runtime's glibc has to clear.
    min_glibc = ""
    glibc_versions = sorted({m for m in re.findall(r"GLIBC_(\d+\.\d+(?:\.\d+)?)", versions)},
                            key=lambda v: [int(x) for x in v.split(".")])
    if glibc_versions:
        min_glibc = glibc_versions[-1]
    vk_icd = sorted(n for n in defined if n.startswith("vk_icd"))
    gpu_names = sorted({m.decode() for m in GPU_NAME_RE.findall(so)})

    print(f"  NEEDED: {' '.join(needed)}")
    print(f"  SONAME: {soname}")
    print(f"  exported vk_icd*: {' '.join(vk_icd) or '(none)'}")
    print(f"  HMI exported: {'HMI' in defined}")
    print(f"  wl_ symbols: {len(wl_symbols)}")

    c.check(soname == "libvulkan_freedreno.so", f"SONAME is libvulkan_freedreno.so (got '{soname}')")
    c.check(b"drirc.d" not in so and "libexpat.so.1" not in needed,
            "driconf defaults are built in (no drirc.d path, no libexpat)")
    if a.kind == "linux":
        c.check("libc.so.6" in needed, "NEEDED has glibc libc.so.6")
        c.check("GLIBC_" in versions, "asks for GLIBC_ symbol versions (a real glibc build)")
    else:
        c.check("libc.so" in needed, "NEEDED has bionic libc.so")
        c.check("libc.so.6" not in needed and "GLIBC_" not in versions, "no glibc (libc.so.6 / GLIBC_ version refs)")

    if a.kind == "android":
        c.check("HMI" in defined, "exports HMI (Android HAL driver, what AdrenoTools loads)")
    elif a.kind == "linux":
        c.check(LINUX_NEEDED_REQUIRED <= set(needed), f"NEEDED has {sorted(LINUX_NEEDED_REQUIRED)}")
        bad = sorted(set(needed) & LINUX_NEEDED_FORBIDDEN)
        c.check(not bad, f"NEEDED has nothing bionic or Android-platform (found {bad})")
        unknown = sorted(set(needed) - LINUX_NEEDED_ALLOWED)
        c.check(not unknown, f"NEEDED only from the runtime's libraries (unexpected {unknown})")
        t = defined.get("vk_icdGetInstanceProcAddr")
        c.check(t is not None and t[0] == "FUNC" and t[1] == "GLOBAL", "exports vk_icdGetInstanceProcAddr (FUNC GLOBAL)")
        c.check("HMI" not in defined, "does not export HMI (not an Android-platform build)")
        c.check(len(wl_symbols) > 0, f"has wl_ symbols, so the Wayland WSI is in ({len(wl_symbols)})")
        c.check(len(xcb_symbols) > 0, f"has xcb_ symbols, so the X11 WSI is in ({len(xcb_symbols)})")
        c.check(b"kgsl" in so, "carries a 'kgsl' string (the KGSL backend is compiled in)")
        for m in LINUX_MARKERS:
            c.check(m.encode() in so, f"carries the KGSL patch marker '{m}'")
        c.check(min_glibc != "", f"a minimum glibc could be read from the binary (got '{min_glibc}')")
        c.check(str(meta.get("minGlibc")) == min_glibc,
                f"meta.json minGlibc == {min_glibc} (got {meta.get('minGlibc')})")
        c.check(meta.get("libc") == "glibc", f"meta.json libc == glibc (got {meta.get('libc')})")
        c.check(meta.get("kind") == "linux-vulkan-icd", f"meta.json kind == linux-vulkan-icd (got {meta.get('kind')})")
        c.check(meta.get("installPath") == "usr/lib/libvulkan_freedreno.so",
                f"meta.json installPath is the runtime's driver path (got {meta.get('installPath')})")
        c.check("libraryName" not in meta and "minApi" not in meta,
                "meta.json has no libraryName / minApi (never handed to AdrenoTools)")
        try:
            icd = json.loads(files.get("freedreno_icd.aarch64.json", b"{}").decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            icd = {}
            c.check(False, f"freedreno_icd.aarch64.json parses ({e})")
        c.check(icd.get("ICD", {}).get("library_path") == "./libvulkan_freedreno.so",
                "the ICD manifest points at ./libvulkan_freedreno.so")
        c.check(re.fullmatch(r"\d+\.\d+\.\d+", str(icd.get("ICD", {}).get("api_version", ""))) is not None,
                f"the ICD manifest has an api_version (got {icd.get('ICD', {}).get('api_version')})")
    else:
        c.check(WAYLAND_NEEDED_REQUIRED <= set(needed),
                f"NEEDED has {sorted(WAYLAND_NEEDED_REQUIRED)}")
        bad = sorted(set(needed) & WAYLAND_NEEDED_FORBIDDEN)
        c.check(not bad, f"NEEDED has no libhardware / libnativewindow / libsync / glibc libraries (found {bad})")
        unknown = sorted(set(needed) - WAYLAND_NEEDED_ALLOWED)
        c.check(not unknown, f"NEEDED only from {sorted(WAYLAND_NEEDED_ALLOWED)} (unexpected {unknown})")
        t = defined.get("vk_icdGetInstanceProcAddr")
        c.check(t is not None and t[0] == "FUNC" and t[1] == "GLOBAL", "exports vk_icdGetInstanceProcAddr (FUNC GLOBAL)")
        c.check("HMI" not in defined, "does not export HMI (not an Android-platform build)")
        c.check(len(wl_symbols) > 0, f"has wl_ symbols ({len(wl_symbols)})")
        c.check(b"wayland" in so.lower(), "carries a 'wayland' string (Bannerlator's importer warns without one)")
        if a.layer_abi:
            wl_exp = load_exports(os.path.join(a.layer_abi, "libwayland-client.so.exports"))
            drm_exp = load_exports(os.path.join(a.layer_abi, "libdrm.so.exports"))
            miss_wl = [n for n in imported if n.startswith("wl_") and n not in wl_exp]
            miss_drm = [n for n in imported if n.startswith("drm") and n not in drm_exp]
            c.check(not miss_wl, f"every wl_ import exists in the layer's libwayland-client (missing {miss_wl})")
            c.check(not miss_drm, f"every drm import exists in the layer's libdrm (missing {miss_drm})")
        c.check("libraryName" not in meta, "meta.json has no libraryName (never handed to AdrenoTools)")
        for m in WAYLAND_MARKERS:
            c.check(m.encode() in so, f"carries '{m}'")

    if a.variant not in VARIANT_MARKERS:
        print(f"  note: no marker list for variant '{a.variant}'")
    for m in VARIANT_MARKERS.get(a.variant, []):
        c.check(m.encode() in so, f"recipe marker '{m}' is in the binary")

    report.update({
        "platform": a.kind,
        "variant": a.variant,
        "zip": zname,
        "size": len(zdata),
        "sha256": hashlib.sha256(zdata).hexdigest(),
        "entries": entries,
        "so_size": len(so),
        "meta": meta,
        "needed": needed,
        "soname": soname,
        "vk_icd_exports": vk_icd,
        "exports_hmi": "HMI" in defined,
        "wl_symbols": len(wl_symbols),
        "wl_imports": [n for n in imported if n.startswith("wl_")],
        "xcb_symbols": len(xcb_symbols),
        "min_glibc": min_glibc,
        "gpu_names": gpu_names,
        "checks": c.items,
        "verified": not c.failed,
    })
    with open(a.report, "w") as f:
        json.dump(report, f, indent=2)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"### {zname}\n\n")
            f.write(f"- NEEDED: `{' '.join(needed)}`\n- vk_icd exports: `{' '.join(vk_icd) or 'none'}`\n")
            f.write(f"- HMI exported: {'HMI' in defined} · wl_ symbols: {len(wl_symbols)}\n")
            f.write(f"- checks: {len(c.items) - len(c.failed)}/{len(c.items)} passed\n\n")

    if c.failed:
        print(f"== {zname}: {len(c.failed)} check(s) FAILED")
        return 1
    print(f"== {zname}: all {len(c.items)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

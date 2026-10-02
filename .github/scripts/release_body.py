#!/usr/bin/env python3
"""Write the combined release's body from what this run actually produced.

Inputs:
  --info DIR      release-info/ from the resolve job (tag, Mesa commit, versions, dates)
  --zips DIR      every driver zip the build legs uploaded
  --reports DIR   the verify_driver_zip.py report of each leg that got as far as uploading
  --out FILE      release body (Markdown)
  --assets FILE   the zip paths to attach, one per line: only zips whose report says verified,
                  whose sha256 matches the downloaded file and whose Mesa commit is this run's

Exit 3 when the standard Android driver is not among them: without it there is no release
(same rule as before the Wayland legs existed). Anything else missing is written into the body.

Three platforms per driver: the AdrenoTools zip, the `-Wayland` zip for Bannerlator's Wine
containers, and the `-Linux` zip (a glibc ICD) for its Linux runtime and native Steam client.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

REPO_BLOB = "https://github.com/{repo}/blob/{ref}/{path}"

DRIVERS = [
    {
        "variant": "regular", "suffix": "", "label": "A6xx / A7xx", "kind": "Standard",
        "gpus": "Adreno 6xx / 7xx: Snapdragon 600-800 series, 7 Gen, 8 Gen 1-3",
    },
    {
        "variant": "a8xx", "suffix": "-A8xx", "label": "A8xx", "kind": "Snapdragon 8 Elite",
        "gpus": "Adreno 840 / 830 / 829 / 825 / 810: Snapdragon 8 Elite",
    },
    {
        "variant": "710-720-test", "suffix": "-710-720-Test", "label": "A710 / A720 / A722", "kind": "Experimental",
        "gpus": "Adreno 710 / 720 / 722 (unverified on hardware)",
    },
    {
        "variant": "8g2-oneui", "suffix": "-8G2-OneUI", "label": "8 Gen 2 One UI", "kind": "Device-specific",
        "gpus": "Adreno 740: Snapdragon 8 Gen 2 on newer firmware (Samsung One UI)",
    },
]


# One leg of every driver per platform. The suffix is part of the file name catalogs match on,
# so it is fixed: "" is the AdrenoTools zip that has always been called that.
PLATFORMS = ("android", "wayland", "linux")
PLATFORM_SUFFIX = {"android": "", "wayland": "-Wayland", "linux": "-Linux"}


def read_info(d, name):
    try:
        with open(os.path.join(d, name + ".txt")) as f:
            return f.read().strip()
    except OSError:
        return ""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md_cell(s):
    return s.replace("|", "\\|").replace("<", "&lt;")


def mib(n):
    return f"{n / (1024 * 1024):.1f} MB"


def patch_commits(path):
    """[(subject, author)] from a git format-patch series."""
    out, author = [], None
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return out
    for line in text.splitlines():
        if line.startswith("From: "):
            author = re.sub(r"\s*<[^>]*>\s*$", "", line[6:]).strip()
        elif line.startswith("Subject: "):
            subj = re.sub(r"^\[PATCH[^\]]*\]\s*", "", line[9:]).strip()
            out.append((subj, author or "unknown"))
            author = None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--info", required=True)
    ap.add_argument("--zips", required=True)
    ap.add_argument("--reports", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--assets", required=True)
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "The412Banner/Banners-Turnip"))
    ap.add_argument("--ref", default="A8xx", help="branch the patch links point at")
    ap.add_argument("--workdir", default=".", help="repo checkout (patch files)")
    a = ap.parse_args()

    tag = read_info(a.info, "tag")
    githash_full = read_info(a.info, "githash_full")
    if not tag or not re.fullmatch(r"[0-9a-f]{40}", githash_full):
        print("release-info is incomplete (tag / githash_full)", file=sys.stderr)
        return 2
    info = {k: read_info(a.info, k) for k in
            ("mesa_version", "build_date", "githash", "commit_date", "commit_title", "vulkan_version")}
    mesa_url = f"https://gitlab.freedesktop.org/mesa/mesa/-/commit/{githash_full}"

    reports = {}
    for p in glob.glob(os.path.join(a.reports, "**", "*.json"), recursive=True):
        try:
            r = json.load(open(p))
            reports[r["zip"]] = r
        except Exception as e:  # noqa: BLE001
            print(f"ignoring unreadable report {p}: {e}", file=sys.stderr)

    # Status of each of the nine files.
    legs = {}
    assets = []
    for drv in DRIVERS:
        for platform in PLATFORMS:
            name = f"Turnip-{tag}{drv['suffix']}{PLATFORM_SUFFIX[platform]}.zip"
            path = os.path.join(a.zips, name)
            rep = reports.get(name)
            why = ""
            if not os.path.isfile(path):
                why = "did not build"
            elif rep is None:
                why = "no verification report"
            elif not rep.get("verified"):
                why = "failed verification"
            elif rep.get("platform") != platform:
                why = "report is for another platform"
            elif rep.get("mesa_commit") != githash_full:
                why = f"built Mesa {str(rep.get('mesa_commit'))[:10]}, not this release's commit"
            elif rep.get("sha256") != sha256(path):
                why = "zip differs from the verified one"
            ok = not why
            legs[(drv["variant"], platform)] = {"name": name, "ok": ok, "why": why, "report": rep,
                                                "size": os.path.getsize(path) if os.path.isfile(path) else 0}
            if ok:
                assets.append(path)
            print(f"{name}: {'OK' if ok else 'NOT INCLUDED (' + why + ')'}")

    unexpected = sorted(set(os.path.basename(p) for p in glob.glob(os.path.join(a.zips, "*.zip")))
                        - {l["name"] for l in legs.values()})
    for u in unexpected:
        print(f"::warning::unexpected zip {u} is not attached")

    with open(a.assets, "w") as f:
        f.write("".join(p + "\n" for p in assets))

    std = legs[("regular", "android")]
    if not std["ok"]:
        print(f"::error::Standard (A6xx/A7xx) Android driver {std['name']}: {std['why']} - nothing to publish.")
        return 3

    L = []
    w = L.append
    android_bad = [d for d in DRIVERS if not legs[(d["variant"], "android")]["ok"]]
    wayland_bad = [d for d in DRIVERS if not legs[(d["variant"], "wayland")]["ok"]]
    linux_bad = [d for d in DRIVERS if not legs[(d["variant"], "linux")]["ok"]]

    w("> ⚠️ **Automated build** from Mesa `main`: checked by CI, **not tested on a device.**")
    w("")
    for d in android_bad:
        leg = legs[(d["variant"], "android")]
        why = "" if leg["why"] == "did not build" else f" ({leg['why']})"
        w(f"> ❌ **{d['label']}** didn't build this run{why}, so it isn't included.")
        w("")
    for d in wayland_bad:
        if not legs[(d["variant"], "android")]["ok"]:
            continue
        leg = legs[(d["variant"], "wayland")]
        why = "" if leg["why"] == "did not build" else f" ({leg['why']})"
        w(f"> ❌ The **Wayland** build of **{d['label']}** didn't build this run{why}. Its X11 zip is fine.")
        w("")
    for d in linux_bad:
        if not legs[(d["variant"], "android")]["ok"]:
            continue
        leg = legs[(d["variant"], "linux")]
        why = "" if leg["why"] == "did not build" else f" ({leg['why']})"
        w(f"> ❌ The **Linux** build of **{d['label']}** didn't build this run{why}. Its X11 zip is fine.")
        w("")

    # Keep these three rows: update_readme.py reads Commit / Commit title / Vulkan version from past bodies.
    w("| Mesa | |")
    w("| :--- | :--- |")
    w(f"| **Commit** | [`{info['githash']}`]({mesa_url}) |")
    w(f"| **Commit title** | {md_cell(info['commit_title'])} |")
    w(f"| **Vulkan version** | {info['vulkan_version']} |")
    w(f"| **Date** | {info['commit_date']} |")
    w("")
    w("### Downloads")
    w("")
    w("| Driver | GPUs | X11 / AdrenoTools | Bannerlator Wayland | Linux runtime |")
    w("| :--- | :--- | :--- | :--- | :--- |")

    def cell(variant, platform):
        leg = legs[(variant, platform)]
        return f"`{leg['name']}`" if leg["ok"] else "❌ not built"

    short = {
        "regular": ("**Standard**", "Adreno 6xx / 7xx (8 Gen 3 and older)"),
        "a8xx": ("**A8xx** (experimental)", "Adreno 810 / 825 / 829 / 830 / 840 (8 Elite)"),
        "710-720-test": ("**A710 / A720 / A722** (experimental, untested on hardware)", "Adreno 710 / 720 / 722"),
        "8g2-oneui": ("**8 Gen 2 One UI**", "Adreno 740 (8 Gen 2) with UI flicker, e.g. Samsung One UI"),
    }
    for d in DRIVERS:
        label, gpus = short[d["variant"]]
        w(f"| {label} | {gpus} | {cell(d['variant'], 'android')} | {cell(d['variant'], 'wayland')} "
          f"| {cell(d['variant'], 'linux')} |")
    w("")
    w("**Which one?**")
    w("- **X11** (Bannerlator, Winlator, BannerHub, any AdrenoTools app): import the normal zip as a GPU driver. "
      "Not sure which driver? Use **Standard**.")
    w("- **Bannerlator Wayland containers:** *Import Wayland game driver (.zip)*, then pick the `-Wayland` zip.")
    lx = legs[("regular", "linux")]["report"] or {}
    glibc = lx.get("min_glibc") or lx.get("meta", {}).get("minGlibc") or ""
    w("- **Bannerlator Linux runtime** (gamescope + the native ARM64 Steam client): the `-Linux` zip. It is a "
      "**glibc** Vulkan ICD and it is what draws the client and every game the client launches"
      + (f" (needs glibc {glibc} or newer)" if glibc else "") + ". "
      "It is not an AdrenoTools driver and it does not load in a Wine container; the Android zip still puts the "
      "finished frame on the screen.")
    w("")
    w("**Tips:** A8xx: `TU_DEBUG=sysmem` if an A830 looks glitchy, `TU_DEBUG=deck_emu` if a game won't start. "
      "A710 / A720 / A722: `TU_DEBUG=sysmem` (in Winlator also `WRAPPER_BLIT=1`). "
      "8 Gen 2 One UI: only if the Standard driver makes the phone's UI glitch or flicker; on other 8 Gen 2 "
      "devices it causes that glitch. The same switch without changing driver: "
      "`FD_DEV_FEATURES=enable_tp_ubwc_flag_hint=1`.")
    w("")

    a8 = legs[("a8xx", "android")]["report"] or legs[("a8xx", "wayland")]["report"] or {}
    a8_patch = a8.get("extra_patch") or "patches/a8xx_gen8.patch"
    a8_scripts = [x for x in (a8.get("extra_script") or "patches/a8xx_shared_mem.py").split(":") if x]
    a8_commits = patch_commits(os.path.join(a.workdir, a8_patch))
    t7 = legs[("710-720-test", "android")]["report"] or legs[("710-720-test", "wayland")]["report"] or {}
    t7_scripts = [x for x in (t7.get("extra_script") or "patches/a710-720.py").split(":") if x]

    def link(path):
        return f"[`{os.path.basename(path)}`]({REPO_BLOB.format(repo=a.repo, ref=a.ref, path=path)})"

    w("**🩹 Fixes in every driver** (bugs still in Mesa `main`; every zip carries them, see "
      + link("patches/common/SOURCE") + "):")
    w("")
    k = "patches/common/mesa-44838/"
    w("- **DirectX 12 no longer waits on the GPU every frame** (" + link(k + "0002-tu-kgsl-Prevent-indefinite-wait-times-for-0-timeout-.patch")
      + "). A quick \"is the GPU done yet?\" check was sent to the kernel as \"wait until it's done\", so the CPU "
      "and GPU took turns with VKD3D-Proton. Now it answers at once. On an Adreno 750, a DirectX 12 demo went from "
      "378 to 1422 fps on X11 and from 588 to 3449 fps on Wayland ([report](" + REPO_BLOB.format(repo=a.repo, ref=a.ref,
      path="docs/KGSL_ZERO_TIMEOUT_POLL.md") + ")).")
    w("- **No crash when a frame waits on two kinds of sync at once** (" + link(k + "0010-tu-kgsl-Correctly-merge-timestamps-and-sync-files.patch")
      + "). Cemu crashed on its first frame.")
    w("- **The rest of the KGSL sync clean-up:** wait-any picks the earliest timestamp, reads `poll()` correctly and no "
      "longer crashes on FD-only waits; no out-of-bounds read, timeout overflow or profiling leak; errors are returned "
      "instead of hitting asserts.")
    w("")
    w("All three are Danylo Piliaiev's 13-patch series from Mesa MR "
      "[!44838](https://gitlab.freedesktop.org/mesa/mesa/-/merge_requests/44838), which took our two fixes upstream "
      "and replaced our own patches.")
    w("")
    wn = "patches/a8xx-winnative/"
    w("**🧩 A8xx driver only:** Max's WinNative series (MaxsTechReview, " + link(wn + "0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch")
      + " … " + link(wn + "0006-tu-kgsl-Cache-retired-A8XX-IB-storage.patch") + "). The A6xx / A7xx drivers carry only the fixes above.")
    w("")
    w("- **DirectX 12 Ultimate: mesh shaders + wave32** (0001, 0002). `VK_EXT_mesh_shader` is emulated with compute, "
      "so VKD3D-Proton can offer mesh shaders to games that need them (FINAL FANTASY VII REBIRTH, Alan Wake 2); "
      "render passes with mesh draws run in sysmem.")
    w("- **Four Adreno 8xx GPU hang fixes** (0003-0006): cube-map directions, bindless descriptors, command-stream "
      "memory and its reuse (`TU_KGSL_IB_CACHE=false` turns off the last one).")
    w("")
    w("<details>")
    w("<summary>Build details and checksums</summary>")
    w("")
    w("- **Standard:** Mesa `main` plus the fixes in every driver, no GPU-specific patches, no mesh shaders or wave32.")
    a8_desc = f"whitebelyash's `turnip/gen8` stack ({link(a8_patch)}"
    a8_desc += f", {len(a8_commits)} commits)" if a8_commits else ")"
    if a8_scripts:
        a8_desc += " + " + ", ".join(link(x) for x in a8_scripts)
    w(f"- **A8xx:** {a8_desc}.")
    w(f"- **A710 / A720 / A722:** " + ", ".join(link(x) for x in t7_scripts)
      + " from [Vauzi-17/710](https://github.com/Vauzi-17/710).")
    w("- **8 Gen 2 One UI:** Standard plus " + link("patches/8g2_oneui.py")
      + ": `enable_tp_ubwc_flag_hint` on for the Adreno 740 (Mesa leaves it off to match the older system driver).")
    w("- **Wayland zips:** the same commit and patches, built as Linux-style Vulkan drivers (KGSL, Wayland, bionic) "
      "with Bannerlator's zero-copy patch. CI checks each one before it is attached. They don't load as AdrenoTools "
      "drivers, and the X11 zips don't work as Wayland game drivers.")
    w("- **Linux zips:** the same commit and patches, cross-built against glibc (KGSL, Wayland + X11 WSI) for "
      "Bannerlator's Arch Linux ARM runtime, plus the two KGSL fixes that runtime needs "
      + link("patches/linux/kgsl-drm-node.patch") + " and " + link("patches/linux/kgsl-no-calibrated-timestamps.patch")
      + ". They ship the ICD and its manifest only: the libraries are the runtime's own. CI checks each one.")
    w("")
    w("| File | SHA-256 |")
    w("| :--- | :--- |")
    for d in DRIVERS:
        for platform in PLATFORMS:
            leg = legs[(d["variant"], platform)]
            if leg["ok"]:
                w(f"| `{leg['name']}` | `{leg['report']['sha256']}` |")
    w("")
    w("</details>")

    with open(a.out, "w") as f:
        f.write("\n".join(L) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

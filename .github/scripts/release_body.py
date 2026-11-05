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
        "gpus": "Adreno 840 / 830 / 829 / 825 / 812 / 810: Snapdragon 8 Elite",
    },
    {
        "variant": "710-720-test", "suffix": "-710-720-Test", "label": "A710 / A720 / A722", "kind": "Experimental",
        "gpus": "Adreno 710 / 720 / 722 (unverified on hardware)",
    },
    {
        "variant": "8g2-oneui", "suffix": "-8G2-OneUI", "label": "8 Gen 2 One UI", "kind": "Device-specific",
        "gpus": "Adreno 740: Snapdragon 8 Gen 2 on newer firmware (Samsung One UI)",
    },
    {
        # Named Turnip-<tag>-Banners-AIO: see aio_stem() and the workflow's resolve job.
        "variant": "aio", "suffix": "", "label": "Banners-AIO", "kind": "All SoC",
        "gpus": "Every Adreno: 6xx, 7xx, 710 / 720 / 722, 8xx",
    },
]


def aio_stem(tag, githash_full):
    """Banners-AIO file stem, in the Turnip-<tag>-<variant> pattern the driver catalogs match on."""
    return f"Turnip-{tag}-Banners-AIO"


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
    stem_aio = read_info(a.info, "aio_stem") or aio_stem(tag, githash_full)
    for drv in DRIVERS:
        for platform in PLATFORMS:
            if drv["variant"] == "aio":
                name = f"{stem_aio}{PLATFORM_SUFFIX[platform]}.zip"
            else:
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
        "a8xx": ("**A8xx** (experimental)", "Adreno 810 / 812 / 825 / 829 / 830 / 840 (8 Elite)"),
        "710-720-test": ("**A710 / A720 / A722** (experimental, untested on hardware)", "Adreno 710 / 720 / 722"),
        "8g2-oneui": ("**8 Gen 2 One UI**", "Adreno 740 (8 Gen 2) with UI flicker, e.g. Samsung One UI"),
        "aio": ("**Banners-AIO** (all SoC)", "Every Adreno: 6xx, 7xx, 710 / 720 / 722, 8xx"),
    }
    for d in DRIVERS:
        label, gpus = short[d["variant"]]
        w(f"| {label} | {gpus} | {cell(d['variant'], 'android')} | {cell(d['variant'], 'wayland')} "
          f"| {cell(d['variant'], 'linux')} |")
    w("")
    w("**Which one?**")
    w("- **X11** (Bannerlator, Winlator, BannerHub, any AdrenoTools app): import the normal zip as a GPU driver. "
      "Not sure which driver? Use **Standard**.")
    w("- **Banners-AIO:** one zip for every Adreno. Each GPU family keeps its own changes: the A8xx recipe only on "
      "A8xx chips, the A722 registers only on the A722. Its recipe was tested on an Adreno 830, 750 and 722 before "
      "it joined these builds; each hourly build is still only checked by CI.")
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

    def details(summary, lines):
        w("<details>")
        w(f"<summary>{summary}</summary>")
        w("")
        for line in lines:
            w(line)
        w("")
        w("</details>")
        w("")

    def credit_commits(path):
        return [f"  - {md_cell(subj)} — *{md_cell(auth or 'unknown')}*" for subj, auth in patch_commits(os.path.join(a.workdir, path))]

    wn = "patches/a8xx-winnative/"
    gh_link = lambda who, url: f"[{who}]({url})"  # noqa: E731
    vauzi = gh_link("Vauzi-17/710", "https://github.com/Vauzi-17/710")
    ddrv = gh_link("Droid-Deck/Drivers", "https://github.com/Droid-Deck/Drivers")
    wnrepo = gh_link("WinNative-Emu/Drivers", "https://github.com/WinNative-Emu/Drivers")
    mr = "[MR 44838](https://gitlab.freedesktop.org/mesa/mesa/-/merge_requests/44838)"

    w("### What's in each driver")
    w("")
    w("Tap a driver to see which GPUs it is for, what it changes on top of Mesa, where each change came from "
      "and who wrote it.")
    w("")
    details("<b>Every driver</b>: what all five share", [
        f"- **Base:** Mesa `main` at [`{info['githash']}`]({mesa_url}) ({info['commit_date']}), built for KGSL.",
        "- **DirectX 12 no longer waits on the GPU every frame.** A quick \"is the GPU done yet?\" check was sent "
        "to the kernel as \"wait until it's done\", so the CPU and GPU took turns with VKD3D-Proton. On an Adreno 750 "
        "a DirectX 12 demo went from 378 to 1422 fps on X11 and from 588 to 3449 fps on Wayland ([report]("
        + REPO_BLOB.format(repo=a.repo, ref=a.ref, path="docs/KGSL_ZERO_TIMEOUT_POLL.md") + ")). Found here "
        f"(The412Banner); fixed in Mesa by Danylo Piliaiev, {mr} (2026-10-08).",
        "- **No crash when a frame waits on two kinds of sync at once** (Cemu crashed on its first frame; RPCS3 and "
        "Dolphin checked too). First fixed in DroidDeck's driver; fixed in Mesa by Danylo Piliaiev (`1da50a1b`, "
        f"{mr}). See " + link("patches/common/SOURCE") + ".",
        "- **Game entries** (" + link("patches/common/apply_common.sh") + ", not in Mesa yet): MIO: Memories in Orbit "
        "and UNCHARTED: Legacy of Thieves Collection turn on `tu_enable_ssbo_emulation` on Adreno 7xx, so their large "
        "storage buffers work ([MIO report](" + REPO_BLOB.format(repo=a.repo, ref=a.ref, path="docs/MIO_A7XX_SSBO_LIMIT.md")
        + ")). The option itself is Mesa's, by Job Noorman. With other Turnip builds from after 2026-06-10, set "
        "`tu_enable_ssbo_emulation=true` yourself.",
    ])
    details("<b>Standard</b>: Adreno 6xx / 7xx (8 Gen 3 and older)", [
        "- Mesa `main` plus **Every driver** above. No GPU-specific patches, no mesh shaders, no wave32.",
        "- Credit: the Mesa / Freedreno developers.",
    ])
    a8_lines = [
        "- **For:** Adreno 810 / 812 / 825 / 829 / 830 / 840 (Snapdragon 8 Elite). Experimental.",
        f"- {link(a8_patch)}: whitebelyash's `turnip/gen8` stack ([mesa-unified](https://github.com/whitebelyash/mesa-unified)): "
        "A8xx GPU entries, UBWC gralloc detection, the `disable_gmem` property, the Steam Deck spoof "
        "(`TU_DEBUG=deck_emu`), A810 / A812 fixes. Commits and authors:",
    ] + credit_commits(a8_patch)
    if "patches/a8xx_shared_mem.py" in a8_scripts:
        a8_lines.append("- " + link("patches/a8xx_shared_mem.py") + ": compute shared memory 32 → 64 KiB on every "
                        "entry (whitebelyash, `dcbb41b2`). Known: Vulkan conformance tests above 32 KiB fail on an "
                        "Adreno 830; Banners-AIO keeps 32 KiB.")
    else:
        a8_lines += [f"- {link(x)}" for x in a8_scripts]
    a8_lines += [
        "- **Max's WinNative series** (Max / MaxsTechReview, " + wnrepo + ", GPL-3.0), A8xx only: "
        + link(wn + "0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch") + " mesh shaders emulated with compute and "
        + link(wn + "0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch") + " wave32 (DirectX 12 Ultimate "
        "games such as FINAL FANTASY VII REBIRTH and Alan Wake 2); "
        + link(wn + "0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch") + ", "
        + link(wn + "0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch") + ", "
        + link(wn + "0005-tu-kgsl-Fetch-A8XX-command-streams-through-a-virtual.patch")
        + " three GPU hang fixes. His IB cache (0006) is left out: it broke the Linux driver on some Adreno 840s.",
        "- Plus **Every driver** above. Tips: `TU_DEBUG=sysmem` if an A830 looks glitchy, `TU_DEBUG=deck_emu` if a "
        "game won't start.",
    ]
    details("<b>A8xx</b>: Adreno 8xx (Snapdragon 8 Elite)", a8_lines)
    t7_patch = t7.get("extra_patch") or "patches/710-720/01-u_gralloc-always-use-ubwc-detection.patch"
    details("<b>A710 / A720 / A722</b>: Adreno 710 / 720 / 722", [
        "- A710 and A720 come from Mesa `main` itself (upstream since September 2026).",
        "- " + ", ".join(link(x) for x in t7_scripts) + ": swaps Mesa's A730-based A722 entry for " + vauzi
        + "'s registers captured on real A722 hardware (`num_ccu = 2`). Credit: Vauzi-17.",
        "- " + link(t7_patch) + ": UBWC gralloc fix (whitebelyash), as shipped in " + vauzi + "'s releases.",
        "- Plus **Every driver** above. Tips: `TU_DEBUG=sysmem`; in Winlator also `WRAPPER_BLIT=1`.",
    ])
    details("<b>8 Gen 2 One UI</b>: Adreno 740 on newer firmware", [
        "- Standard plus " + link("patches/8g2_oneui.py") + " (Banners-Turnip): turns on "
        "`enable_tp_ubwc_flag_hint` for the Adreno 740, to match newer system drivers such as Samsung One UI. Mesa "
        "leaves it off to match the older system driver.",
        "- Only if the Standard driver makes the phone's UI glitch or flicker; on other 8 Gen 2 devices it causes "
        "that glitch. Same switch without changing driver: `FD_DEV_FEATURES=enable_tp_ubwc_flag_hint=1`.",
    ])
    details("<b>Banners-AIO</b>: every Adreno, one driver", [
        "- One `libvulkan_freedreno.so` for every Adreno; Turnip picks each GPU's settings by chip ID. "
        + link("patches/one/one_gpu_gates.py") + " (Banners-Turnip) keeps the A8xx-wide changes on A8xx chips, so "
        "every other GPU behaves as in its own driver here. Compute shared memory is 32 KiB on every GPU.",
        "- **Every GPU:** **Every driver** above, plus from " + ddrv + " (copied unchanged, with permission): "
        "render-pass barrier flushes kept (UE5 Nanite) and 32-bit SSBO offset wrap (*K11MCH1*); memory budget "
        "counts the whole process (*Charles DuBose*).",
        "- **Every GPU on Android:** IMapper5 gralloc backend and UBWC-compressed swapchain buffers (*Leb-Sun*, "
        + ddrv + ").",
        "- **A6xx / A7xx:** as Standard plus the above.",
        "- **A710 / A720 / A722 / A725 / A730:** early preamble and scalar predicates off (*DroidDeck*, " + ddrv + ").",
        "- **A722:** " + vauzi + "'s registers (*Vauzi-17*) and GMEM off (GMEM gives CCU write page faults on the "
        "A722 in every Turnip build).",
        "- **A8xx:** whitebelyash's `turnip/gen8` stack and Max's WinNative 0001-0005 as in the A8xx driver (without "
        "the 64 KiB script); LRZ controls reset after the end-of-pass flush (*Gustash*); buffer descriptors of 1 GiB "
        "and more keep their size (*airidosas252*, now also in Mesa); RB_RESOLVE_CR_CNTL and LRZ "
        "color mask as the Qualcomm driver (*adapted from " + vauzi + "*); extra chip IDs for the A829, A845 and "
        "A850, and no category-4 repeat on the A845 / A850 (*misakayuuki*); GMEM off on the A810 and A829.",
        "- Sources: " + link("patches/one/one_fixes.py") + " and " + link("patches/one/dd/SOURCE.md") + ". Its recipe "
        "was tested on an Adreno 830, 750 and 722 before it joined these builds.",
    ])
    w("<details>")
    w("<summary>Build details and checksums</summary>")
    w("")
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

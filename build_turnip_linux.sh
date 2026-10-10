#!/bin/bash
# Linux legs of "Build Turnip (Combined)": the same Turnip driver as the Android and Wayland legs
# -- same Mesa commit, same EXTRA_PATCH / EXTRA_SCRIPT -- built for GLIBC, as the Vulkan ICD for
# Bannerlator's Linux runtime (the Arch Linux ARM rootfs that runs gamescope and Valve's native
# ARM64 Steam client).
#
# This is the driver that DRAWS on that path: the Steam client's own menus (OpenGL -> Zink ->
# Vulkan) and every game the client launches (D3D -> DXVK/VKD3D -> Vulkan) go through it, and so
# does gamescope's compositing. It is a glibc shared object: neither of the other two builds can
# be loaded by those processes at all, because they are bionic. Putting the finished frame on the
# screen is still the Android (AdrenoTools) driver's job, in the app's compositor.
#
# Built against a sysroot assembled from the same Arch Linux ARM packages the runtime itself is
# built from, so the libdrm / wayland / libxcb it links against are the ones present on the device.
# No libraries are shipped in the zip for that reason - only the ICD.
#
# Fail-hard: any download, patch, script or check that goes wrong exits non-zero before a zip
# exists. The other legs of the same driver are different jobs and are not affected.
#
# Environment:
#   MESA_COMMIT      40-hex Mesa commit (the one every leg of the run builds)          required
#   ZIP_NAME         output zip file name                                              required
#   META_NAME        meta.json "name"                                                  required
#   PACKAGE_VERSION  meta.json "packageVersion"                                        default 1
#   META_DESC        the Android leg's description for this driver ("" = standard)
#   EXTRA_PATCH      patch series, as build_turnip.sh
#   EXTRA_SCRIPT     colon-separated Python scripts, as build_turnip.sh
#   VARIANT          label for logs and the build report
#   KEEP_SYMBOLS     1 = optimised build with debug info, not stripped (a driver gdb can name
#                    functions in; for tracking a crash, never for a release)
# Output: linux_workdir/$ZIP_NAME and linux_workdir/build-report.json
#
# Needs: aarch64-linux-gnu-gcc/g++, meson >= 1.5, ninja, python3 (mako, pyyaml, packaging),
#        glslang-tools, curl, tar with zstd, zip, patch, bison, flex, cmake.

set -eo pipefail

green='\033[0;32m'
red='\033[0;31m'
nocolor='\033[0m'
die(){ echo -e "${red}[linux ${VARIANT:-?}] $*${nocolor}" >&2; exit 1; }
log(){ echo -e "${green}[linux ${VARIANT:-?}]${nocolor} $*"; }

repo="$(cd "$(dirname "$0")" && pwd)"
workdir="$(pwd)/linux_workdir"
sysroot="$workdir/sysroot"
mesa="$workdir/mesa"
stage="$workdir/stage"
hosttools="$workdir/host"
lx_patches="$repo/patches/linux"

# The runtime's own package source (tools/linuxfs/build-linuxfs.sh). Same mirror, same repos.
mirror="http://mirror.archlinuxarm.org/aarch64"
# What Turnip links against, plus the toolchain's target libc and headers. Dependencies are
# resolved from the repository databases, so this list is only what the build asks for by name.
sysroot_seeds="glibc linux-api-headers libdrm wayland wayland-protocols libxcb libx11 libxshmfence
  libxext libxfixes libxrandr zlib zstd expat gcc-libs"
# wayland-scanner runs on the BUILD machine and must be at least as new as the wayland-protocols
# in the sysroot; distributions lag it (Ubuntu 24.04 ships 1.22), so build the scanner alone.
wl_version="1.26.0"
wl_sha256="64176eaa46e4969903e286f8e5ef8331affc17fdf03ac9b58381d2b23162b7a3"

[[ "$MESA_COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "MESA_COMMIT must be a 40-hex commit, got '${MESA_COMMIT}'"
[ -n "$ZIP_NAME" ] || die "ZIP_NAME is required"
[ -n "$META_NAME" ] || die "META_NAME is required"
PACKAGE_VERSION="${PACKAGE_VERSION:-1}"

fetch(){	# <url> <out>
	curl -fsSL --retry 6 --retry-delay 10 --retry-all-errors "$1" -o "$2" || die "download failed: $1"
}

# --- the sysroot: Arch Linux ARM aarch64 packages, dependency closure over the repo databases ---
build_sysroot(){
	mkdir -p "$workdir/db" "$workdir/pkgs" && cd "$workdir"
	log "fetching Arch Linux ARM package databases"
	local repo_name
	for repo_name in core extra alarm; do
		fetch "$mirror/$repo_name/$repo_name.db" "db/$repo_name.db"
		rm -rf "db/x_$repo_name" && mkdir -p "db/x_$repo_name"
		tar -xzf "db/$repo_name.db" -C "db/x_$repo_name" || die "$repo_name.db is not a package database"
	done

	# %DEPENDS% lives in a separate `depends` file and several names are virtual (%PROVIDES%).
	python3 - $sysroot_seeds > pkglist.txt <<'PY' || die "package closure failed"
import os, sys, collections
pkgs, provides = {}, collections.defaultdict(list)
def strip(d):
    for op in (">=", "<=", "==", ">", "<", "="):
        if op in d: return d.split(op)[0]
    return d
for repo in ("core", "extra", "alarm"):
    base = os.path.join("db", "x_" + repo)
    for entry in os.listdir(base):
        fields, key = {}, None
        for name in ("desc", "depends"):
            path = os.path.join(base, entry, name)
            if not os.path.exists(path): continue
            for line in open(path, encoding="utf-8", errors="replace"):
                line = line.rstrip("\n")
                if line.startswith("%") and line.endswith("%"): key = line.strip("%"); fields[key] = []
                elif line == "": key = None
                elif key: fields[key].append(line)
        n = fields.get("NAME", [None])[0]
        if not n: continue
        pkgs[n] = {"repo": repo, "file": fields["FILENAME"][0],
                   "depends": [strip(d) for d in fields.get("DEPENDS", [])],
                   "provides": [strip(p) for p in fields.get("PROVIDES", [])]}
        provides[n].append(n)
        for p in pkgs[n]["provides"]: provides[p].append(n)
seen, queue, missing = set(), list(sys.argv[1:]), []
while queue:
    want = queue.pop()
    real = want if want in pkgs else (provides.get(want) or [None])[0]
    if real is None: missing.append(want); continue
    if real in seen: continue
    seen.add(real)
    queue.extend(pkgs[real]["depends"])
if missing: sys.exit("unresolved: " + " ".join(missing))
for n in sorted(seen): print(pkgs[n]["repo"] + "/" + pkgs[n]["file"])
PY
	log "$(wc -l < pkglist.txt) packages in the sysroot closure"

	rm -rf "$sysroot" && mkdir -p "$sysroot"
	: > "$workdir/sysroot-packages.txt"
	local entry file
	while read -r entry; do
		file="${entry#*/}"
		# A mirror error page is not a package; check before extracting, not after.
		if ! tar -tf "pkgs/$file" >/dev/null 2>&1; then
			rm -f "pkgs/$file"
			fetch "$mirror/$entry" "pkgs/$file"
			tar -tf "pkgs/$file" >/dev/null || die "$file is not a package"
		fi
		tar -xf "pkgs/$file" -C "$sysroot" --no-same-owner --no-same-permissions \
			--exclude=.PKGINFO --exclude=.MTREE --exclude=.INSTALL --exclude=.BUILDINFO --exclude=.CHANGELOG \
			|| die "cannot unpack $file"
		echo "$file" >> "$workdir/sysroot-packages.txt"
	done < pkglist.txt
	chmod -R u+rwX "$sysroot"

	# glibc pulls in `filesystem`, so /lib -> /usr/lib is there and the linker script inside
	# libc.so (which names absolute /usr/lib paths, resolved against --sysroot) works. Assert what
	# the build actually opens rather than trust the closure: a mirror that moved a library into
	# another package would otherwise fail 20 minutes later inside meson.
	for f in usr/lib/libc.so.6 usr/lib/libdrm.so usr/lib/libwayland-client.so usr/lib/libxcb.so \
	         usr/lib/pkgconfig/libdrm.pc usr/lib/pkgconfig/wayland-client.pc usr/lib/pkgconfig/xcb.pc \
	         usr/share/pkgconfig/wayland-protocols.pc usr/include/xf86drm.h; do
		[ -e "$sysroot/$f" ] || die "sysroot is missing $f"
	done
	log "sysroot glibc: $(basename "$(readlink -f "$sysroot/usr/lib/libc.so.6")")"
}

# --- host wayland-scanner, built from the pinned release (seconds; no libraries, no docs) ---
build_host_scanner(){
	cd "$workdir"
	fetch "https://gitlab.freedesktop.org/wayland/wayland/-/releases/$wl_version/downloads/wayland-$wl_version.tar.xz" "wayland-$wl_version.tar.xz"
	echo "$wl_sha256  wayland-$wl_version.tar.xz" | sha256sum -c --quiet || die "wayland-$wl_version.tar.xz checksum mismatch"
	rm -rf "wayland-$wl_version" wayland-build && tar -xJf "wayland-$wl_version.tar.xz"
	meson setup wayland-build "wayland-$wl_version" --prefix "$hosttools" --libdir lib --buildtype release \
		-Dlibraries=false -Dscanner=true -Dtests=false -Ddocumentation=false -Ddtd_validation=false \
		|| die "host wayland-scanner: meson setup failed"
	ninja -C wayland-build install || die "host wayland-scanner: build failed"
	[ -x "$hosttools/bin/wayland-scanner" ] || die "host wayland-scanner was not installed"
	"$hosttools/bin/wayland-scanner" --version
}

fetch_mesa(){
	cd "$workdir"
	log "fetching Mesa $MESA_COMMIT"
	rm -rf "$mesa"
	git init -q "$mesa"
	git -C "$mesa" remote add origin https://gitlab.freedesktop.org/mesa/mesa.git
	local ok=0 i
	for i in 1 2 3 4; do
		if git -C "$mesa" fetch -q --depth=1 origin "$MESA_COMMIT"; then ok=1; break; fi
		echo "Mesa fetch attempt $i failed, retrying in 30 s"; sleep 30
	done
	[ "$ok" = 1 ] || die "could not fetch Mesa $MESA_COMMIT"
	git -C "$mesa" checkout -q FETCH_HEAD
	[ "$(git -C "$mesa" rev-parse HEAD)" = "$MESA_COMMIT" ] || die "Mesa checkout is not $MESA_COMMIT"
}

# The KGSL fixes the Linux runtime needs; both are device-proven there (patches/linux/SOURCE).
# None of the Wayland leg's bionic work applies here: glibc has pthread_cancel, Mesa's own Linux
# detection is already right, and the zero-copy AHardwareBuffer layer is Android-only.
apply_linux_patches(){
	cd "$mesa"
	local p out rc
	for p in "$lx_patches/kgsl-drm-node.patch" "$lx_patches/kgsl-no-calibrated-timestamps.patch"; do
		[ -f "$p" ] || die "missing $p"
		log "applying $(basename "$p")"
		rc=0
		out="$(patch -p1 -N --fuzz=3 --no-backup-if-mismatch < "$p" 2>&1)" || rc=$?
		echo "$out" | sed 's/^/    /'
		[ "$rc" = 0 ] || die "$(basename "$p") did not apply cleanly (patch exit $rc) - it needs rebasing onto this Mesa"
		[ -z "$(git status --porcelain --untracked-files=all | grep -E '\.(rej|orig)$' || true)" ] \
			|| die "$(basename "$p") left .rej/.orig files"
	done
	# Assert the result rather than trust the patch: the whole point of both is these three lines.
	grep -q "local_major = device->master_major" src/freedreno/vulkan/tu_knl_kgsl.cc \
		|| die "kgsl-drm-node did not reach tu_knl_kgsl.cc"
	grep -q "bool has_calibrated_timestamps" src/freedreno/vulkan/tu_device.cc \
		|| die "kgsl-no-calibrated-timestamps did not reach tu_device.cc"
	grep -q "kgsl_device_get_gpu_timestamp" src/freedreno/vulkan/tu_knl_kgsl.cc \
		&& die "kgsl_device_get_gpu_timestamp is still in tu_knl_kgsl.cc"

	# Termux 0014, as the Wayland leg does it: the KGSL timestamp wait must not assert on an
	# unexpected errno. The kernel is the same Android kernel on this path. Mesa does this itself
	# since MR 44838 (2026-10-08); the rewrite is kept for an older Mesa and skipped otherwise.
	kgsl_assert="$(python3 - <<'PY'
p = 'src/freedreno/vulkan/tu_knl_kgsl.cc'
s = open(p).read()
old = """      } else if (ret == -1) {
         assert(errno == ETIMEDOUT);
         return VK_TIMEOUT;"""
new = """      } else if (ret == -1) {
         if (errno != ETIMEDOUT)
            mesa_logw("wait_timestamp_safe: errno %d (%s)", errno, strerror(errno));
         return VK_TIMEOUT;"""
if old in s:
    open(p, 'w').write(s.replace(old, new, 1))
    print('applied')
elif 'kgsl_timestamp_error(' in s:
    # Mesa MR 44838 (b7ad24ad, 2026-10-08) removed the assert: every errno now goes through
    # kgsl_timestamp_error(), which logs it and returns VK_TIMEOUT / device lost.
    print('upstream')
else:
    print('not-found')
PY
)"
	log "KGSL timestamp-wait assert -> warning: $kgsl_assert"
	[ "$kgsl_assert" != not-found ] || die "the KGSL timestamp wait has neither the assert nor upstream's kgsl_timestamp_error(): look at wait_timestamp_safe()"
	# KGSL fixes every leg ships (patches/common/SOURCE).
	bash "$repo/patches/common/apply_common.sh" . || die "patches/common did not apply"

	git -c user.name=banners-turnip -c user.email=build@banners-turnip commit -q -am "Linux build: KGSL patches"
	git tag -f banner-linux >/dev/null
}

# The driver's own recipe, from the same EXTRA_PATCH / EXTRA_SCRIPT as its Android leg and in the
# same order. build_turnip.sh tolerates rejected hunks and missing scripts; here either one fails.
apply_recipe(){
	cd "$mesa"
	patch_fuzz_hunks=0
	if [ -n "$EXTRA_PATCH" ]; then
		[ -f "$repo/$EXTRA_PATCH" ] || die "EXTRA_PATCH $EXTRA_PATCH does not exist"
		log "applying $EXTRA_PATCH (patch -p1 -N --fuzz=4, as build_turnip.sh; any reject fails)"
		local out rc=0
		out="$(patch -p1 -N --fuzz=4 --no-backup-if-mismatch < "$repo/$EXTRA_PATCH" 2>&1)" || rc=$?
		echo "$out" | sed 's/^/    /'
		[ "$rc" = 0 ] || die "$EXTRA_PATCH did not apply cleanly (patch exit $rc)"
		[ -z "$(git status --porcelain --untracked-files=all | grep -E '\.(rej|orig)$' || true)" ] \
			|| die "$EXTRA_PATCH left .rej/.orig files"
		patch_fuzz_hunks="$(echo "$out" | grep -c 'with fuzz' || true)"
		[ "$patch_fuzz_hunks" = 0 ] || echo "    note: $patch_fuzz_hunks hunk(s) applied with fuzz (same as the Android leg would)"
	fi
	python3 -c "compile(open('src/freedreno/common/freedreno_devices.py').read(),'f','exec')" \
		|| die "freedreno_devices.py does not parse after the patch series"

	if [ -n "$EXTRA_SCRIPT" ]; then
		local scripts s before after
		IFS=':' read -ra scripts <<< "$EXTRA_SCRIPT"
		for s in "${scripts[@]}"; do
			[ -f "$repo/$s" ] || die "EXTRA_SCRIPT $s does not exist"
			before="$(git diff | sha256sum)"
			log "running $s"
			python3 "$repo/$s" 2>&1 | sed 's/^/    /' || die "$s failed"
			after="$(git diff | sha256sum)"
			[ "$after" != "$before" ] || die "$s changed nothing"
		done
		python3 -c "compile(open('src/freedreno/common/freedreno_devices.py').read(),'f','exec')" \
			|| die "freedreno_devices.py does not parse after the scripts"
	fi

	echo "[linux ${VARIANT}] recipe changes on top of the Linux patches:"
	git --no-pager diff --stat banner-linux
}

build(){
	cd "$mesa"
	local cross="$workdir/cross.ini" native="$workdir/native.ini"
	cat > "$cross" <<EOF
[binaries]
c = 'aarch64-linux-gnu-gcc'
cpp = 'aarch64-linux-gnu-g++'
ar = 'aarch64-linux-gnu-ar'
strip = 'aarch64-linux-gnu-strip'
pkg-config = 'pkg-config'

[properties]
sys_root = '$sysroot'
pkg_config_libdir = '$sysroot/usr/lib/pkgconfig:$sysroot/usr/share/pkgconfig'

[built-in options]
c_args = ['--sysroot=$sysroot']
cpp_args = ['--sysroot=$sysroot']
c_link_args = ['--sysroot=$sysroot', '-L$sysroot/usr/lib']
cpp_link_args = ['--sysroot=$sysroot', '-L$sysroot/usr/lib']

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
EOF
	# Programs Mesa runs on the BUILD machine. Without the explicit wayland-scanner it asks the
	# sysroot's pkg-config and gets the aarch64 binary, which this machine cannot execute.
	cat > "$native" <<EOF
[binaries]
c = 'gcc'
cpp = 'g++'
pkg-config = '/usr/bin/pkg-config'
cmake = '/usr/bin/cmake'
wayland-scanner = '$hosttools/bin/wayland-scanner'
glslangValidator = '$(command -v glslangValidator)'

[built-in options]
pkg_config_path = '$hosttools/lib/pkgconfig'
EOF
	# freedreno-kmds MUST list msm as well as kgsl: with kgsl alone meson drops libdrm and
	# wsi_common_drm.c, and vkCreateSwapchainKHR walks into a compiled-out branch.
	# The driconf defaults (vkd3d/DXVK workarounds, per-game options) are compiled in with xmlconfig off, as the Android and Wayland legs have them.
	# With it on, the driver read them from the runtime's /usr/share/drirc.d, which is whatever Mesa the rootfs ships, or nothing at all.
	# Only the Vulkan ICD is built: the runtime's own Mesa supplies Zink, EGL and GL, and the
	# client's OpenGL reaches this driver through that Zink.
	local buildtype=release
	[ -n "$KEEP_SYMBOLS" ] && buildtype=debugoptimized
	rm -rf build-linux
	meson setup build-linux \
		--cross-file "$cross" \
		--native-file "$native" \
		--prefix /usr \
		--libdir lib \
		--buildtype "$buildtype" \
		-Dvulkan-drivers=freedreno \
		-Dfreedreno-kmds=msm,kgsl \
		-Dgallium-drivers= \
		-Dplatforms=wayland,x11 \
		-Dopengl=false \
		-Dgbm=disabled \
		-Dglx=disabled \
		-Degl=disabled \
		-Dllvm=disabled \
		-Dvulkan-layers= \
		-Dtools= \
		-Dxmlconfig=disabled \
		|| { echo "== meson log =="; tail -80 build-linux/meson-logs/meson-log.txt 2>/dev/null; die "meson setup failed"; }
	ninja -C build-linux src/freedreno/vulkan/libvulkan_freedreno.so || die "build failed"
	[ -f build-linux/src/freedreno/vulkan/libvulkan_freedreno.so ] || die "libvulkan_freedreno.so was not built"
}

package(){
	cd "$mesa"
	local githash version vk_patch vk_minor driver_version desc glibc_min
	githash="$(git rev-parse --short "$MESA_COMMIT")"
	version="$(sed 's/-devel.*//' VERSION | tr -d '[:space:]')"
	vk_patch=$(grep '^#define VK_HEADER_VERSION ' include/vulkan/vulkan_core.h | awk '{print $3}')
	vk_minor=$(grep 'define TU_API_VERSION' src/freedreno/vulkan/tu_device.cc | grep -oP 'VK_MAKE_VERSION\(\s*[0-9]+,\s*\K[0-9]+')
	[ -n "$vk_patch" ] && [ -n "$vk_minor" ] || die "cannot read the Vulkan version from the tree"
	driver_version="Vulkan 1.${vk_minor}.${vk_patch}"

	if [ -n "$META_DESC" ]; then desc="$META_DESC"
	else desc="A6xx/A7xx Turnip driver from Mesa main (git ${githash}). KGSL build."; fi
	desc="Linux build: ${desc} glibc Vulkan ICD (KGSL, Wayland + X11 WSI) for Bannerlator's Linux runtime - it draws the native Steam client and the games it launches. Not an AdrenoTools driver and not for Wine containers."

	rm -rf "$stage" && mkdir -p "$stage"
	if [ -n "$KEEP_SYMBOLS" ]; then
		log "KEEP_SYMBOLS: shipping the unstripped driver (debug build)"
		cp build-linux/src/freedreno/vulkan/libvulkan_freedreno.so "$stage/libvulkan_freedreno.so" || die "copy failed"
	else
		aarch64-linux-gnu-strip -o "$stage/libvulkan_freedreno.so" \
			build-linux/src/freedreno/vulkan/libvulkan_freedreno.so || die "strip failed"
	fi

	# The highest glibc symbol version the driver asks for: the rootfs must be at least this.
	glibc_min="$(aarch64-linux-gnu-readelf -V -W "$stage/libvulkan_freedreno.so" \
		| grep -oP 'GLIBC_\K[0-9]+\.[0-9]+(\.[0-9]+)?' | sort -uV | tail -1)"
	[ -n "$glibc_min" ] || die "the driver has no GLIBC_ version references - is it really a glibc build?"
	log "minimum glibc: $glibc_min"

	# The ICD manifest the Khronos loader reads, pointing at the driver beside it. api_version is
	# the loader's own interface version, not the driver's.
	cat > "$stage/freedreno_icd.aarch64.json" <<EOF
{
    "ICD": {
        "api_version": "1.1.274",
        "library_path": "./libvulkan_freedreno.so"
    },
    "file_format_version": "1.0.0"
}
EOF

	STAGE="$stage" M_NAME="$META_NAME" M_DESC="$desc" M_PKGVER="$PACKAGE_VERSION" M_DRV="$driver_version" \
	M_GLIBC="$glibc_min" python3 - <<'PY'
import json, os
meta = {
    "schemaVersion": 1,
    "name": os.environ["M_NAME"],
    "description": os.environ["M_DESC"],
    "author": "The412Banner",
    "packageVersion": os.environ["M_PKGVER"],
    "vendor": "Mesa",
    "driverVersion": os.environ["M_DRV"],
    "libc": "glibc",
    "minGlibc": os.environ["M_GLIBC"],
    # Where it goes inside the Linux runtime, replacing the rootfs's own Turnip.
    "installPath": "usr/lib/libvulkan_freedreno.so",
    # No "libraryName" and no "minApi": an AdrenoTools importer that took this zip by mistake
    # would hand a glibc object to the Android loader.
    "kind": "linux-vulkan-icd",
}
with open(os.path.join(os.environ["STAGE"], "meta.json"), "w") as f:
    json.dump(meta, f, indent=2)
    f.write("\n")
print(json.dumps(meta, indent=2))
PY
	rm -f "$workdir/$ZIP_NAME"
	(cd "$stage" && zip -q -X "$workdir/$ZIP_NAME" libvulkan_freedreno.so freedreno_icd.aarch64.json meta.json) \
		|| die "zip failed"

	# Facts the release body is written from (verify_driver_zip.py adds the checks).
	R_OUT="$workdir/build-report.json" R_PKGS="$workdir/sysroot-packages.txt" R_KGSL="$kgsl_assert" \
	R_FUZZ="$patch_fuzz_hunks" R_VERSION="$version" R_DRV="$driver_version" R_GLIBC="$glibc_min" \
	R_WL="$wl_version" R_CC="$(aarch64-linux-gnu-gcc -dumpversion)" \
	R_LXSRC="$(cat "$lx_patches/SOURCE" 2>/dev/null | head -1 || echo unknown)" python3 - <<'PY'
import json, os, re
pkgs = {}
for line in open(os.environ["R_PKGS"]):
    m = re.match(r"^(.*)-([^-]+-[^-]+)-(aarch64|any)\.pkg\.tar\.[a-z]+$", line.strip())
    if m:
        pkgs[m.group(1)] = m.group(2)
report = {
    "platform": "linux",
    "variant": os.environ.get("VARIANT", ""),
    "mesa_commit": os.environ["MESA_COMMIT"],
    "mesa_version": os.environ["R_VERSION"],
    "driver_version": os.environ["R_DRV"],
    "extra_patch": os.environ.get("EXTRA_PATCH", ""),
    "extra_script": os.environ.get("EXTRA_SCRIPT", ""),
    "patch_fuzz_hunks": int(os.environ.get("R_FUZZ") or 0),
    "libc": "glibc",
    "min_glibc": os.environ["R_GLIBC"],
    "cross_gcc": os.environ["R_CC"],
    "host_wayland_scanner": os.environ["R_WL"],
    "sysroot_packages": len(pkgs),
    "sysroot": {k: pkgs[k] for k in ("glibc", "libdrm", "wayland", "libxcb") if k in pkgs},
    "linux_patches": {
        "kgsl_drm_node": "applied",
        "kgsl_no_calibrated_timestamps": "applied",
        "kgsl_wait_assert": os.environ["R_KGSL"],
        "source": os.environ["R_LXSRC"],
    },
}
json.dump(report, open(os.environ["R_OUT"], "w"), indent=2)
print(json.dumps(report, indent=2))
PY
	log "built $workdir/$ZIP_NAME"
}

mkdir -p "$workdir"
build_sysroot
build_host_scanner
fetch_mesa
apply_linux_patches
apply_recipe
build
package

#!/bin/bash
# Wayland legs of "Build Turnip (Combined)": the same Turnip driver as one Android leg
# (build_turnip.sh) -- same Mesa commit, same EXTRA_PATCH / EXTRA_SCRIPT -- built the way the
# working drivers in Bannerlator's Wayland Proton layer are built (branch `wayland`,
# build_wayland.sh): a Linux-style Turnip on bionic (KGSL backend, Wayland WSI, NDK r29 at API 29,
# linked against Termux's libwayland-client and libdrm) that the Khronos Vulkan loader inside the
# Wine container loads as an ICD.
#
# It is NOT an AdrenoTools driver, and it is a separate build on purpose: an Android-platform
# Turnip with the Wayland WSI added (run 34713704642, 2026-09-12) loads through AdrenoTools but
# fails inside the container with VK_ERROR_INCOMPATIBLE_DRIVER.
#
# Fail-hard: any download, patch, script or check that goes wrong exits non-zero before a zip
# exists. The Android leg of the same driver is a different job and is not affected.
#
# Environment:
#   MESA_COMMIT      40-hex Mesa commit (the one every leg of the run builds)          required
#   ZIP_NAME         output zip file name                                               required
#   META_NAME        meta.json "name"                                                   required
#   PACKAGE_VERSION  meta.json "packageVersion"                                         default 1
#   META_DESC        the Android leg's description for this driver ("" = standard)
#   EXTRA_PATCH      patch series, as build_turnip.sh
#   EXTRA_SCRIPT     colon-separated Python scripts, as build_turnip.sh
#   VARIANT          label for logs and the build report
# Output: wayland_workdir/$ZIP_NAME and wayland_workdir/build-report.json

set -eo pipefail

green='\033[0;32m'
red='\033[0;31m'
nocolor='\033[0m'
die(){ echo -e "${red}[wayland ${VARIANT:-?}] $*${nocolor}" >&2; exit 1; }
log(){ echo -e "${green}[wayland ${VARIANT:-?}]${nocolor} $*"; }

repo="$(cd "$(dirname "$0")" && pwd)"
workdir="$(pwd)/wayland_workdir"
ndkver="android-ndk-r29"
ndk="$workdir/$ndkver/toolchains/llvm/prebuilt/linux-x86_64/bin"
api=29   # reallocarray and ELF TLS (build_wayland.sh)
termux_repo="https://packages-cf.termux.dev/apt/termux-main"
termux_pkgs="libwayland libwayland-protocols libdrm libffi"
termux_host_pkgs="libwayland-cross-scanner"   # wayland-scanner of exactly the libwayland version
sysroot="$workdir/termux"
tprefix="$sysroot/data/data/com.termux/files/usr"
mesa="$workdir/mesa"
stage="$workdir/stage"
wl_patches="$repo/patches/wayland"

[[ "$MESA_COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "MESA_COMMIT must be a 40-hex commit, got '${MESA_COMMIT}'"
[ -n "$ZIP_NAME" ] || die "ZIP_NAME is required"
[ -n "$META_NAME" ] || die "META_NAME is required"
PACKAGE_VERSION="${PACKAGE_VERSION:-1}"

fetch(){	# <url> <out>
	curl -fsSL --retry 5 --retry-delay 10 --retry-all-errors "$1" -o "$2" || die "download failed: $1"
}

prepare(){
	mkdir -p "$workdir" && cd "$workdir"

	log "downloading $ndkver"
	fetch "https://dl.google.com/android/repository/$ndkver-linux.zip" ndk.zip
	unzip -q ndk.zip && rm ndk.zip
	[ -x "$ndk/aarch64-linux-android$api-clang" ] || die "NDK clang for API $api missing"

	# Termux bionic aarch64 packages for what Mesa links against. Resolve the current file names
	# from the index: Termux drops old versions from the pool.
	log "fetching Termux packages: $termux_pkgs $termux_host_pkgs"
	fetch "$termux_repo/dists/stable/main/binary-aarch64/Packages" Packages
	rm -rf "$sysroot" debs && mkdir -p "$sysroot" debs
	: > termux-versions.txt
	for p in $termux_pkgs $termux_host_pkgs; do
		read -r fn ver < <(awk -v P="$p" 'BEGIN{RS="";FS="\n"} {n="";f="";v=""; for(i=1;i<=NF;i++){if($i~/^Package: /)n=substr($i,10); if($i~/^Filename: /)f=substr($i,11); if($i~/^Version: /)v=substr($i,10)} if(n==P){print f, v; exit}}' Packages) || true
		[ -n "$fn" ] || die "Termux package $p not in the index"
		echo " - $fn"
		echo "$p $ver" >> termux-versions.txt
		fetch "$termux_repo/$fn" "debs/$p.deb"
		(cd debs && rm -rf x && mkdir x && cd x && ar x "../$p.deb" && tar -xf data.tar.* -C "$sysroot") || die "cannot unpack $p.deb"
	done
	[ -e "$tprefix/lib/libwayland-client.so" ] || die "Termux sysroot has no libwayland-client.so"
	[ -e "$tprefix/lib/libdrm.so" ] || die "Termux sysroot has no libdrm.so"

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

# The Wayland-on-bionic source changes, as build_wayland.sh's apply_wayland_patches does them for
# the Turnip it ships. Its EGL (egl_wayland_no_drm_node.py) and Zink (general_layout) edits are not
# made: those files are not part of libvulkan_freedreno.so, and this build compiles only that.
apply_wayland_patches(){
	cd "$mesa"
	# A Linux-style build on bionic, like Termux's Mesa: Mesa's Android detection off.
	sed -i 's/^#if defined(__ANDROID__)$/#if 0 \/* Linux-style build on bionic *\//' src/util/detect_os.h
	sed -i 's/^#if defined(__ANDROID__) || defined(ANDROID)$/#if 0 \/* Linux-style build on bionic *\//' include/vulkan/vk_android_native_buffer.h
	sed -i '/^#elif\|^#if/s/DETECT_OS_ANDROID/defined(__ANDROID__)/' src/util/u_process.c
	grep -q "Linux-style build on bionic" src/util/detect_os.h || die "detect_os.h: Android detection guard not found"
	grep -q "Linux-style build on bionic" include/vulkan/vk_android_native_buffer.h || die "vk_android_native_buffer.h: Android guard not found"

	# Termux 0014: the KGSL timestamp wait must not assert on an unexpected errno. Mesa does this
	# itself since MR 44838 (2026-10-08); the rewrite is kept for an older Mesa and skipped otherwise.
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

	# bionic has no pthread_cancel (VK_KHR_display WSI, built because libdrm is linked).
	python3 "$wl_patches/no_pthread_cancel.py" src/vulkan/wsi/wsi_common_display.c \
		|| die "no_pthread_cancel.py did not apply"
	# Bannerlator zero-copy layers (banner_ahb_v1, UBWC request); every anchor is asserted.
	python3 "$wl_patches/banner_ahb_wsi.py" . || die "banner_ahb_wsi.py did not apply"
	# KGSL fixes every leg ships (patches/common/SOURCE).
	bash "$repo/patches/common/apply_common.sh" . || die "patches/common did not apply"

	git -c user.name=banners-turnip -c user.email=build@banners-turnip commit -q -am "Wayland build: shared patches"
	git tag -f banner-wayland >/dev/null
}

# The driver's own recipe, from the same EXTRA_PATCH / EXTRA_SCRIPT as its Android leg and in the
# same order (patch series, freedreno_devices.py syntax, scripts, NDK r29 seds). build_turnip.sh
# tolerates rejected hunks and missing scripts; here either one fails the leg.
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

	# build_turnip.sh's NDK r29 seds (Android-only files; kept so the recipe is the same).
	sed -i 's/typedef const native_handle_t\* buffer_handle_t;/typedef void\* buffer_handle_t;/g' include/android_stub/cutils/native_handle.h || true
	sed -i 's/, hnd->handle/, (void \*)hnd->handle/g' src/util/u_gralloc/u_gralloc_fallback.c || true
	sed -i -E 's/([a-z_]+)->handle->/((const native_handle_t *)\1->handle)->/g' src/vulkan/runtime/vk_android.c || true

	echo "[wayland ${VARIANT}] recipe changes on top of the Wayland patches:"
	git --no-pager diff --stat banner-wayland
}

# Same meson options as build_wayland.sh's configure(); only the Turnip target is built, as that
# script does for every driver but the one that also provides EGL/Zink.
build(){
	cd "$mesa"
	export PATH="$tprefix/opt/libwayland/cross/bin:$PATH"
	command -v wayland-scanner >/dev/null || die "Termux wayland-scanner not on PATH"
	wayland-scanner --version
	export CFLAGS="-Wno-error -Wno-deprecated-declarations -Wno-incompatible-pointer-types-discards-qualifiers -Wno-incompatible-pointer-types"
	export CXXFLAGS="$CFLAGS"

	cat <<EOF >"$workdir/cross.txt"
[binaries]
ar = '$ndk/llvm-ar'
c = ['ccache', '$ndk/aarch64-linux-android$api-clang']
cpp = ['ccache', '$ndk/aarch64-linux-android$api-clang++', '-fno-exceptions', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '--start-no-unused-arguments', '-static-libstdc++', '--end-no-unused-arguments']
c_ld = 'lld'
cpp_ld = 'lld'
strip = '$ndk/llvm-strip'
pkg-config = '/usr/bin/pkg-config'

[properties]
sys_root = '$sysroot'
pkg_config_libdir = ['$tprefix/lib/pkgconfig', '$tprefix/share/pkgconfig']

[host_machine]
system = 'android'
cpu_family = 'aarch64'
cpu = 'armv8'
endian = 'little'
EOF
	cat <<EOF >"$workdir/native.txt"
[binaries]
c = ['ccache', 'clang']
cpp = ['ccache', 'clang++']
ar = 'llvm-ar'
strip = 'llvm-strip'
c_ld = 'lld'
cpp_ld = 'lld'
EOF

	# freedreno-kmds MUST list msm as well as kgsl: with kgsl alone meson drops libdrm and
	# wsi_common_drm.c, and vkCreateSwapchainKHR walks into a compiled-out branch (build_wayland.sh).
	meson setup build-wayland \
		--cross-file "$workdir/cross.txt" \
		--native-file "$workdir/native.txt" \
		--prefix /usr \
		--libdir lib \
		-Dbuildtype=release \
		-Dstrip=false \
		-Db_ndebug=true \
		-Dplatforms=wayland \
		-Dgallium-drivers=zink \
		-Dvulkan-drivers=freedreno \
		-Dfreedreno-kmds=msm,kgsl \
		-Dvulkan-beta=true \
		-Degl=enabled \
		-Dopengl=true \
		-Dgles1=disabled \
		-Dgles2=enabled \
		-Dglx=disabled \
		-Dgbm=disabled \
		-Dglvnd=disabled \
		-Dllvm=disabled \
		-Dxmlconfig=disabled \
		-Dexpat=disabled \
		-Dzstd=disabled \
		-Dvalgrind=disabled \
		-Dlibunwind=disabled \
		-Dandroid-libbacktrace=disabled \
		-Dvideo-codecs= \
		-Dtools=

	ninja -C build-wayland src/freedreno/vulkan/libvulkan_freedreno.so
	[ -f build-wayland/src/freedreno/vulkan/libvulkan_freedreno.so ] || die "libvulkan_freedreno.so was not built"
}

package(){
	cd "$mesa"
	local githash version vk_patch vk_minor driver_version desc
	githash="$(git rev-parse --short "$MESA_COMMIT")"
	version="$(sed 's/-devel.*//' VERSION | tr -d '[:space:]')"
	vk_patch=$(grep '^#define VK_HEADER_VERSION ' include/vulkan/vulkan_core.h | awk '{print $3}')
	vk_minor=$(grep 'define TU_API_VERSION' src/freedreno/vulkan/tu_device.cc | grep -oP 'VK_MAKE_VERSION\(\s*[0-9]+,\s*\K[0-9]+')
	[ -n "$vk_patch" ] && [ -n "$vk_minor" ] || die "cannot read the Vulkan version from the tree"
	driver_version="Vulkan 1.${vk_minor}.${vk_patch}"

	if [ -n "$META_DESC" ]; then desc="$META_DESC"
	else desc="A6xx/A7xx Turnip driver from Mesa main (git ${githash}). KGSL build."; fi
	desc="Wayland build: ${desc} Linux-style Vulkan ICD (KGSL, Wayland WSI, bionic) for Bannerlator Wayland containers - import it as a Wayland game driver. Not an AdrenoTools / X11 driver."

	rm -rf "$stage" && mkdir -p "$stage"
	cp -L build-wayland/src/freedreno/vulkan/libvulkan_freedreno.so "$stage/libvulkan_freedreno.so"
	# The libdrm it was linked against; Bannerlator's importer keeps a libdrm.so next to the driver.
	cp -L "$tprefix/lib/libdrm.so" "$stage/libdrm.so"
	STAGE="$stage" M_NAME="$META_NAME" M_DESC="$desc" M_PKGVER="$PACKAGE_VERSION" M_DRV="$driver_version" python3 - <<'PY'
import json, os
meta = {
    "schemaVersion": 1,
    "name": os.environ["M_NAME"],
    "description": os.environ["M_DESC"],
    "author": "The412Banner",
    "packageVersion": os.environ["M_PKGVER"],
    "vendor": "Mesa",
    "driverVersion": os.environ["M_DRV"],
    "minApi": 29,
    # No "libraryName": an AdrenoTools importer that takes this zip by mistake then never hands
    # the driver to AdrenoTools. Bannerlator's Wayland importer reads only name / driverVersion.
    "kind": "wayland-game-driver",
}
with open(os.path.join(os.environ["STAGE"], "meta.json"), "w") as f:
    json.dump(meta, f, indent=2)
    f.write("\n")
print(json.dumps(meta, indent=2))
PY
	rm -f "$workdir/$ZIP_NAME"
	(cd "$stage" && zip -q -X "$workdir/$ZIP_NAME" libvulkan_freedreno.so libdrm.so meta.json)

	# Facts the release body is written from (verify_driver_zip.py adds the checks).
	R_OUT="$workdir/build-report.json" R_TERMUX="$workdir/termux-versions.txt" R_KGSL="$kgsl_assert" \
	R_FUZZ="$patch_fuzz_hunks" R_VERSION="$version" R_DRV="$driver_version" R_API="$api" R_NDK="$ndkver" \
	R_WLSRC="$(cat "$wl_patches/SOURCE" 2>/dev/null || echo unknown)" python3 - <<'PY'
import json, os
termux = {}
for line in open(os.environ["R_TERMUX"]):
    p = line.split()
    if len(p) >= 2:
        termux[p[0]] = p[1]
report = {
    "platform": "wayland",
    "variant": os.environ.get("VARIANT", ""),
    "mesa_commit": os.environ["MESA_COMMIT"],
    "mesa_version": os.environ["R_VERSION"],
    "driver_version": os.environ["R_DRV"],
    "extra_patch": os.environ.get("EXTRA_PATCH", ""),
    "extra_script": os.environ.get("EXTRA_SCRIPT", ""),
    "patch_fuzz_hunks": int(os.environ.get("R_FUZZ") or 0),
    "ndk": os.environ["R_NDK"],
    "api": int(os.environ["R_API"]),
    "termux": termux,
    "wayland_patches": {
        "android_detection_off": "applied",
        "kgsl_wait_assert": os.environ["R_KGSL"],
        "no_pthread_cancel": "applied",
        "banner_ahb_wsi": "applied",
        "source": os.environ["R_WLSRC"],
    },
}
json.dump(report, open(os.environ["R_OUT"], "w"), indent=2)
print(json.dumps(report, indent=2))
PY
	log "built $workdir/$ZIP_NAME"
}

prepare
apply_wayland_patches
apply_recipe
build
package

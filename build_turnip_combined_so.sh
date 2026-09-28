#!/bin/bash
# TEST: one libvulkan_freedreno.so for both of Bannerlator's worlds -- the AdrenoTools driver (X11
# games and the Wayland compositor) AND the Wayland game driver (the ICD winewayland hands to the
# Khronos loader inside the Wine container).
#
# Second attempt. The first (build_turnip_wayland_wsi.sh on branch `wayland`, run 34713704642,
# 2026-09-12) was the Android release recipe plus -Dplatforms=android,wayland; it loaded through
# AdrenoTools but every Wayland launch died with VK_ERROR_INCOMPATIBLE_DRIVER. Against that build
# this one changes:
#   * -Dandroid-strict=false  Mesa defaults it to true, and ANDROID_STRICT hides every instance
#                             extension outside Android's allow-list -- VK_KHR_wayland_surface
#                             included -- and refuses them in vkCreateInstance (vk_instance.c).
#   * freedreno-kmds=kgsl,msm With kgsl alone Mesa drops libdrm, so wsi_common_drm.c (the dma-buf
#                             swapchain path the Wayland WSI uses) is compiled out. Same rule as
#                             build_turnip_wayland.sh.
#   * the Wayland legs' patches: banner_ahb_wsi (zero-copy layers), the KGSL wait assert, and
#                             patches/common. no_pthread_cancel is not needed: the display WSI is
#                             not built on the Android platform.
#   * DT_RUNPATH=$ORIGIN, with libwayland-client / libffi / libdrm shipped beside the driver, so
#                             AdrenoTools (which searches only its hooks dir) still resolves them.
#
# Output: combined_workdir/$ZIP_NAME -- a flat zip both of Bannerlator's importers accept:
# libvulkan_freedreno.so + libdrm.so + libwayland-client.so + libffi.so + meta.json (libraryName
# set, no "kind", so the AdrenoTools importer takes it; the Wayland importer keeps the .so + libdrm).
#
# Environment: MESA_COMMIT (required), ZIP_NAME (required), META_NAME (required), VARIANT,
#              EXTRA_PATCH, EXTRA_SCRIPT (as build_turnip.sh; any failure fails the build).

set -eo pipefail

green='\033[0;32m'
red='\033[0;31m'
nocolor='\033[0m'
die(){ echo -e "${red}[combined ${VARIANT:-?}] $*${nocolor}" >&2; exit 1; }
log(){ echo -e "${green}[combined ${VARIANT:-?}]${nocolor} $*"; }

repo="$(cd "$(dirname "$0")" && pwd)"
workdir="$(pwd)/combined_workdir"
ndkver="android-ndk-r29"
ndk="$workdir/$ndkver/toolchains/llvm/prebuilt/linux-x86_64/bin"
sdkver=36      # Mesa platform-sdk-version, as the Android release
clangapi=34    # the NDK compiler the Android release uses
termux_repo="https://packages-cf.termux.dev/apt/termux-main"
termux_pkgs="libwayland libwayland-protocols libdrm libffi"
termux_host_pkgs="libwayland-cross-scanner"
sysroot="$workdir/termux"
tprefix="$sysroot/data/data/com.termux/files/usr"
mesa="$workdir/mesa"
stage="$workdir/stage"
wl_patches="$repo/patches/wayland"

[[ "$MESA_COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "MESA_COMMIT must be a 40-hex commit, got '${MESA_COMMIT}'"
[ -n "$ZIP_NAME" ] || die "ZIP_NAME is required"
[ -n "$META_NAME" ] || die "META_NAME is required"

fetch(){	# <url> <out>
	curl -fsSL --retry 5 --retry-delay 10 --retry-all-errors "$1" -o "$2" || die "download failed: $1"
}

prepare(){
	mkdir -p "$workdir" && cd "$workdir"

	log "downloading $ndkver"
	fetch "https://dl.google.com/android/repository/$ndkver-linux.zip" ndk.zip
	unzip -q ndk.zip && rm ndk.zip
	[ -x "$ndk/aarch64-linux-android$clangapi-clang" ] || die "NDK clang for API $clangapi missing"

	log "fetching Termux packages: $termux_pkgs $termux_host_pkgs"
	fetch "$termux_repo/dists/stable/main/binary-aarch64/Packages" Packages
	rm -rf "$sysroot" debs && mkdir -p "$sysroot" debs
	for p in $termux_pkgs $termux_host_pkgs; do
		fn=$(awk -v P="$p" 'BEGIN{RS="";FS="\n"} {n="";f=""; for(i=1;i<=NF;i++){if($i~/^Package: /)n=substr($i,10); if($i~/^Filename: /)f=substr($i,11)} if(n==P){print f; exit}}' Packages)
		[ -n "$fn" ] || die "Termux package $p not in the index"
		echo " - $fn"
		fetch "$termux_repo/$fn" "debs/$p.deb"
		(cd debs && rm -rf x && mkdir x && cd x && ar x "../$p.deb" && tar -xf data.tar.* -C "$sysroot") || die "cannot unpack $p.deb"
	done
	for l in libwayland-client.so libdrm.so libffi.so; do
		[ -e "$tprefix/lib/$l" ] || die "Termux sysroot has no $l"
	done

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

apply_patches(){
	cd "$mesa"
	# Termux 0014: the KGSL timestamp wait must not assert on an unexpected errno (as the Wayland legs).
	python3 - <<'PY' || die "KGSL wait patch failed"
p = 'src/freedreno/vulkan/tu_knl_kgsl.cc'
s = open(p).read()
old = """      } else if (ret == -1) {
         assert(errno == ETIMEDOUT);
         return VK_TIMEOUT;"""
new = """      } else if (ret == -1) {
         if (errno != ETIMEDOUT)
            mesa_logw("wait_timestamp_safe: errno %d (%s)", errno, strerror(errno));
         return VK_TIMEOUT;"""
print('KGSL wait assert -> warning:', 'applied' if old in s else 'not-found')
if old in s:
    open(p, 'w').write(s.replace(old, new, 1))
PY
	python3 "$wl_patches/banner_ahb_wsi.py" . || die "banner_ahb_wsi.py did not apply"
	bash "$repo/patches/common/apply_common.sh" . || die "patches/common did not apply"

	if [ -n "$EXTRA_PATCH" ]; then
		[ -f "$repo/$EXTRA_PATCH" ] || die "EXTRA_PATCH $EXTRA_PATCH does not exist"
		log "applying $EXTRA_PATCH"
		patch -p1 -N --fuzz=4 --no-backup-if-mismatch < "$repo/$EXTRA_PATCH" || die "$EXTRA_PATCH did not apply cleanly"
	fi
	python3 -c "compile(open('src/freedreno/common/freedreno_devices.py').read(),'f','exec')" \
		|| die "freedreno_devices.py does not parse after the patch series"
	if [ -n "$EXTRA_SCRIPT" ]; then
		local scripts s
		IFS=':' read -ra scripts <<< "$EXTRA_SCRIPT"
		for s in "${scripts[@]}"; do
			[ -f "$repo/$s" ] || die "EXTRA_SCRIPT $s does not exist"
			log "running $s"
			python3 "$repo/$s" || die "$s failed"
		done
	fi

	# build_turnip.sh's NDK r29 fixes (the Android platform code is compiled here).
	sed -i 's/typedef const native_handle_t\* buffer_handle_t;/typedef void\* buffer_handle_t;/g' include/android_stub/cutils/native_handle.h || true
	sed -i 's/, hnd->handle/, (void \*)hnd->handle/g' src/util/u_gralloc/u_gralloc_fallback.c || true
	sed -i -E 's/([a-z_]+)->handle->/((const native_handle_t *)\1->handle)->/g' src/vulkan/runtime/vk_android.c || true
}

build(){
	cd "$mesa"
	export PATH="$tprefix/opt/libwayland/cross/bin:$PATH"
	command -v wayland-scanner >/dev/null || die "Termux wayland-scanner not on PATH"
	wayland-scanner --version
	export CFLAGS="-D__ANDROID__ -Wno-error -Wno-deprecated-declarations -Wno-incompatible-pointer-types-discards-qualifiers -Wno-incompatible-pointer-types"
	export CXXFLAGS="$CFLAGS"

	cat <<EOF >"$workdir/cross.txt"
[binaries]
ar = '$ndk/llvm-ar'
c = ['ccache', '$ndk/aarch64-linux-android$clangapi-clang']
cpp = ['ccache', '$ndk/aarch64-linux-android$clangapi-clang++', '-fno-exceptions', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '--start-no-unused-arguments', '-static-libstdc++', '--end-no-unused-arguments']
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

	meson setup build-combined \
		--cross-file "$workdir/cross.txt" \
		--native-file "$workdir/native.txt" \
		--prefix /usr \
		--libdir lib \
		-Dbuildtype=release \
		-Dstrip=true \
		-Dplatforms=android,wayland \
		-Dandroid-strict=false \
		-Dandroid-stub=true \
		-Dplatform-sdk-version=$sdkver \
		-Dandroid-libbacktrace=disabled \
		-Dvideo-codecs= \
		-Dgallium-drivers= \
		-Dvulkan-drivers=freedreno \
		-Dvulkan-beta=true \
		-Dfreedreno-kmds=kgsl,msm \
		-Degl=disabled

	ninja -C build-combined src/freedreno/vulkan/libvulkan_freedreno.so
	[ -f build-combined/src/freedreno/vulkan/libvulkan_freedreno.so ] || die "libvulkan_freedreno.so was not built"
}

package(){
	cd "$mesa"
	local re="$ndk/llvm-readelf" githash vk_patch vk_minor driver_version
	rm -rf "$stage" && mkdir -p "$stage"
	cp -L build-combined/src/freedreno/vulkan/libvulkan_freedreno.so "$stage/"
	for l in libwayland-client.so libdrm.so libffi.so; do cp -L "$tprefix/lib/$l" "$stage/$l"; done
	for l in libvulkan_freedreno.so libwayland-client.so libdrm.so; do
		patchelf --set-rpath '$ORIGIN' "$stage/$l" || die "patchelf $l failed"
	done

	# The facts the whole test rests on; any one missing fails the build.
	local so="$stage/libvulkan_freedreno.so"
	log "NEEDED: $("$re" -d "$so" | grep -oP 'NEEDED.*\[\K[^]]+' | tr '\n' ' ')"
	log "RUNPATH: $("$re" -d "$so" | grep -E 'RUNPATH|RPATH' || true)"
	"$re" -d "$so" | grep -q 'RUNPATH.*\$ORIGIN' || die "no DT_RUNPATH \$ORIGIN"
	local syms; syms="$("$re" --dyn-syms -W "$so")"
	echo "$syms" | grep -qw 'HMI'                                   || die "no HMI export (AdrenoTools cannot load it)"
	echo "$syms" | grep -q 'vk_icdGetInstanceProcAddr'              || die "no vk_icdGetInstanceProcAddr export (the Khronos loader cannot load it)"
	echo "$syms" | grep -q 'vk_icdNegotiateLoaderICDInterfaceVersion' || die "no vk_icdNegotiateLoaderICDInterfaceVersion export"
	local wl; wl="$(echo "$syms" | grep -c ' UND .*wl_' || true)"
	[ "$wl" -gt 10 ] || die "only $wl wl_* imports: the Wayland WSI is not in"
	grep -q "VK_KHR_wayland_surface" "$so" || die "VK_KHR_wayland_surface string missing"
	grep -q "banner_ahb_v1" "$so" || die "banner_ahb_v1 missing (zero-copy patch not in)"
	for l in libwayland-client.so libdrm.so libffi.so; do
		log "$l NEEDED: $("$re" -d "$stage/$l" | grep -oP 'NEEDED.*\[\K[^]]+' | tr '\n' ' ')"
	done
	log "$wl wl_* imports, HMI + vk_icd* exported, RUNPATH \$ORIGIN"

	githash="$(git rev-parse --short HEAD)"
	vk_patch=$(grep '^#define VK_HEADER_VERSION ' include/vulkan/vulkan_core.h | awk '{print $3}')
	vk_minor=$(grep 'define TU_API_VERSION' src/freedreno/vulkan/tu_device.cc | grep -oP 'VK_MAKE_VERSION\(\s*[0-9]+,\s*\K[0-9]+')
	driver_version="Vulkan 1.${vk_minor}.${vk_patch}"
	cat <<EOF >"$stage/meta.json"
{
  "schemaVersion": 1,
  "name": "${META_NAME}",
  "description": "TEST: one Turnip for X11 (AdrenoTools), the Wayland compositor and the Wayland game driver. Mesa git ${githash}, KGSL, Android + Wayland platforms. Import it in both lists.",
  "author": "The412Banner",
  "packageVersion": "1",
  "vendor": "Mesa",
  "driverVersion": "${driver_version}",
  "minApi": 28,
  "libraryName": "libvulkan_freedreno.so"
}
EOF
	cat "$stage/meta.json"
	rm -f "$workdir/$ZIP_NAME"
	(cd "$stage" && zip -q -X "$workdir/$ZIP_NAME" libvulkan_freedreno.so libwayland-client.so libdrm.so libffi.so meta.json)
	ls -la "$stage" "$workdir/$ZIP_NAME"
	log "built $workdir/$ZIP_NAME"
}

prepare
apply_patches
build
package

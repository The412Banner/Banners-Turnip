#!/bin/bash -e
# Combined Turnip: the release's A6xx/A7xx AdrenoTools driver (Android platform, KGSL) with the
# Wayland WSI built in as well, so one driver serves both the X11 path (AdrenoTools) and Wine's
# winewayland.drv on the Bannerlator compositor. Same Mesa commit as the release (mesa_hash.txt),
# no patches; the only addition to the release recipe is -Dplatforms=android,wayland, which
# links Termux's libwayland-client (shipped next to the driver in the zip).

green='\033[0;32m'
red='\033[0;31m'
nocolor='\033[0m'
workdir="$(pwd)/wayland_workdir"
sdkver="36"
ndkver="android-ndk-r29"
ndk="$workdir/$ndkver/toolchains/llvm/prebuilt/linux-x86_64/bin"
api=29   # reallocarray and ELF TLS
termux_repo="https://packages-cf.termux.dev/apt/termux-main"
termux_pkgs="libwayland libwayland-protocols libdrm libffi"
# Mesa wants a wayland-scanner of exactly the libwayland version; Termux ships an x86_64 one.
termux_host_pkgs="libwayland-cross-scanner"
sysroot="$workdir/termux"
tprefix="$sysroot/data/data/com.termux/files/usr"
out="$workdir/out"

mesa_hash="$(tr -d '[:space:]' < mesa_hash.txt)"

prepare(){
	mkdir -p "$workdir" && cd "$workdir"

	if [ ! -d "$ndkver" ]; then
		echo "Downloading $ndkver..."
		curl -sL "https://dl.google.com/android/repository/$ndkver-linux.zip" -o ndk.zip
		unzip -q ndk.zip && rm ndk.zip
	fi

	# Termux bionic aarch64 packages for the libraries Mesa links against. Resolve the current file
	# names from the index: Termux drops old versions from the pool.
	echo "Fetching Termux packages: $termux_pkgs"
	curl -sL "$termux_repo/dists/stable/main/binary-aarch64/Packages" -o Packages
	rm -rf "$sysroot" debs && mkdir -p "$sysroot" debs
	for p in $termux_pkgs $termux_host_pkgs; do
		fn=$(awk -v P="$p" 'BEGIN{RS="";FS="\n"} {n="";f=""; for(i=1;i<=NF;i++){if($i~/^Package: /)n=substr($i,10); if($i~/^Filename: /)f=substr($i,11)} if(n==P){print f; exit}}' Packages)
		[ -n "$fn" ] || { echo -e "${red}Termux package $p not found${nocolor}"; exit 1; }
		echo " - $fn"
		curl -sL "$termux_repo/$fn" -o "debs/$p.deb"
		(cd debs && rm -rf x && mkdir x && cd x && ar x "../$p.deb" && tar -xf data.tar.* -C "$sysroot")
	done
	ls "$tprefix/lib" | grep -E "wayland|drm|ffi" || true

	if [ ! -d mesa ]; then
		echo "Fetching Mesa $mesa_hash..."
		git init -q mesa
		git -C mesa remote add origin https://gitlab.freedesktop.org/mesa/mesa.git
		git -C mesa fetch -q --depth=1 origin "$mesa_hash"
		git -C mesa checkout -q FETCH_HEAD
	fi
}

build(){
	cd "$workdir/mesa"
	git checkout -q -- .

	# The same NDK r29 fixes as build_turnip.sh.
	sed -i 's/typedef const native_handle_t\* buffer_handle_t;/typedef void\* buffer_handle_t;/g' include/android_stub/cutils/native_handle.h || true
	sed -i 's/, hnd->handle/, (void \*)hnd->handle/g' src/util/u_gralloc/u_gralloc_fallback.c || true
	sed -i -E 's/([a-z_]+)->handle->/((const native_handle_t *)\1->handle)->/g' src/vulkan/runtime/vk_android.c || true

	export PATH="$tprefix/opt/libwayland/cross/bin:$PATH"
	wayland-scanner --version

	export CFLAGS="-D__ANDROID__ -Wno-error -Wno-deprecated-declarations -Wno-incompatible-pointer-types-discards-qualifiers -Wno-incompatible-pointer-types"
	export CXXFLAGS="$CFLAGS"

	cat <<EOF >cross-combined.txt
[binaries]
ar = '$ndk/llvm-ar'
c = ['ccache', '$ndk/aarch64-linux-android$sdkver-clang']
cpp = ['ccache', '$ndk/aarch64-linux-android$sdkver-clang++', '-fno-exceptions', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '--start-no-unused-arguments', '-static-libstdc++', '--end-no-unused-arguments']
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

	cat <<EOF >native.txt
[binaries]
c = ['ccache', 'clang']
cpp = ['ccache', 'clang++']
ar = 'llvm-ar'
strip = 'llvm-strip'
c_ld = 'lld'
cpp_ld = 'lld'
EOF

	meson setup build-combined \
		--cross-file cross-combined.txt \
		--native-file native.txt \
		--prefix /usr \
		--libdir lib \
		-Dbuildtype=release \
		-Dstrip=true \
		-Dplatforms=android,wayland \
		-Dvideo-codecs= \
		-Dplatform-sdk-version=$sdkver \
		-Dandroid-stub=true \
		-Dgallium-drivers= \
		-Dvulkan-drivers=freedreno \
		-Dvulkan-beta=true \
		-Dfreedreno-kmds=kgsl \
		-Degl=disabled \
		-Dandroid-libbacktrace=disabled

	ninja -C build-combined
	rm -rf "$out-combined" && DESTDIR="$out-combined" ninja -C build-combined install
}

package(){
	cd "$out-combined/usr/lib"
	ls -la
	[ -e libvulkan_freedreno.so ] || { echo -e "${red}missing libvulkan_freedreno.so${nocolor}"; exit 1; }
	echo "libvulkan_freedreno.so needs: $("$ndk/llvm-readelf" -d libvulkan_freedreno.so | grep -oP 'NEEDED.*\[\K[^]]+' | tr '\n' ' ')"
	echo "Wayland WSI symbols: $("$ndk/llvm-readelf" --dyn-syms libvulkan_freedreno.so | grep -c -E 'wl_|wayland')"

	githash="$(git -C "$workdir/mesa" rev-parse --short HEAD)"
	version="$(sed 's/-devel.*//' "$workdir/mesa/VERSION" | tr -d '[:space:]')"
	pkg="$workdir/turnip-combined"
	rm -rf "$pkg" && mkdir -p "$pkg"
	cp libvulkan_freedreno.so "$pkg/"
	cp -L "$tprefix/lib/libwayland-client.so" "$pkg/"
	_vk_patch=$(grep '^#define VK_HEADER_VERSION ' "$workdir/mesa/include/vulkan/vulkan_core.h" | awk '{print $3}')
	_vk_minor=$(grep 'define TU_API_VERSION' "$workdir/mesa/src/freedreno/vulkan/tu_device.cc" | grep -oP 'VK_MAKE_VERSION\(\s*[0-9]+,\s*\K[0-9]+')
	cat <<EOF >"$pkg/meta.json"
{
  "schemaVersion": 1,
  "name": "Mesa Turnip v${version}-${githash} (Android + Wayland)",
  "description": "A6xx/A7xx Turnip driver from Mesa main (git ${githash}). KGSL build with the Wayland WSI, for X11 (AdrenoTools) and Wayland alike.",
  "author": "The412Banner",
  "packageVersion": "1",
  "vendor": "Mesa",
  "driverVersion": "Vulkan 1.${_vk_minor}.${_vk_patch}",
  "minApi": 28,
  "libraryName": "libvulkan_freedreno.so"
}
EOF
	cat "$pkg/meta.json"
	(cd "$pkg" && zip -q "$workdir/mesa-turnip-combined-wayland-${version}-${githash}.zip" libvulkan_freedreno.so libwayland-client.so meta.json)
	ls -la "$workdir"/*.zip
	echo -e "${green}Built the combined Android + Wayland Turnip${nocolor}"
}

prepare
build
package

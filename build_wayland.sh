#!/bin/bash -e
# Wayland variant: the A6xx/A7xx Turnip (KGSL) with the Wayland WSI, plus Mesa's EGL (Wayland
# platform) and Zink for OpenGL. It is meant for Wine's winewayland.drv running on the Bannerlator
# compositor, not for AdrenoTools: it's built for a Termux-style bionic userland (the Bannerlator
# imagefs) and links Termux's libwayland and libdrm.
#
# Same Mesa commit as the Android release (mesa_hash.txt), no patches.

green='\033[0;32m'
red='\033[0;31m'
nocolor='\033[0m'
workdir="$(pwd)/wayland_workdir"
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

	# This is a Linux-style build on bionic (like Termux's Mesa), not an Android-platform one: turn
	# off Mesa's Android detection, as Termux does (their 0000/0002 patches), and keep Turnip out of
	# Zink's general-layout path (their 0018: rendering artifacts on Adreno).
	git checkout -q -- .
	sed -i 's/^#if defined(__ANDROID__)$/#if 0 \/* Linux-style build on bionic *\//' src/util/detect_os.h
	sed -i 's/^#if defined(__ANDROID__) || defined(ANDROID)$/#if 0 \/* Linux-style build on bionic *\//' include/vulkan/vk_android_native_buffer.h
	sed -i '/^#elif\|^#if/s/DETECT_OS_ANDROID/defined(__ANDROID__)/' src/util/u_process.c
	grep -n "Linux-style build on bionic" src/util/detect_os.h include/vulkan/vk_android_native_buffer.h
	python3 - <<'PY'
p = 'src/gallium/drivers/zink/zink_screen.c'
s = open(p).read()
old = "   case VK_DRIVER_ID_MESA_TURNIP:\n   case VK_DRIVER_ID_QUALCOMM_PROPRIETARY:\n      screen->driver_workarounds.general_layout = true;\n      break;\n"
new = ("   case VK_DRIVER_ID_QUALCOMM_PROPRIETARY:\n      screen->driver_workarounds.general_layout = true;\n      break;\n"
       "   case VK_DRIVER_ID_MESA_TURNIP:\n      screen->driver_workarounds.general_layout = false;\n      break;\n")
if old in s:
    open(p, 'w').write(s.replace(old, new, 1))
    print("zink: general layout off for Turnip")
else:
    print("zink: general-layout list changed upstream, left as is")
PY

	# Termux's x86_64 wayland-scanner (the libwayland version) ahead of any system one.
	export PATH="$tprefix/opt/libwayland/cross/bin:$PATH"
	wayland-scanner --version

	export CFLAGS="-Wno-error -Wno-deprecated-declarations -Wno-incompatible-pointer-types-discards-qualifiers -Wno-incompatible-pointer-types"
	export CXXFLAGS="$CFLAGS"

	cat <<EOF >cross.txt
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

	cat <<EOF >native.txt
[binaries]
c = ['ccache', 'clang']
cpp = ['ccache', 'clang++']
ar = 'llvm-ar'
strip = 'llvm-strip'
c_ld = 'lld'
cpp_ld = 'lld'
EOF

	meson setup build-wayland \
		--cross-file cross.txt \
		--native-file native.txt \
		--prefix /usr \
		--libdir lib \
		-Dbuildtype=release \
		-Dstrip=true \
		-Dplatforms=wayland \
		-Dgallium-drivers=zink \
		-Dvulkan-drivers=freedreno \
		-Dfreedreno-kmds=kgsl \
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

	ninja -C build-wayland
	rm -rf "$out" && DESTDIR="$out" ninja -C build-wayland install
}

package(){
	cd "$out/usr/lib"
	ls -la
	# This cross build names the libraries without a version; Wine opens libEGL.so.1.
	[ -e libEGL.so.1 ] || cp -L libEGL.so libEGL.so.1
	[ -e libGLESv2.so.2 ] || cp -L libGLESv2.so libGLESv2.so.2
	for f in libEGL.so.1 libGLESv2.so.2 libvulkan_freedreno.so libgallium-*.so; do
		[ -e "$f" ] || { echo -e "${red}missing $f${nocolor}"; exit 1; }
	done
	echo "== NEEDED / SONAME =="
	for f in *.so*; do
		[ -f "$f" ] || continue
		echo "$f: soname $("$ndk/llvm-readelf" -d "$f" | grep -oP 'SONAME.*\[\K[^]]+') needs $("$ndk/llvm-readelf" -d "$f" | grep -oP 'NEEDED.*\[\K[^]]+' | tr '\n' ' ')"
	done

	# The libraries, anything of this build they link, and the Termux libwayland they were linked
	# against.
	pkg="$workdir/banner-mesa-wayland"
	rm -rf "$pkg" && mkdir -p "$pkg/lib"
	cp -L libEGL.so.1 libGLESv2.so.2 libvulkan_freedreno.so libgallium-*.so "$pkg/lib/"
	for f in libEGL.so.1 libGLESv2.so.2 libvulkan_freedreno.so libgallium-*.so; do
		for n in $("$ndk/llvm-readelf" -d "$f" | grep -oP 'NEEDED.*\[\K[^]]+'); do
			[ -e "$n" ] && [ ! -e "$pkg/lib/$n" ] && cp -L "$n" "$pkg/lib/" && echo "bundled $n (needed by $f)"
		done
	done
	cp -L "$tprefix/lib/libwayland-client.so" "$tprefix/lib/libwayland-server.so" "$tprefix/lib/libwayland-egl.so" "$pkg/lib/"
	{
		echo "Mesa $(cat "$workdir/mesa/VERSION") at $mesa_hash (gitlab.freedesktop.org/mesa/mesa)."
		echo "Linux-style build on bionic like Termux's (Android detection off, Zink general layout off for Turnip)."
		echo "Built with $ndkver, API $api, for the Bannerlator imagefs."
		echo "Turnip: KGSL, Wayland WSI. OpenGL: EGL (Wayland platform) + Zink, no LLVM, no GLX."
		echo "Termux packages linked:"
		for p in $termux_pkgs; do awk -v P="$p" 'BEGIN{RS="";FS="\n"} {n="";v=""; for(i=1;i<=NF;i++){if($i~/^Package: /)n=substr($i,10); if($i~/^Version: /)v=substr($i,10)} if(n==P){print "  " n " " v; exit}}' "$workdir/Packages"; done
	} > "$pkg/BUILD-INFO.txt"
	cat "$pkg/BUILD-INFO.txt"
	ls -la "$pkg/lib"
	(cd "$workdir" && tar -czf banner-mesa-wayland.tar.gz banner-mesa-wayland)
	echo -e "${green}Built $workdir/banner-mesa-wayland.tar.gz${nocolor}"
}

prepare
build
package

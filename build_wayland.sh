#!/bin/bash -e
# Wayland variant: the A6xx/A7xx Turnip (KGSL) with the Wayland WSI, plus Mesa's EGL (Wayland
# platform) and Zink for OpenGL. It is meant for Wine's winewayland.drv running on the Bannerlator
# compositor, not for AdrenoTools: it's built for a Termux-style bionic userland (the Bannerlator
# imagefs) and links Termux's libwayland and libdrm.
#
# Same Mesa commit as the Android release (mesa_hash.txt). Three Turnip drivers come out of the one
# checkout, with the same flags: the plain one, plus the two Android-matrix variants
# (turnip_build_combined_test.yml) applied exactly as build_turnip.sh applies them:
#   plain : no extra patch                    Adreno 6xx, 730/740/750 (and upstream's 722 entry)
#   a7xx  : patches/a710-720.py               Adreno 710/720/722 (tuned magic regs, replaces 722)
#   a8xx  : patches/tu8_kgsl_26.patch + fix_a8xx_dev_info.py + apply_a8xx_gpus.py
#                                             Adreno 8xx (adds 825, A810 KGSL id, extra 829 ids)
# winewayland picks one through BANNER_WAYLAND_VK_VARIANT (see proton-wine android/wayland-deps/TURNIP.md).

green='\033[0;32m'
red='\033[0;31m'
nocolor='\033[0m'
workdir="$(pwd)/wayland_workdir"
ndkver="android-ndk-r29"
ndk="$workdir/$ndkver/toolchains/llvm/prebuilt/linux-x86_64/bin"
api=29   # reallocarray and ELF TLS
termux_repo="https://packages-cf.termux.dev/apt/termux-main"
# This repo: prepare() cd's into the work dir, so resolve it before anything moves.
repo="$(cd "$(dirname "$0")" && pwd)"
termux_pkgs="libwayland libwayland-protocols libdrm libffi"
# Mesa wants a wayland-scanner of exactly the libwayland version; Termux ships an x86_64 one.
termux_host_pkgs="libwayland-cross-scanner"
sysroot="$workdir/termux"
tprefix="$sysroot/data/data/com.termux/files/usr"
out="$workdir/out"

# The Wayland variant may pin its own Mesa ref (a tag or commit) in mesa_wayland_ref.txt; the
# Android release keeps using mesa_hash.txt. Used to A/B the driver against Termux's Mesa version.
if [ -s mesa_wayland_ref.txt ]; then mesa_hash="$(tr -d '[:space:]' < mesa_wayland_ref.txt)"
else mesa_hash="$(tr -d '[:space:]' < mesa_hash.txt)"; fi

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
	# The shared patches get committed on top of this so each variant can start from them cleanly.
	git -C mesa rev-parse -q --verify banner-base >/dev/null 2>&1 || git -C mesa tag banner-base HEAD
}

# The Android matrix's variant step (build_turnip.sh): a patch series with -N --fuzz=4, then the
# scripts. Here a patch that does not apply is an error, and a variant that leaves the device table
# untouched is refused: a driver that silently equals the plain one must not ship under its name.
apply_variant(){
	local name="$1" patch="$2" scripts="$3" s
	cd "$workdir/mesa"
	git checkout -q -- .
	if [ -n "$patch" ]; then
		echo "[$name] applying $patch"
		patch -p1 -N --fuzz=4 < "$repo/$patch" || { echo -e "${red}[$name] $patch did not apply${nocolor}"; exit 1; }
	fi
	IFS=':' read -ra s <<< "$scripts"
	for script in "${s[@]}"; do
		echo "[$name] running $script"
		python3 "$repo/$script" || { echo -e "${red}[$name] $script failed${nocolor}"; exit 1; }
	done
	echo "[$name] changes against the shared tree:"
	git --no-pager diff --stat
	if git diff --quiet -- src/freedreno/common/freedreno_devices.py; then
		echo -e "${red}[$name] variant left freedreno_devices.py unchanged, refusing to ship it${nocolor}"; exit 1
	fi
}

configure(){
	meson setup "$1" \
		--cross-file cross.txt \
		--native-file native.txt \
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
}

build(){
	cd "$workdir/mesa"

	# This is a Linux-style build on bionic (like Termux's Mesa), not an Android-platform one: turn
	# off Mesa's Android detection, as Termux does (their 0000/0002 patches), and keep Turnip out of
	# Zink's general-layout path (their 0018: rendering artifacts on Adreno).
	git reset -q --hard banner-base
	sed -i 's/^#if defined(__ANDROID__)$/#if 0 \/* Linux-style build on bionic *\//' src/util/detect_os.h
	sed -i 's/^#if defined(__ANDROID__) || defined(ANDROID)$/#if 0 \/* Linux-style build on bionic *\//' include/vulkan/vk_android_native_buffer.h
	sed -i '/^#elif\|^#if/s/DETECT_OS_ANDROID/defined(__ANDROID__)/' src/util/u_process.c
	grep -n "Linux-style build on bionic" src/util/detect_os.h include/vulkan/vk_android_native_buffer.h
	# No DRM device here: with Zink forced, EGL takes its software-window (kopper) path, which
	# then renders on the GPU through Zink's own Vulkan WSI. Upstream only takes it for
	# LIBGL_ALWAYS_SOFTWARE, and that flag makes Zink insist on a CPU Vulkan device.
	python3 - <<'PY'
p = 'src/egl/drivers/dri2/platform_wayland.c'
s = open(p).read()
old = "   if (disp->Options.ForceSoftware)\n      return dri2_initialize_wayland_swrast(disp);\n   else\n      return dri2_initialize_wayland_drm(disp);"
new = "   if (disp->Options.ForceSoftware || disp->Options.Zink)\n      return dri2_initialize_wayland_swrast(disp);\n   else\n      return dri2_initialize_wayland_drm(disp);"
if old in s:
    open(p, 'w').write(s.replace(old, new, 1))
    print("egl: Zink takes the kopper path on Wayland")
else:
    print("egl: platform_wayland.c differs at this Mesa ref, kopper patch skipped")
PY
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

	# Termux 0014: tu_knl_kgsl's timestamp wait asserts that a failed ioctl can only ever be
	# ETIMEDOUT. On this KGSL kernel it can be other things, and the assert takes the whole
	# process down instead of letting the caller handle a timeout. Warn and report the
	# timeout instead, which is what Termux ships.
	python3 - <<'PYEOF_KGSL'
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
    print('turnip: kgsl timestamp wait no longer asserts')
else:
    print('turnip: kgsl wait_timestamp_safe assert not found, left as is')
PYEOF_KGSL
	# With libdrm present Mesa also builds the VK_KHR_display WSI (wsi_common_display.c), which
	# stops its wait/hotplug threads with pthread_cancel. bionic has none, so do what Termux's 0006
	# does (SIGUSR2 handler that pthread_exits), written against exact source text so it survives
	# line drift between Mesa versions.
	python3 "$repo/patches/wayland/no_pthread_cancel.py" src/vulkan/wsi/wsi_common_display.c \
		|| { echo -e "${red}wsi display: pthread_cancel replacement did not apply${nocolor}"; exit 1; }
	# Everything above is shared by the three drivers: commit it so a variant is exactly
	# "these patches + its own", and git diff shows only the variant's part.
	git -c user.name=banners-turnip -c user.email=build@banners-turnip commit -q -am "Wayland build: shared patches"

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

	# freedreno-kmds MUST list msm as well as kgsl: with kgsl alone Mesa's top-level meson decides
	# the system has no KMS/DRM, drops libdrm, and does not compile wsi_common_drm.c. The Wayland
	# WSI still builds DRM-type images for every real device, so vkCreateSwapchainKHR then runs into
	# a compiled-out branch (unreachable) and the guest dies with an access violation. Termux builds
	# msm,kgsl; msm just finds no /dev/dri at runtime.
	configure build-wayland

	ninja -C build-wayland
	rm -rf "$out" && DESTDIR="$out" ninja -C build-wayland install
	cp -L build-wayland/src/freedreno/vulkan/libvulkan_freedreno.so "$out/usr/lib/libvulkan_freedreno_wayland.so"

	# The two Adreno variants: same tree, same flags, only the Turnip target.
	build_variant a7xx "" "patches/a710-720.py"
	build_variant a8xx "patches/tu8_kgsl_26.patch" "patches/fix_a8xx_dev_info.py:patches/apply_a8xx_gpus.py"
	cd "$workdir/mesa" && git checkout -q -- .
}

build_variant(){
	local name="$1"
	apply_variant "$@"
	configure "build-wayland-$name"
	ninja -C "build-wayland-$name" src/freedreno/vulkan/libvulkan_freedreno.so
	cp -L "build-wayland-$name/src/freedreno/vulkan/libvulkan_freedreno.so" "$out/usr/lib/libvulkan_freedreno_wayland_$name.so"
}

package(){
	cd "$out/usr/lib"
	ls -la
	# This cross build names the libraries without a version; Wine opens libEGL.so.1.
	[ -e libEGL.so.1 ] || cp -L libEGL.so libEGL.so.1
	[ -e libGLESv2.so.2 ] || cp -L libGLESv2.so libGLESv2.so.2
	turnips="libvulkan_freedreno_wayland.so libvulkan_freedreno_wayland_a7xx.so libvulkan_freedreno_wayland_a8xx.so"
	for f in libEGL.so.1 libGLESv2.so.2 $turnips libgallium-*.so; do
		[ -e "$f" ] || { echo -e "${red}missing $f${nocolor}"; exit 1; }
	done
	# The ICD must carry the DRM image path (see the freedreno-kmds note): fail loudly if it does not.
	for f in $turnips; do
		"$ndk/llvm-readelf" -d "$f" | grep -q "libdrm.so" || { echo -e "${red}$f does not link libdrm: the Wayland WSI has no DRM image path${nocolor}"; exit 1; }
	done
	# The variants are drop-in replacements for the plain driver: same SONAME, same dependencies.
	elfid(){ "$ndk/llvm-readelf" -d "$1" | grep -oP '(SONAME|NEEDED).*\[\K[^]]+' | sort | tr '\n' ' '; }
	plain_id="$(elfid libvulkan_freedreno_wayland.so)"
	for f in libvulkan_freedreno_wayland_a7xx.so libvulkan_freedreno_wayland_a8xx.so; do
		[ "$(elfid "$f")" = "$plain_id" ] || { echo -e "${red}$f: SONAME/NEEDED differ from the plain driver\n  plain: $plain_id\n  $f: $(elfid "$f")${nocolor}"; exit 1; }
	done
	# And each really carries its GPU table: names from freedreno_devices.py end up in fd_dev_recs.
	has(){ "$ndk/llvm-strings" "$1" | grep -qxF "$2"; }
	has libvulkan_freedreno_wayland_a7xx.so "FD710" && ! has libvulkan_freedreno_wayland.so "FD710" \
		|| { echo -e "${red}a7xx driver does not carry FD710 (or the plain one does)${nocolor}"; exit 1; }
	has libvulkan_freedreno_wayland_a8xx.so "Adreno (TM) 825" && ! has libvulkan_freedreno_wayland.so "Adreno (TM) 825" \
		|| { echo -e "${red}a8xx driver does not carry Adreno 825 (or the plain one does)${nocolor}"; exit 1; }
	echo "variant tables verified: a7xx has FD710, a8xx has Adreno (TM) 825, plain has neither"
	echo "== NEEDED / SONAME =="
	for f in *.so*; do
		[ -f "$f" ] || continue
		echo "$f: soname $("$ndk/llvm-readelf" -d "$f" | grep -oP 'SONAME.*\[\K[^]]+') needs $("$ndk/llvm-readelf" -d "$f" | grep -oP 'NEEDED.*\[\K[^]]+' | tr '\n' ' ')"
	done

	# The libraries, anything of this build they link, and the Termux libwayland they were linked
	# against.
	pkg="$workdir/banner-mesa-wayland"
	rm -rf "$pkg" && mkdir -p "$pkg/lib" "$pkg/share/vulkan/icd.d"
	cp -L libEGL.so.1 libGLESv2.so.2 $turnips libgallium-*.so "$pkg/lib/"
	# One ICD manifest per driver, from the one Mesa installed (right api_version), pointing at
	# lib/ relative to icd.d/ the way winewayland's bundled layout expects.
	python3 - "$out/usr/share/vulkan/icd.d" "$pkg/share/vulkan/icd.d" <<'PYICD'
import json, sys, glob, os
src = glob.glob(os.path.join(sys.argv[1], 'freedreno_icd*.json'))[0]
for lib, name in (('libvulkan_freedreno_wayland.so', 'banner_wayland_turnip.json'),
                  ('libvulkan_freedreno_wayland_a7xx.so', 'banner_wayland_turnip_a7xx.json'),
                  ('libvulkan_freedreno_wayland_a8xx.so', 'banner_wayland_turnip_a8xx.json')):
    m = json.load(open(src))
    m['ICD']['library_path'] = '../../../lib/' + lib
    m['ICD']['library_arch'] = '64'
    out = os.path.join(sys.argv[2], name)
    with open(out, 'w') as f:
        json.dump(m, f, indent=4)
        f.write('\n')
    print(name, '->', m['ICD']['library_path'], 'api', m['ICD']['api_version'])
PYICD
	for f in libEGL.so.1 libGLESv2.so.2 $turnips libgallium-*.so; do
		for n in $("$ndk/llvm-readelf" -d "$f" | grep -oP 'NEEDED.*\[\K[^]]+'); do
			[ -e "$n" ] && [ ! -e "$pkg/lib/$n" ] && cp -L "$n" "$pkg/lib/" && echo "bundled $n (needed by $f)"
		done
	done
	cp -L "$tprefix/lib/libwayland-client.so" "$tprefix/lib/libwayland-server.so" "$tprefix/lib/libwayland-egl.so" "$pkg/lib/"
	# libdrm comes from the Termux sysroot, not this build, so the NEEDED loop above misses it.
	cp -L "$tprefix/lib/libdrm.so" "$pkg/lib/"
	{
		echo "Mesa $(cat "$workdir/mesa/VERSION") at $mesa_hash (gitlab.freedesktop.org/mesa/mesa)."
		echo "Linux-style build on bionic like Termux's (Android detection off, Zink general layout off for Turnip)."
		echo "Built with $ndkver, API $api, for the Bannerlator imagefs."
		echo "Turnip: KGSL, Wayland WSI. OpenGL: EGL (Wayland platform) + Zink, no LLVM, no GLX."
		echo "Turnip variants (same tree and flags; ICD manifests in share/vulkan/icd.d):"
		echo "  lib/libvulkan_freedreno_wayland.so       plain            Adreno 6xx, 730/740/750"
		echo "  lib/libvulkan_freedreno_wayland_a7xx.so  patches/a710-720.py   Adreno 710/720/722"
		echo "  lib/libvulkan_freedreno_wayland_a8xx.so  patches/tu8_kgsl_26.patch + fix_a8xx_dev_info.py + apply_a8xx_gpus.py   Adreno 8xx"
		echo "Termux packages linked:"
		for p in $termux_pkgs; do awk -v P="$p" 'BEGIN{RS="";FS="\n"} {n="";v=""; for(i=1;i<=NF;i++){if($i~/^Package: /)n=substr($i,10); if($i~/^Version: /)v=substr($i,10)} if(n==P){print "  " n " " v; exit}}' "$workdir/Packages"; done
	} > "$pkg/BUILD-INFO.txt"
	cat "$pkg/BUILD-INFO.txt"
	ls -la "$pkg/lib" "$pkg/share/vulkan/icd.d"
	(cd "$workdir" && tar -czf banner-mesa-wayland.tar.gz banner-mesa-wayland)
	echo -e "${green}Built $workdir/banner-mesa-wayland.tar.gz${nocolor}"
}

prepare
build
package

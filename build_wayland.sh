#!/bin/bash -e
set -o pipefail
# Wayland variant: Turnip (KGSL) with the Wayland WSI, plus Mesa's EGL (Wayland platform) and Zink
# for OpenGL. It is meant for Wine's winewayland.drv running on the Bannerlator compositor, not for
# AdrenoTools: it's built for a Termux-style bionic userland (the Bannerlator imagefs) and links
# Termux's libwayland and libdrm.
#
# Four Turnip drivers come out of this build, each from its own Mesa pin, all with the same flags
# and the same Wayland changes on top (apply_wayland_patches); EGL + Zink come from the plain tree:
#   plain      Mesa mesa_hash.txt (the Android release's), no device patches   Adreno 6xx, 730/740/750
#   a7xx       Vauzi-17/710 release 3.6 recipe (add_710_720_722.py) on Mesa    Adreno 710/720/722
#              $mesa_a7xx_ref                     -> patches/upstream/vauzi-3.6/SOURCE.md
#   a8xx       WinNative-Emu/Drivers v1.15 (WN-Turnip 1.15) recipe on Mesa     Adreno 8xx
#              $mesa_a8xx_ref: build_wn_turnip.sh's EXTRA_SCRIPT set, then
#              apply_balance_variant.py (Balanced)  -> patches/upstream/winnative-v1.15/SOURCE.md
#   a8xx_perf  the same set, then apply_perf_variant.py (Performance: KGSL PWR_MAX constraint)
#   a8xx_gen8  this repo's own Android a8xx recipe (turnip_build_combined.yml, a8xx job):
#              patches/a8xx_gen8.patch (whitebelyash tu8 series) + patches/a8xx_shared_mem.py,
#              applied the way build_turnip.sh applies them; that job tracks Mesa main, so the
#              Wayland build pins it to the same commit as the WN-Turnip drivers ($mesa_a8xx_ref).
#   a8xx_smxz  StevenMXZ/Adreno-Tools-Drivers v36 "Turnip Gen8 V36": its build_turnip.sh seds on
#              upstream Mesa $mesa_smxz_ref, the commit the released binary embeds
#              (patches/upstream/smxz-v36/SOURCE.md on why not the fork branch the script names)
#   a8xx_white whitebelyash/freedreno_turnip-CI tu_v31 "Mainline Turnip v31": the mesa-unified
#              turnip/gen8 branch at $mesa_white_ref (fetched from that fork) + tu_version.h v31,
#              the primary asset (patches/upstream/white-tu_v31/SOURCE.md)
#   a8xx_upstream  pure upstream Mesa main at $mesa_upstream_ref (the head when this was pinned),
#              nothing but the Wayland changes: the reference for what upstream gives 8xx today.
# winewayland picks one through BANNER_WAYLAND_VK_VARIANT (proton-wine android/wayland-deps/TURNIP.md).

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

# The community recipes, each at the Mesa commit its release was built from (see the SOURCE.md
# next to each vendored copy for how the commit was established).
vz="$repo/patches/upstream/vauzi-3.6"
vz_tag="Vauzi-17/710 release 3.6 (tag commit 5db89bde562d2bb89d39b016ddf8b25f6d3bf309)"
mesa_a7xx_ref="7631b5254f1a0a4371f5594e630ce2f2b8394e73"
wn="$repo/patches/upstream/winnative-v1.15"
wn_tag="WinNative-Emu/Drivers v1.15 (tag commit 8407c8012d7b3096621becec73d836f4fbe7b3ce)"
mesa_a8xx_ref="12b7b819edb4ddd3580e7e5ffe384610ae726c90"
# build_wn_turnip.sh's EXTRA_SCRIPT, in its order. The gralloc / aimapper / UBWC-swapchain ones
# are Android-side (files this build does not compile); they may apply, they may not.
wn_scripts="fix_gralloc_flushall.py fix_a8xx_dev_info.py apply_a8xx_gpus.py apply_a7xx_gen1_quirks.py apply_a7xx_gen2_ubwc_hint.py add_aimapper_gralloc.py add_ubwc_swapchain_usage.py"
# These are the driver: they must apply and must change the tree.
wn_required="fix_a8xx_dev_info.py apply_a8xx_gpus.py apply_a7xx_gen1_quirks.py apply_a7xx_gen2_ubwc_hint.py"
# The Android release's own a8xx recipe; its job clones Mesa main unpinned, this build pins it.
mesa_gen8_ref="$mesa_a8xx_ref"
smxz="$repo/patches/upstream/smxz-v36"
smxz_tag="StevenMXZ/Adreno-Tools-Drivers v36 (tag commit 50cbd613e7f6f10e6bc36cfde51e9c76c23a441d)"
mesa_smxz_ref="c501e1d16e11c256610cd5922b1afa5660f2f5ea"
white="$repo/patches/upstream/white-tu_v31"
white_tag="whitebelyash/freedreno_turnip-CI tu_v31 (tag commit 258fc21943dc3cab448bc53d1566a5f699283cf4)"
mesa_white_ref="9c475fc367a7283a7eee58501fb48149780f2c1e"
mesa_white_remote="https://github.com/whitebelyash/mesa-unified.git"
# Pure upstream, pinned to the mesa/mesa main head at the time of pinning (bump deliberately).
mesa_upstream_ref="bbc7792f717f27b17b4c12e6a4503d703a362aac"
mesa_upstream_date="2026-09-13T15:39:30Z"

fetch_mesa(){	# <dir> <ref> [remote]: a shallow checkout of one Mesa commit, tagged so it can be reset to.
	local dir="$1" ref="$2" remote="${3:-https://gitlab.freedesktop.org/mesa/mesa.git}"
	if [ ! -d "$dir" ]; then
		echo "Fetching Mesa $ref from $remote into $dir..."
		git init -q "$dir"
		git -C "$dir" remote add origin "$remote"
		git -C "$dir" fetch -q --depth=1 origin "$ref"
		git -C "$dir" checkout -q FETCH_HEAD
	fi
	# The shared patches get committed on top of this so each variant can start from them cleanly.
	git -C "$dir" rev-parse -q --verify banner-base >/dev/null 2>&1 || git -C "$dir" tag banner-base HEAD
}

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

	fetch_mesa mesa "$mesa_hash"
	fetch_mesa mesa-a7xx "$mesa_a7xx_ref"
	fetch_mesa mesa-a8xx "$mesa_a8xx_ref"
	fetch_mesa mesa-a8xx-gen8 "$mesa_gen8_ref"
	fetch_mesa mesa-a8xx-smxz "$mesa_smxz_ref"
	fetch_mesa mesa-a8xx-white "$mesa_white_ref" "$mesa_white_remote"
	fetch_mesa mesa-a8xx-upstream "$mesa_upstream_ref"
}

# The Wayland-on-bionic changes every driver here gets, committed on top of the checkout so a
# variant is exactly "these + its own recipe" and git diff shows only the recipe's part.
apply_wayland_patches(){	# <dir>
	cd "$workdir/$1"
	# This is a Linux-style build on bionic (like Termux's Mesa), not an Android-platform one: turn
	# off Mesa's Android detection, as Termux does (their 0000/0002 patches), and keep Turnip out of
	# Zink's general-layout path (their 0018: rendering artifacts on Adreno).
	git reset -q --hard banner-base
	sed -i 's/^#if defined(__ANDROID__)$/#if 0 \/* Linux-style build on bionic *\//' src/util/detect_os.h
	sed -i 's/^#if defined(__ANDROID__) || defined(ANDROID)$/#if 0 \/* Linux-style build on bionic *\//' include/vulkan/vk_android_native_buffer.h
	sed -i '/^#elif\|^#if/s/DETECT_OS_ANDROID/defined(__ANDROID__)/' src/util/u_process.c
	grep -n "Linux-style build on bionic" src/util/detect_os.h include/vulkan/vk_android_native_buffer.h
	# OpenGL must take EGL's Wayland *DRM* path, not its shm/swrast one. Only the DRM initialiser
	# asks zwp_linux_dmabuf_v1 for its default feedback (version >= 4, which the compositor has
	# advertised since 2026-09-13), takes a render node out of the feedback's main_device, and so
	# reaches driver_name = "zink" with kopper = true: GL on the GPU, presenting through Zink's own
	# Vulkan WSI (this build's Turnip, zero-copy patch included). The swrast initialiser has no
	# dmabuf branch at any version and this gallium build has no rasteriser at all (zink only,
	# -Dllvm=disabled), so a display that lands there commits never-written shm buffers: native
	# OpenGL windows were solid black on Wayland from the first build until 2026-09-13. Up to then
	# this script forced exactly that, with "|| disp->Options.Zink" bolted onto the dispatcher (the
	# kopper design it intended cannot work there: the swrast path leaves fd_render_gpu at -1 and
	# dri2_setup_device then refuses the display unless ForceSoftware is on, and ForceSoftware makes
	# Zink demand a CPU Vulkan device). The shortcut is gone; what is left is the assert that
	# upstream's dispatcher still has the shape that reasoning is built on.
	python3 - <<'PY'
import sys
p = 'src/egl/drivers/dri2/platform_wayland.c'
s = open(p).read()
stock = ("   if (disp->Options.ForceSoftware)\n"
         "      return dri2_initialize_wayland_swrast(disp);\n"
         "   else\n"
         "      return dri2_initialize_wayland_drm(disp);")
if stock not in s:
    sys.exit("egl: dri2_initialize_wayland is not the stock two-way dispatcher at this Mesa ref - "
             "establish which path a Zink display takes before shipping this driver")
# The DRM path is only worth anything if it still reads the feedback we send; MIN2(version, 4) is
# what makes it bind our version 4 global.
for marker in ("zwp_linux_dmabuf_v1_get_default_feedback(",
               "MIN2(version, ZWP_LINUX_DMABUF_V1_GET_DEFAULT_FEEDBACK_SINCE_VERSION)"):
    if marker not in s:
        sys.exit("egl: platform_wayland.c no longer has %s - the compositor's dmabuf feedback is "
                 "how this driver finds a render node" % marker)
print("egl: Zink on Wayland takes the DRM path (dmabuf feedback -> render node -> zink + kopper)")
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
	# Bannerlator zero-copy window layers: with BANNER_WSI_AHB=1 (and the compositor's banner_ahb_v1
	# global) the Wayland swapchain's images are gralloc AHardwareBuffers the compositor can put on a
	# SurfaceControl layer without a copy. Runtime-gated: without the variable the WSI is unchanged.
	python3 "$repo/patches/wayland/banner_ahb_wsi.py" . \
		|| { echo -e "${red}wsi wayland: banner_ahb_wsi.py did not apply${nocolor}"; exit 1; }
	git -c user.name=banners-turnip -c user.email=build@banners-turnip commit -q -am "Wayland build: shared patches"
	git tag -f banner-wayland >/dev/null
}

# Run one recipe script from the current Mesa checkout, the way its own build does (cwd = Mesa
# root, scripts take relative paths). The community scripts never fail on a missing anchor, they
# log a warning and go on; for the scripts that ARE the driver that is not acceptable here, so a
# required script must neither report a missing anchor nor leave the tracked tree unchanged.
run_script(){	# <label> <required 0|1> <script> [VAR=value ...]
	local label="$1" required="$2" script="$3"; shift 3
	local log="$workdir/log-$label-$(basename "$script").txt" before after
	before="$(git diff | sha256sum)"
	echo "[$label] running $(basename "$script")"
	env "$@" python3 "$script" 2>&1 | sed 's/^/    /' | tee "$log" \
		|| { echo -e "${red}[$label] $(basename "$script") failed${nocolor}"; exit 1; }
	if [ "$required" = 1 ]; then
		# The autotune drawcall gate is one upstream restructured away on purpose; WinNative's own
		# verify_patches.sh tolerates exactly that line.
		if [ -n "$(grep -E 'WARNING|anchor absent|not matched|FATAL|skipping' "$log" | grep -v 'drawcall anchor absent' || true)" ]; then
			echo -e "${red}[$label] $(basename "$script") reported a missing anchor, refusing to ship this variant${nocolor}"; exit 1
		fi
		after="$(git diff | sha256sum)"
		[ "$after" != "$before" ] || { echo -e "${red}[$label] $(basename "$script") changed nothing, refusing to ship this variant${nocolor}"; exit 1; }
	fi
}

write_meson_files(){
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
}

# freedreno-kmds MUST list msm as well as kgsl: with kgsl alone Mesa's top-level meson decides
# the system has no KMS/DRM, drops libdrm, and does not compile wsi_common_drm.c. The Wayland
# WSI still builds DRM-type images for every real device, so vkCreateSwapchainKHR then runs into
# a compiled-out branch (unreachable) and the guest dies with an access violation. Termux builds
# msm,kgsl; msm just finds no /dev/dri at runtime.
configure(){	# <mesa dir> <build dir>
	cd "$workdir/$1"
	meson setup "$2" \
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
}

build_turnip(){	# <mesa dir> <build dir> <output name>: only the Turnip target of a variant tree.
	configure "$1" "$2"
	ninja -C "$workdir/$1/$2" src/freedreno/vulkan/libvulkan_freedreno.so
	cp -L "$workdir/$1/$2/src/freedreno/vulkan/libvulkan_freedreno.so" "$out/usr/lib/$3"
}

build(){
	# Termux's x86_64 wayland-scanner (the libwayland version) ahead of any system one.
	export PATH="$tprefix/opt/libwayland/cross/bin:$PATH"
	wayland-scanner --version
	export CFLAGS="-Wno-error -Wno-deprecated-declarations -Wno-incompatible-pointer-types-discards-qualifiers -Wno-incompatible-pointer-types"
	export CXXFLAGS="$CFLAGS"
	write_meson_files

	# plain: the whole thing (Turnip + EGL + Zink), installed.
	apply_wayland_patches mesa
	configure mesa build-wayland
	ninja -C "$workdir/mesa/build-wayland"
	rm -rf "$out" && DESTDIR="$out" ninja -C "$workdir/mesa/build-wayland" install
	cp -L "$workdir/mesa/build-wayland/src/freedreno/vulkan/libvulkan_freedreno.so" "$out/usr/lib/libvulkan_freedreno_wayland.so"

	# a7xx: Vauzi-17/710 3.6.
	apply_wayland_patches mesa-a7xx
	run_script a7xx 1 "$vz/add_710_720_722.py"
	echo "[a7xx] recipe changes against the Wayland tree:"; git --no-pager diff --stat banner-wayland
	build_turnip mesa-a7xx build-wayland-a7xx libvulkan_freedreno_wayland_a7xx.so
	git checkout -q -- .

	# a8xx: WinNative v1.15, the common set once, then each tuning on top of it.
	apply_wayland_patches mesa-a8xx
	for s in $wn_scripts; do
		req=0; case " $wn_required " in *" $s "*) req=1;; esac
		run_script a8xx $req "$wn/patches/$s"
	done
	echo "[a8xx] WN-Turnip common changes against the Wayland tree:"
	git add -A src/util/u_gralloc		# add_aimapper_gralloc.py drops a new source in
	git --no-pager diff --stat HEAD
	git -c user.name=banners-turnip -c user.email=build@banners-turnip commit -q -am "WN-Turnip 1.15: common scripts"
	run_script a8xx 1 "$wn/patches/apply_balance_variant.py"
	echo "[a8xx] Balanced:"; git --no-pager diff --stat
	build_turnip mesa-a8xx build-wayland-a8xx libvulkan_freedreno_wayland_a8xx.so
	git checkout -q -- .
	run_script a8xx_perf 1 "$wn/patches/apply_perf_variant.py" BUILD_VARIANT=p
	for line in "KGSL_CONTEXT_PWR_CONSTRAINT to context flags" "PWR_MAX helper" "initial PWR_MAX constraint setup" "KGSL_CMDBATCH_PWR_CONSTRAINT" "periodic PWR_MAX refresh"; do
		grep -qF "$line" "$workdir/log-a8xx_perf-apply_perf_variant.py.txt" \
			|| { echo -e "${red}[a8xx_perf] '$line' never reported: no PWR_MAX clock forcing${nocolor}"; exit 1; }
	done
	echo "[a8xx_perf] Performance:"; git --no-pager diff --stat
	build_turnip mesa-a8xx build-wayland-a8xx_perf libvulkan_freedreno_wayland_a8xx_perf.so
	git checkout -q -- .

	# a8xx_gen8: the Android a8xx job, mirrored from build_turnip.sh: the patch series with
	# -N --fuzz=4 (rejects tolerated there, listed here), freedreno_devices.py reset if the series
	# left it unparsable, the script, then its NDK r29 seds (Android-only files, harmless here).
	apply_wayland_patches mesa-a8xx-gen8
	echo "[a8xx_gen8] applying patches/a8xx_gen8.patch"
	patch -p1 -N --fuzz=4 < "$repo/patches/a8xx_gen8.patch" 2>&1 | sed 's/^/    /' | tee "$workdir/log-a8xx_gen8-a8xx_gen8.patch.txt" \
		|| echo -e "${red}[a8xx_gen8] partial patch failures (build_turnip.sh continues here too)${nocolor}"
	rejects="$(git status --porcelain --untracked-files=all | grep '\.rej$' || true)"
	[ -z "$rejects" ] || { echo "[a8xx_gen8] rejected hunks:"; echo "$rejects"; }
	if ! python3 -c "compile(open('src/freedreno/common/freedreno_devices.py').read(),'f','exec')" 2>/dev/null; then
		echo -e "${red}[a8xx_gen8] freedreno_devices.py has syntax errors after patching — resetting (as build_turnip.sh does)${nocolor}"
		git checkout -- src/freedreno/common/freedreno_devices.py
	fi
	run_script a8xx_gen8 1 "$repo/patches/a8xx_shared_mem.py"
	sed -i 's/typedef const native_handle_t\* buffer_handle_t;/typedef void\* buffer_handle_t;/g' include/android_stub/cutils/native_handle.h || true
	sed -i 's/, hnd->handle/, (void \*)hnd->handle/g' src/util/u_gralloc/u_gralloc_fallback.c || true
	sed -i -E 's/([a-z_]+)->handle->/((const native_handle_t *)\1->handle)->/g' src/vulkan/runtime/vk_android.c || true
	echo "[a8xx_gen8] recipe changes against the Wayland tree:"; git --no-pager diff --stat banner-wayland
	# The series is the driver: its device table and its deck_emu debug option must have landed.
	grep -q 'name="Adreno (TM) 825"' src/freedreno/common/freedreno_devices.py && grep -q 'deck_emu' src/freedreno/vulkan/tu_util.cc \
		|| { echo -e "${red}[a8xx_gen8] the gen8 series did not land its A825 entry / deck_emu option, refusing to ship it${nocolor}"; exit 1; }
	build_turnip mesa-a8xx-gen8 build-wayland-a8xx_gen8 libvulkan_freedreno_wayland_a8xx_gen8.so
	git checkout -q -- .

	# a8xx_smxz: the v36 build_turnip.sh's edits, verbatim, on the upstream commit the release
	# embeds (it applies no patch files). The a7xx_gen1 line is the whole recipe here: assert it.
	apply_wayland_patches mesa-a8xx-smxz
	echo "[a8xx_smxz] applying the v36 build_turnip.sh seds"
	echo '#define TUGEN8_DRV_VERSION ""' > ./src/freedreno/vulkan/tu_version.h
	sed -i 's/ (%s)//g' src/freedreno/vulkan/tu_device.cc || true
	sed -i 's/ (%s)//g' src/freedreno/vulkan/tu_device.c || true
	sed -i '/a7xx_gen1 = GPUProps(/a \        has_early_preamble = False,' src/freedreno/common/freedreno_devices.py || true
	sed -i 's/typedef const native_handle_t\* buffer_handle_t;/typedef void\* buffer_handle_t;/g' include/android_stub/cutils/native_handle.h || true
	sed -i 's/, hnd->handle/, (void \*)hnd->handle/g' src/util/u_gralloc/u_gralloc_fallback.c || true
	sed -i 's/native_buffer->handle->/((const native_handle_t \*)native_buffer->handle)->/g' src/vulkan/runtime/vk_android.c || true
	sed -i 's/anb->handle->/((const native_handle_t \*)anb->handle)->/g' src/vulkan/runtime/vk_android.c || true
	grep -A1 '^a7xx_gen1 = GPUProps(' src/freedreno/common/freedreno_devices.py | grep -q 'has_early_preamble = False' \
		|| { echo -e "${red}[a8xx_smxz] has_early_preamble = False did not land on a7xx_gen1, refusing to ship it${nocolor}"; exit 1; }
	python3 -c "compile(open('src/freedreno/common/freedreno_devices.py').read(),'f','exec')"
	echo "[a8xx_smxz] recipe changes against the Wayland tree:"; git --no-pager diff --stat banner-wayland
	build_turnip mesa-a8xx-smxz build-wayland-a8xx_smxz libvulkan_freedreno_wayland_a8xx_smxz.so
	git checkout -q -- .

	# a8xx_white: the fork branch is the recipe; turnip_builder.sh only stamps the version.
	apply_wayland_patches mesa-a8xx-white
	echo "[a8xx_white] TUGEN8_DRV_VERSION v31 (turnip_builder.sh)"
	echo '#define TUGEN8_DRV_VERSION "v31"' > ./src/freedreno/vulkan/tu_version.h
	grep -q 'name="Adreno (TM) 812"' src/freedreno/common/freedreno_devices.py && grep -q 'TUGEN8_DRV_VERSION' src/freedreno/vulkan/tu_device.cc \
		|| { echo -e "${red}[a8xx_white] this is not the mesa-unified turnip/gen8 tree (no Adreno 812 / TUGEN8_DRV_VERSION), refusing${nocolor}"; exit 1; }
	echo "[a8xx_white] recipe changes against the Wayland tree:"; git --no-pager diff --stat banner-wayland
	build_turnip mesa-a8xx-white build-wayland-a8xx_white libvulkan_freedreno_wayland_a8xx_white.so
	git checkout -q -- .

	# a8xx_upstream: nothing on top of the Wayland changes.
	apply_wayland_patches mesa-a8xx-upstream
	echo "[a8xx_upstream] Mesa main $mesa_upstream_ref ($mesa_upstream_date), no device patches"
	build_turnip mesa-a8xx-upstream build-wayland-a8xx_upstream libvulkan_freedreno_wayland_a8xx_upstream.so
}

package(){
	cd "$out/usr/lib"
	ls -la
	# This cross build names the libraries without a version; Wine opens libEGL.so.1.
	[ -e libEGL.so.1 ] || cp -L libEGL.so libEGL.so.1
	[ -e libGLESv2.so.2 ] || cp -L libGLESv2.so libGLESv2.so.2
	turnips="libvulkan_freedreno_wayland.so libvulkan_freedreno_wayland_a7xx.so libvulkan_freedreno_wayland_a8xx.so libvulkan_freedreno_wayland_a8xx_perf.so libvulkan_freedreno_wayland_a8xx_gen8.so libvulkan_freedreno_wayland_a8xx_smxz.so libvulkan_freedreno_wayland_a8xx_white.so libvulkan_freedreno_wayland_a8xx_upstream.so"
	for f in libEGL.so.1 libGLESv2.so.2 $turnips libgallium-*.so; do
		[ -e "$f" ] || { echo -e "${red}missing $f${nocolor}"; exit 1; }
	done
	# The ICD must carry the DRM image path (see the freedreno-kmds note): fail loudly if it does not.
	for f in $turnips; do
		"$ndk/llvm-readelf" -d "$f" | grep "libdrm.so" >/dev/null || { echo -e "${red}$f does not link libdrm: the Wayland WSI has no DRM image path${nocolor}"; exit 1; }
	done
	# The variants are drop-in replacements for the plain driver: same SONAME, same dependencies.
	elfid(){ "$ndk/llvm-readelf" -d "$1" | grep -oP '(SONAME|NEEDED).*\[\K[^]]+' | sort | tr '\n' ' '; }
	plain_id="$(elfid libvulkan_freedreno_wayland.so)"
	for f in $turnips; do
		[ "$(elfid "$f")" = "$plain_id" ] || { echo -e "${red}$f: SONAME/NEEDED differ from the plain driver\n  plain: $plain_id\n  $f: $(elfid "$f")${nocolor}"; exit 1; }
	done
	# And each really carries its recipe: GPU names from freedreno_devices.py end up in fd_dev_recs,
	# the Performance tuning has its own log strings.
	# Not grep -q: under pipefail an early exit gives llvm-strings SIGPIPE and the check "fails".
	has(){ "$ndk/llvm-strings" "$1" | grep -F "$2" >/dev/null; }
	# On a failed check, show what GPU names / tuning strings each driver does carry.
	names(){ echo "  $1: $("$ndk/llvm-strings" "$1" | grep -E '^(FD[0-9]{3}|Adreno \(TM\) [0-9X-]+|Adreno X[0-9-]+|WN-Turnip:.*)$' | sort -u | tr '\n' '|')"; }
	fail_strings(){ echo -e "${red}$1${nocolor}"; for g in $turnips; do names "$g"; done; exit 1; }
	only_in(){	# <string> <the one file that must have it> <others that must have it too>; the rest must not
		local s="$1" f="$2" g
		has "$f" "$s" || fail_strings "$f does not carry '$s'"
		for g in $turnips; do
			[ "$g" = "$f" ] && continue
			case " $3 " in *" $g "*) has "$g" "$s" || fail_strings "$g does not carry '$s'"; continue;; esac
			has "$g" "$s" && fail_strings "$g carries '$s', which belongs to $f"
		done
		return 0
	}
	only_in "FD710" libvulkan_freedreno_wayland_a7xx.so "libvulkan_freedreno_wayland_a8xx_white.so"
	only_in "Adreno (TM) 825" libvulkan_freedreno_wayland_a8xx.so "libvulkan_freedreno_wayland_a8xx_perf.so libvulkan_freedreno_wayland_a8xx_gen8.so libvulkan_freedreno_wayland_a8xx_white.so"
	only_in "WN-Turnip: Failed to set initial PWR_MAX constraint" libvulkan_freedreno_wayland_a8xx_perf.so ""
	only_in "deck_emu" libvulkan_freedreno_wayland_a8xx_gen8.so "libvulkan_freedreno_wayland_a8xx_white.so"
	only_in "Adreno (TM) 812" libvulkan_freedreno_wayland_a8xx_white.so ""
	only_in "whitebelyash branch" libvulkan_freedreno_wayland_a8xx_white.so ""
	# (Not the " (v31)" device-name suffix: clang folds that 6-byte strcat literal into immediates,
	# so it never reaches .rodata; the 812 entry and the driverInfo string above are the markers.)
	# The SMXZ recipe has no textual marker (one Python-level prop on upstream): it must at least
	# be its own binary, and the WN tunings must differ from each other.
	for g in $turnips; do
		[ "$g" = libvulkan_freedreno_wayland_a8xx_smxz.so ] && continue
		cmp -s libvulkan_freedreno_wayland_a8xx_smxz.so "$g" && { echo -e "${red}a8xx_smxz is byte-identical to $g${nocolor}"; exit 1; }
	done
	cmp -s libvulkan_freedreno_wayland_a8xx.so libvulkan_freedreno_wayland_a8xx_perf.so && { echo -e "${red}a8xx and a8xx_perf are the same file${nocolor}"; exit 1; }
	# a8xx_upstream: upstream's own 8xx table (840 is upstream's, also in plain) and a different
	# Mesa tree than plain: not the same bytes, and a different embedded Mesa git string.
	has libvulkan_freedreno_wayland_a8xx_upstream.so "Adreno (TM) 840" || fail_strings "a8xx_upstream does not carry upstream's Adreno (TM) 840 entry"
	cmp -s libvulkan_freedreno_wayland_a8xx_upstream.so libvulkan_freedreno_wayland.so && { echo -e "${red}a8xx_upstream is byte-identical to plain${nocolor}"; exit 1; }
	gitstr(){ "$ndk/llvm-strings" "$1" | grep -oE '26\.[0-9]+\.[0-9]+-devel \(git-[0-9a-f]+\)' | head -1; }
	echo "Mesa strings: plain '$(gitstr libvulkan_freedreno_wayland.so)' upstream '$(gitstr libvulkan_freedreno_wayland_a8xx_upstream.so)'"
	[ -n "$(gitstr libvulkan_freedreno_wayland_a8xx_upstream.so)" ] && [ "$(gitstr libvulkan_freedreno_wayland_a8xx_upstream.so)" != "$(gitstr libvulkan_freedreno_wayland.so)" ] \
		|| { echo -e "${red}a8xx_upstream and plain carry the same Mesa git string${nocolor}"; exit 1; }
	echo "variant tables verified: FD710 in a7xx + a8xx_white; Adreno (TM) 825 in a8xx + a8xx_perf + a8xx_gen8 + a8xx_white; PWR_MAX only in a8xx_perf; deck_emu in a8xx_gen8 + a8xx_white; Adreno 812 / whitebelyash branch only in a8xx_white; a8xx_smxz distinct; a8xx_upstream has Adreno 840 and its own Mesa string"
	# Every driver carries the zero-copy WSI (the private protocol's interface name is its marker).
	for f in $turnips; do
		has "$f" "banner_ahb_v1" || fail_strings "$f does not carry the banner_ahb_v1 zero-copy WSI"
	done
	echo "zero-copy WSI (banner_ahb_v1) present in every driver"
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
                  ('libvulkan_freedreno_wayland_a8xx.so', 'banner_wayland_turnip_a8xx.json'),
                  ('libvulkan_freedreno_wayland_a8xx_perf.so', 'banner_wayland_turnip_a8xx_perf.json'),
                  ('libvulkan_freedreno_wayland_a8xx_gen8.so', 'banner_wayland_turnip_a8xx_gen8.json'),
                  ('libvulkan_freedreno_wayland_a8xx_smxz.so', 'banner_wayland_turnip_a8xx_smxz.json'),
                  ('libvulkan_freedreno_wayland_a8xx_white.so', 'banner_wayland_turnip_a8xx_white.json'),
                  ('libvulkan_freedreno_wayland_a8xx_upstream.so', 'banner_wayland_turnip_a8xx_upstream.json')):
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
		echo "Zero-copy layers: with BANNER_WSI_AHB=1 and a compositor advertising banner_ahb_v1, swapchain images are"
		echo "  gralloc AHardwareBuffers handed to the compositor (patches/wayland/banner_ahb_wsi.py); off = unchanged WSI."
		echo "Turnip drivers (same flags and Wayland changes; ICD manifests in share/vulkan/icd.d):"
		echo "  lib/libvulkan_freedreno_wayland.so           plain: Mesa $mesa_hash, no device patches"
		echo "                                               Adreno 6xx, 730/740/750"
		echo "  lib/libvulkan_freedreno_wayland_a7xx.so      $vz_tag"
		echo "                                               add_710_720_722.py on Mesa $mesa_a7xx_ref"
		echo "                                               Adreno 710/720/722 (their README: TU_DEBUG=sysmem recommended)"
		echo "  lib/libvulkan_freedreno_wayland_a8xx.so      $wn_tag"
		echo "                                               build_wn_turnip.sh EXTRA_SCRIPT set + apply_balance_variant.py (Balanced)"
		echo "                                               on Mesa $mesa_a8xx_ref; Adreno 8xx"
		echo "  lib/libvulkan_freedreno_wayland_a8xx_perf.so the same + apply_perf_variant.py (Performance: KGSL PWR_MAX constraint)"
		echo "  lib/libvulkan_freedreno_wayland_a8xx_gen8.so Banners-Turnip Android a8xx recipe (turnip_build_combined.yml a8xx job):"
		echo "                                               patches/a8xx_gen8.patch + patches/a8xx_shared_mem.py on Mesa $mesa_gen8_ref"
		echo "                                               (that job tracks Mesa main; pinned here to the WN-Turnip commit); Adreno 8xx"
		echo "  lib/libvulkan_freedreno_wayland_a8xx_smxz.so $smxz_tag"
		echo "                                               v36 build_turnip.sh seds (has_early_preamble=False on a7xx_gen1) on upstream Mesa $mesa_smxz_ref"
		echo "                                               (the commit the released binary embeds; the script's fork branch is April 2026); Adreno 8xx as upstream"
		echo "  lib/libvulkan_freedreno_wayland_a8xx_white.so $white_tag"
		echo "                                               mesa-unified turnip/gen8 at $mesa_white_ref + TUGEN8_DRV_VERSION v31 (primary asset, no 39751.diff)"
		echo "                                               Adreno 840/830/829/825/812/810 + 710/720/722 (sysmem only) + upstream 6xx/7xx"
		echo "  lib/libvulkan_freedreno_wayland_a8xx_upstream.so pure upstream: Mesa main @ $mesa_upstream_ref ($mesa_upstream_date), no device patches"
		echo "                                               Adreno 8xx as upstream (810/829/830/840/X2) + everything upstream lists"
		echo "Termux packages linked:"
		for p in $termux_pkgs; do awk -v P="$p" 'BEGIN{RS="";FS="\n"} {n="";v=""; for(i=1;i<=NF;i++){if($i~/^Package: /)n=substr($i,10); if($i~/^Version: /)v=substr($i,10)} if(n==P){print "  " n " " v; exit}}' "$workdir/Packages"; done
	} > "$pkg/BUILD-INFO.txt"
	cat "$pkg/BUILD-INFO.txt"
	# The recipe logs travel with the drivers: they are the evidence of what each script changed.
	mkdir -p "$pkg/recipe-logs" && cp "$workdir"/log-*.txt "$pkg/recipe-logs/"
	if [ -n "$GITHUB_STEP_SUMMARY" ]; then
		{ echo '```'; cat "$pkg/BUILD-INFO.txt"; echo '```'; } >> "$GITHUB_STEP_SUMMARY"
	fi
	ls -la "$pkg/lib" "$pkg/share/vulkan/icd.d"
	(cd "$workdir" && tar -czf banner-mesa-wayland.tar.gz banner-mesa-wayland)
	echo -e "${green}Built $workdir/banner-mesa-wayland.tar.gz${nocolor}"
}

prepare
build
package

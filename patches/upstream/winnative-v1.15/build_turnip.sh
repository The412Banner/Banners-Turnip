#!/bin/bash -e

green='\033[0;32m'
red='\033[0;31m'
nocolor='\033[0m'
deps="git meson ninja patchelf unzip curl pip flex bison zip glslang glslangValidator"
workdir="$(pwd)/turnip_workdir"
ndkver="android-ndk-r26d"
if [ -n "${ANDROID_NDK_HOME:-}" ]; then
	ndk="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin"
elif [ -n "${NDK_BIN:-}" ]; then
	ndk="$NDK_BIN"
else
	ndk="/home/max/Build/Turnip/$ndkver/toolchains/llvm/prebuilt/linux-x86_64/bin"
fi
sdkver="34"
mesasrc="https://gitlab.freedesktop.org/mesa/mesa"
srcfolder="mesa"
MESA_COMMIT="$(cat mesa_hash.txt | tr -d '[:space:]')"

# BUILD_VARIANT should be one of: b, p, p1, p2
BUILD_VARIANT="${BUILD_VARIANT:-b}"

run_all(){
	echo -e "${green}====== Begin building WN-Turnip v${BUILD_VERSION}-${BUILD_VARIANT} Axxx! ======${nocolor}"
	check_deps
	prepare_workdir

	build_lib_for_android main
}

check_deps(){
	echo "Checking system for required Dependencies ..."
	for deps_chk in $deps; do
		if command -v "$deps_chk" >/dev/null 2>&1 ; then
			echo -e "$green - $deps_chk found $nocolor"
		else
			echo -e "$red - $deps_chk not found, can't continue. $nocolor"
			deps_missing=1
		fi
	done

	if [ "$deps_missing" == "1" ]; then
		echo "Please install missing dependencies" && exit 1
	fi

	echo "Installing python Mako dependency..."
	pip install mako &> /dev/null || true
}

prepare_workdir(){
	echo "Preparing work directory..."
	mkdir -p "$workdir" && cd "$_"

	# If MESA_LOCAL_SRC points at an existing mesa checkout, clone from it (fast). Otherwise clone upstream.
	# If MESA_PIN_COMMIT is set, fetch that exact commit and check it out (used by bisect).
	rm -rf $srcfolder
	if [ -n "$MESA_LOCAL_SRC" ] && [ -d "$MESA_LOCAL_SRC/.git" ]; then
		echo "Cloning mesa source from local checkout: $MESA_LOCAL_SRC"
		if [ -n "$MESA_PIN_COMMIT" ]; then
			git clone --no-local --shared "$MESA_LOCAL_SRC" $srcfolder
			cd $srcfolder
			git fetch origin "$MESA_PIN_COMMIT" 2>/dev/null || true
			git -c advice.detachedHead=false checkout "$MESA_PIN_COMMIT"
		else
			git clone --depth=1 --no-local --shared "$MESA_LOCAL_SRC" $srcfolder
			cd $srcfolder
		fi
	else
		echo "Cloning fresh mesa source..."
		git clone $mesasrc --depth=1 -b main $srcfolder
		cd $srcfolder
		if [ -n "$MESA_PIN_COMMIT" ]; then
			git fetch origin "$MESA_PIN_COMMIT"
			git -c advice.detachedHead=false checkout "$MESA_PIN_COMMIT"
		fi
	fi
	MESA_COMMIT=$(git rev-parse HEAD)
	echo $MESA_COMMIT > ../../mesa_hash.txt
	cd ..
}

build_lib_for_android(){
	cd "$workdir/$srcfolder"
	echo "==== Building Mesa on $1 branch ===="
	# Apply optional patches if EXTRA_PATCH is set. Accepts a single path or a colon-separated list.
	if [ -n "$EXTRA_PATCH" ]; then
		IFS=':' read -ra PATCHES <<< "$EXTRA_PATCH"
		for PATCH in "${PATCHES[@]}"; do
			if [ -f "../../$PATCH" ]; then
				echo "Applying patch: $PATCH"
				patch -p1 -N --fuzz=4 < "../../$PATCH" || echo -e "${red}Warning: partial patch failures in $PATCH, continuing...${nocolor}"
			else
				echo -e "${red}Warning: patch file not found: $PATCH${nocolor}"
			fi
		done
	fi

	# Apply optional Python scripts if EXTRA_SCRIPT is set (colon-separated list)
	if [ -n "$EXTRA_SCRIPT" ]; then
		if ! python3 -c "compile(open('src/freedreno/common/freedreno_devices.py').read(),'f','exec')" 2>/dev/null; then
			echo -e "${red}freedreno_devices.py has syntax errors after patching — resetting${nocolor}"
			git checkout -- src/freedreno/common/freedreno_devices.py
		fi
		IFS=':' read -ra SCRIPTS <<< "$EXTRA_SCRIPT"
		for SCRIPT in "${SCRIPTS[@]}"; do
			if [ -f "../../$SCRIPT" ]; then
				echo "Running script: $SCRIPT"
				python3 "../../$SCRIPT" || { echo -e "${red}Script $SCRIPT failed, aborting!${nocolor}"; exit 1; }
			fi
		done
	fi

	# Apply variant-specific changes via Python scripts (more reliable than patches)
	if [[ "$BUILD_VARIANT" == "p" || "$BUILD_VARIANT" == "p1" || "$BUILD_VARIANT" == "p2" ]] && [ -f "../../patches/apply_perf_variant.py" ]; then
		echo "Applying performance variant scripts..."
		python3 "../../patches/apply_perf_variant.py" || { echo -e "${red}Perf variant script failed!${nocolor}"; exit 1; }
	elif [ "$BUILD_VARIANT" == "b" ] && [ -f "../../patches/apply_balance_variant.py" ]; then
		echo "Applying balance variant scripts..."
		python3 "../../patches/apply_balance_variant.py" || { echo -e "${red}Balance variant script failed!${nocolor}"; exit 1; }
	fi

	# Preventive fixes for NDK r29 compilation
	sed -i 's/typedef const native_handle_t\* buffer_handle_t;/typedef void\* buffer_handle_t;/g' include/android_stub/cutils/native_handle.h || true
	sed -i 's/, hnd->handle/, (void \*)hnd->handle/g' src/util/u_gralloc/u_gralloc_fallback.c || true
	sed -i 's/native_buffer->handle->/((const native_handle_t \*)native_buffer->handle)->/g' src/vulkan/runtime/vk_android.c || true
	# Upstream commit added vk_android_import_anb_memory which dereferences anb->handle. Same buffer_handle_t void* coercion needed.
	sed -i 's/anb->handle->/((const native_handle_t \*)anb->handle)->/g' src/vulkan/runtime/vk_android.c || true
	# Fresh upstream Mesa currently hard-adds this as Werror in meson, which breaks Android builds on clang.
	sed -i "/-Werror=gnu-empty-initializer/d" meson.build || true

	mkdir -p "$workdir/bin"
	ln -sf "$ndk/clang" "$workdir/bin/cc"
	ln -sf "$ndk/clang++" "$workdir/bin/c++"
	export PATH="$workdir/bin:$ndk:$PATH"
	export CC=clang
	export CXX=clang++
	export AR=llvm-ar
	export RANLIB=llvm-ranlib
	export STRIP=llvm-strip
	export OBJDUMP=llvm-objdump
	export OBJCOPY=llvm-objcopy
	export LDFLAGS="-fuse-ld=lld"
	export CFLAGS="-D__ANDROID__ -Wno-error -Wno-error=gnu-empty-initializer -Wno-gnu-empty-initializer -Wno-deprecated-declarations -Wno-incompatible-pointer-types-discards-qualifiers -Wno-incompatible-pointer-types"
	export CXXFLAGS="-D__ANDROID__ -Wno-error -Wno-error=gnu-empty-initializer -Wno-gnu-empty-initializer -Wno-deprecated-declarations -Wno-incompatible-pointer-types-discards-qualifiers -Wno-incompatible-pointer-types"

	# Read Mesa version for driverVersion field
	MESA_VER=$(cat VERSION 2>/dev/null | tr -d '[:space:]' || echo "26.1.0-devel")

	echo "Generating build files..."
	cat <<EOF >"android-aarch64.txt"
[binaries]
ar = '$ndk/llvm-ar'
c = ['ccache', '$ndk/aarch64-linux-android$sdkver-clang']
cpp = ['ccache', '$ndk/aarch64-linux-android$sdkver-clang++', '-fno-exceptions', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '--start-no-unused-arguments', '-static-libstdc++', '--end-no-unused-arguments']
c_ld = '$ndk/ld.lld'
cpp_ld = '$ndk/ld.lld'
strip = '$ndk/llvm-strip'
pkg-config = ['env', 'PKG_CONFIG_LIBDIR=$ndk/pkg-config', '/usr/bin/pkg-config']

[host_machine]
system = 'android'
cpu_family = 'aarch64'
cpu = 'armv8'
endian = 'little'
EOF

	cat <<EOF >"native.txt"
[build_machine]
c = ['ccache', 'clang']
cpp = ['ccache', 'clang++']
ar = 'llvm-ar'
strip = 'llvm-strip'
c_ld = 'ld.lld'
cpp_ld = 'ld.lld'
system = 'linux'
cpu_family = 'x86_64'
cpu = 'x86_64'
endian = 'little'
EOF

	meson setup build-android-aarch64 \
		--cross-file "android-aarch64.txt" \
		--native-file "native.txt" \
		--prefix /tmp/turnip-$1 \
		-Dbuildtype=release \
		-Dstrip=true \
		-Dplatforms=android \
		-Dvideo-codecs= \
		-Dplatform-sdk-version="$sdkver" \
		-Dandroid-stub=true \
		-Dgallium-drivers= \
		-Dvulkan-drivers=freedreno \
		-Dvulkan-beta=true \
		-Dfreedreno-kmds=kgsl \
		-Degl=disabled \
		-Dplatform-sdk-version=36 \
		-Dandroid-libbacktrace=disabled \
		--reconfigure

	echo "Compiling build files..."
	ninja -C build-android-aarch64 install

	if ! [ -f /tmp/turnip-$1/lib/libvulkan_freedreno.so ]; then
		echo -e "${red}Build failed!${nocolor}" && exit 1
	fi

	# Determine variant-specific metadata
	local variant_name variant_desc
	if [ "$BUILD_VARIANT" == "p" ]; then
		variant_name="WN-Turnip-${BUILD_VERSION}-p Axxx"
		variant_desc="WinNative Turnip ${BUILD_VERSION} Performance"
	elif [ "$BUILD_VARIANT" == "p1" ]; then
		variant_name="WN-Turnip-${BUILD_VERSION}-p1 Axxx"
		variant_desc="WinNative Turnip ${BUILD_VERSION} Performance+"
	elif [ "$BUILD_VARIANT" == "p2" ]; then
		variant_name="WN-Turnip-${BUILD_VERSION}-p2 Axxx"
		variant_desc="WinNative Turnip ${BUILD_VERSION} Performance++"
	else
		variant_name="WN-Turnip-${BUILD_VERSION}-b Axxx"
		variant_desc="WinNative Turnip ${BUILD_VERSION} Balanced"
	fi

	echo "Making the archive..."
	cd /tmp/turnip-$1/lib

	cat <<EOF >"meta.json"
{
  "schemaVersion": 1,
  "name": "${variant_name}",
  "description": "${variant_desc}",
  "author": "WinNative",
  "packageVersion": "1",
  "vendor": "mesa",
  "driverVersion": "WN-${BUILD_VERSION}-${BUILD_VARIANT}",
  "minApi": 29,
  "libraryName": "libvulkan_freedreno.so"
}
EOF

	local zipname="WN-Turnip-${BUILD_VERSION}-${BUILD_VARIANT}_Axxx.zip"
	zip -q "/tmp/${zipname}" libvulkan_freedreno.so meta.json
	cd - > /dev/null

	if ! [ -f "/tmp/${zipname}" ]; then
		echo -e "${red}Failed to pack the archive!${nocolor}"
	else
		cp "/tmp/${zipname}" "$workdir/"
		echo -e "${green}Build completed successfully! Output: ${zipname}${nocolor}"
	fi
}

run_all

#!/bin/bash -e
set -o pipefail

green='\033[0;32m'
red='\033[0;31m'
nocolor='\033[0m'

deps="ninja patchelf unzip curl pip flex bison zip git perl glslangValidator"
workdir="$(pwd)/turnip_workdir"

ndkver="android-ndk-r28"
target_sdk="35" 

base_repo="https://gitlab.freedesktop.org/mesa/mesa.git"

check_deps(){
	echo "Checking system dependencies ..."
	for dep in $deps; do
		if ! command -v $dep >/dev/null 2>&1; then
			echo -e "$red Missing dependency binary: $dep$nocolor"
			missing=1
		else
			echo -e "$green Found: $dep$nocolor"
		fi
	done
	if [ "$missing" == "1" ]; then
		echo "Please install missing dependencies." && exit 1
	fi
    
	echo "Updating Meson via pip..."
	pip install meson mako --break-system-packages &> /dev/null || pip install meson mako &> /dev/null || true
}

prepare_ndk(){
	echo "Preparing NDK r28..."
	mkdir -p "$workdir"
	cd "$workdir"
	if [ ! -d "$ndkver" ]; then
		echo "Downloading Android NDK $ndkver..."
		curl -L "https://dl.google.com/android/repository/${ndkver}-linux.zip" --output "${ndkver}-linux.zip" &> /dev/null
		echo "Extracting NDK..."
		unzip -q "${ndkver}-linux.zip" &> /dev/null
	fi
    export ANDROID_NDK_HOME="$workdir/$ndkver"
}

prepare_source(){
	echo "Preparing Mesa source (Official Main)..."
	cd "$workdir"
	if [ -d mesa ]; then rm -rf mesa; fi
	
    echo -e "${green}Cloning Mesa Main...${nocolor}"
    
	git clone --depth 100 "$base_repo" mesa
	cd mesa
    
    git config user.email "ci@turnip.builder"
    git config user.name "Turnip CI Builder"

    # === HACK V7: FORCE INJECTION (Infalível) ===
    echo -e "${green}Applying V7 Ultimate Injection (Maintenance 7/8, Strict Bypass, A7xx)...${nocolor}"

cat << 'EOF_PYTHON' > inject_ultimate.py
import sys
import re

file_path = 'src/freedreno/vulkan/tu_device.cc'

# 1. FEATURES: Desbloqueio via substituição (Mantido pois funciona bem para features)
force_features_true = [
    "shaderFloat64", "shaderStorageImageMultisample",
    "uniformAndStorageBuffer16BitAccess", "storagePushConstant16",
    "uniformAndStorageBuffer8BitAccess", "storagePushConstant8",
    "shaderSharedInt64Atomics", "shaderBufferInt64Atomics",
    "independentResolve", "independentResolveNone",
    "shaderDenormPreserveFloat16", "shaderDenormFlushToZeroFloat16",
    "shaderRoundingModeRTZFloat16", "shaderDenormPreserveFloat32",
    "shaderRoundingModeRTZFloat32", "samplerFilterMinmax",
    "fragmentDensityMapDynamic", "fragmentDensityInvocations",
    "primitiveUnderestimation", "conservativePointAndLineRasterization",
    "textureCompressionASTC_HDR",
    "integerDotProduct8BitUnsignedAccelerated", "integerDotProduct8BitSignedAccelerated",
    "integerDotProduct8BitMixedSignednessAccelerated", "integerDotProduct4x8BitPackedUnsignedAccelerated",
    "integerDotProduct4x8BitPackedSignedAccelerated", "integerDotProduct4x8BitPackedMixedSignednessAccelerated",
    "integerDotProduct16BitUnsignedAccelerated", "integerDotProduct16BitSignedAccelerated",
    "integerDotProduct16BitMixedSignednessAccelerated", "integerDotProduct32BitUnsignedAccelerated",
    "integerDotProduct32BitSignedAccelerated", "integerDotProduct32BitMixedSignednessAccelerated",
    "integerDotProduct64BitUnsignedAccelerated", "integerDotProduct64BitSignedAccelerated",
    "integerDotProduct64BitMixedSignednessAccelerated",
    "integerDotProductAccumulatingSaturating8BitUnsignedAccelerated",
    "integerDotProductAccumulatingSaturating8BitSignedAccelerated",
    "integerDotProductAccumulatingSaturating8BitMixedSignednessAccelerated",
    "integerDotProductAccumulatingSaturating4x8BitPackedUnsignedAccelerated",
    "integerDotProductAccumulatingSaturating4x8BitPackedSignedAccelerated",
    "integerDotProductAccumulatingSaturating4x8BitPackedMixedSignednessAccelerated",
    "integerDotProductAccumulatingSaturating16BitUnsignedAccelerated",
    "integerDotProductAccumulatingSaturating16BitSignedAccelerated",
    "integerDotProductAccumulatingSaturating16BitMixedSignednessAccelerated",
    "integerDotProductAccumulatingSaturating32BitUnsignedAccelerated",
    "integerDotProductAccumulatingSaturating32BitSignedAccelerated",
    "integerDotProductAccumulatingSaturating32BitMixedSignednessAccelerated",
    "integerDotProductAccumulatingSaturating64BitUnsignedAccelerated",
    "integerDotProductAccumulatingSaturating64BitSignedAccelerated",
    "integerDotProductAccumulatingSaturating64BitMixedSignednessAccelerated"
]

# 2. EXTENSIONS: Lista para Injeção Forçada (Atropela tudo)
forced_extensions_code = """
    // === V7 INJECTION: STRICT BYPASS & A7XX SPOOF ===
    ext->KHR_maintenance5 = true;
    ext->KHR_maintenance6 = true;
    ext->KHR_maintenance7 = true;
    ext->KHR_maintenance8 = true;
    ext->EXT_primitives_generated_query = true;
    ext->EXT_primitive_topology_list_restart = true;
    ext->EXT_depth_clip_control = true;
    ext->EXT_depth_clip_enable = true;
    ext->EXT_attachment_feedback_loop_layout = true;
    ext->EXT_attachment_feedback_loop_dynamic_state = true;
    ext->KHR_compute_shader_derivatives = true;
    ext->NV_compute_shader_derivatives = true;
    ext->KHR_fragment_shading_rate = true;
    ext->EXT_filter_cubic = true;
    ext->IMG_filter_cubic = true;
    ext->EXT_sample_locations = true;
    ext->EXT_texture_compression_astc_hdr = true;
    ext->EXT_calibrated_timestamps = true;
    ext->EXT_conservative_rasterization = true;
    ext->AMD_shader_fragment_mask = true;
    ext->KHR_shader_atomic_int64 = true;
    ext->KHR_8bit_storage = true;
    ext->KHR_16bit_storage = true;
"""

try:
    with open(file_path, 'r') as f:
        content = f.read()

    # PATCH 1: Forçar Vulkan 1.4
    version_regex = r'(props->apiVersion\s*=\s*)([^;]+)(;)'
    if re.search(version_regex, content):
        content = re.sub(version_regex, r'\1TU_API_VERSION\3', content)
        print("Vulkan 1.4 Forced.")

    # PATCH 2: Features (Regex Clássico)
    feat_count = 0
    for prop in force_features_true:
        regex = rf'((?:p|features|props)->{prop}\s*=\s*)([^;]+)(;)'
        if re.search(regex, content):
            content = re.sub(regex, r'\1true\3', content)
            feat_count += 1
    print(f"Features Unlocked: {feat_count}")

    # PATCH 3: Extensions (INJEÇÃO NO FIM DA FUNÇÃO)
    # Procuramos o fechamento da struct "vk_device_extension_table" dentro de get_device_extensions
    # O padrão no código é "} };" fechando o "*ext = (struct ...) { ... } };"
    
    if "} };" in content:
        # Inserimos nosso código logo após o fechamento da struct, antes de sair da função
        content = content.replace("} };", "} };" + forced_extensions_code)
        print("V7 Injection Applied: Extensions forced at end of get_device_extensions().")
    else:
        print("WARNING: Could not find injection point '} };' in tu_device.cc")
        sys.exit(1)

    with open(file_path, 'w') as f:
        f.write(content)

except Exception as e:
    print(f"PYTHON ERROR: {e}")
    sys.exit(1)
EOF_PYTHON

    python3 inject_ultimate.py || { echo -e "${red}Unlock Failed!${nocolor}"; exit 1; }
    
    echo "Cloning SPIRV dependencies..."
    mkdir -p subprojects
    cd subprojects
    rm -rf spirv-tools spirv-headers
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Tools.git spirv-tools
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Headers.git spirv-headers
    cd .. 
    
	commit_hash=$(git rev-parse --short HEAD)
	version_str="Mesa-V7-ForceInjection"
	cd "$workdir"
}

compile_mesa(){
	echo -e "${green}Compiling Mesa for SDK $target_sdk...${nocolor}"

	local source_dir="$workdir/mesa"
	local build_dir="$source_dir/build"
	local ndk_bin_path="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin"
	local ndk_sysroot_path="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/sysroot"

    local compiler_ver="35"
    if [ ! -f "$ndk_bin_path/aarch64-linux-android${compiler_ver}-clang" ]; then compiler_ver="34"; fi
    echo "Using compiler: Clang $compiler_ver"

	local cross_file="$source_dir/android-aarch64-crossfile.txt"
	cat <<EOF > "$cross_file"
[binaries]
ar = '$ndk_bin_path/llvm-ar'
c = ['ccache', '$ndk_bin_path/aarch64-linux-android${compiler_ver}-clang', '--sysroot=$ndk_sysroot_path']
cpp = ['ccache', '$ndk_bin_path/aarch64-linux-android${compiler_ver}-clang++', '--sysroot=$ndk_sysroot_path', '-fno-exceptions', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '--start-no-unused-arguments', '-static-libstdc++', '--end-no-unused-arguments']
c_ld = 'lld'
cpp_ld = 'lld'
strip = '$ndk_bin_path/aarch64-linux-android-strip'

[host_machine]
system = 'android'
cpu_family = 'aarch64'
cpu = 'armv8'
endian = 'little'
EOF

	cd "$source_dir"
	
	export CFLAGS="-D__ANDROID__ -Wno-error"
	export CXXFLAGS="-D__ANDROID__ -Wno-error"

	meson setup "$build_dir" --cross-file "$cross_file" \
		-Dbuildtype=release \
		-Dplatforms=android \
		-Dplatform-sdk-version=$target_sdk \
		-Dandroid-stub=true \
		-Dgallium-drivers= \
		-Dvulkan-drivers=freedreno \
		-Dfreedreno-kmds=kgsl \
		-Degl=disabled \
		-Dglx=disabled \
		-Dvulkan-beta=true \
		-Ddefault_library=shared \
        -Dzstd=disabled \
        -Dwerror=false \
        --force-fallback-for=spirv-tools,spirv-headers \
		2>&1 | tee "$workdir/meson_log"

	ninja -C "$build_dir" 2>&1 | tee "$workdir/ninja_log"
}

package_driver(){
	local source_dir="$workdir/mesa"
	local build_dir="$source_dir/build"
	local lib_path="$build_dir/src/freedreno/vulkan/libvulkan_freedreno.so"
	local package_temp="$workdir/package_temp"

	if [ ! -f "$lib_path" ]; then
		echo -e "${red}Build failed: libvulkan_freedreno.so not found.${nocolor}"
		exit 1
	fi

	rm -rf "$package_temp"
	mkdir -p "$package_temp"
	cp "$lib_path" "$package_temp/lib_temp.so"

	cd "$package_temp"
	patchelf --set-soname "vulkan.adreno.so" lib_temp.so
	mv lib_temp.so "vulkan.ad07XX.so"

	local short_hash=${commit_hash:0:7}
	local meta_name="Turnip-V7-Injection-${short_hash}"
	cat <<EOF > meta.json
{
  "schemaVersion": 1,
  "name": "$meta_name",
  "description": "Vulkan 1.4 + V7 Force Injection (Maintenance 7/8, Strict Bypass). Commit $short_hash",
  "author": "mesa-ci",
  "driverVersion": "$version_str",
  "libraryName": "vulkan.ad07XX.so"
}
EOF

	local zip_name="Turnip-V7-Injection-${short_hash}.zip"
	zip -9 "$workdir/$zip_name" "vulkan.ad07XX.so" meta.json
	echo -e "${green}Package ready: $workdir/$zip_name${nocolor}"
}

generate_release_info() {
    echo -e "${green}Generating release info...${nocolor}"
    cd "$workdir"
    local date_tag=$(date +'%Y%m%d')
	local short_hash=${commit_hash:0:7}

    echo "Turnip-V7-Injection-${date_tag}-${short_hash}" > tag
    echo "Turnip V7 (Force Injection) - ${date_tag}" > release
    echo "Using direct code injection to force Maintenance 7/8 and Strict Mode extensions." > description
}

check_deps
prepare_ndk
prepare_source
compile_mesa
package_driver
generate_release_info

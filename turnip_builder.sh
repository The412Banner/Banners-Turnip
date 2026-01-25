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

    # === HACK V11: SURGICAL HYBRID (A7xx + Strict + Maint) ===
    echo -e "${green}Applying V11 Surgical Patch (Line-by-Line Force True)...${nocolor}"

cat << 'EOF_PYTHON' > patch_tu.py
import sys
import re

file_path = 'src/freedreno/vulkan/tu_device.cc'

# Lista MESTRA de extensões para forçar 'true'
# Combina A7xx (VRS, Derivatives) + Strict (Maintenance, Primitives)
extensions_to_force = [
    # --- MAINTENANCE PACK (Android Strict) ---
    "KHR_maintenance5", 
    "KHR_maintenance6", 
    "KHR_maintenance7", 
    "KHR_maintenance8",
    "EXT_primitives_generated_query", 
    "EXT_primitive_topology_list_restart",
    "EXT_depth_clip_control", 
    "EXT_depth_clip_enable",
    "EXT_attachment_feedback_loop_layout", 
    "EXT_attachment_feedback_loop_dynamic_state",
    
    # --- A7XX / HIGH-END PACK ---
    "KHR_fragment_shading_rate",       # VRS
    "KHR_compute_shader_derivatives",  # A7xx
    "NV_compute_shader_derivatives",   # A7xx
    "EXT_filter_cubic",                # Cubic
    "IMG_filter_cubic",
    "EXT_sample_locations",
    "EXT_texture_compression_astc_hdr",
    "EXT_calibrated_timestamps",
    "EXT_conservative_rasterization",
    "AMD_shader_fragment_mask",
    
    # --- STORAGE & ATOMICS ---
    "KHR_shader_atomic_int64",
    "KHR_8bit_storage", 
    "KHR_16bit_storage"
]

# Lista de Features para forçar 'true'
features_to_force = [
    "shaderFloat64", 
    "shaderStorageImageMultisample", 
    "uniformAndStorageBuffer16BitAccess", 
    "storagePushConstant16", 
    "uniformAndStorageBuffer8BitAccess", 
    "storagePushConstant8",
    "shaderSharedInt64Atomics", 
    "shaderBufferInt64Atomics", 
    "independentResolve",
    "independentResolveNone",
    "shaderDenormPreserveFloat16", 
    "shaderDenormFlushToZeroFloat16",
    "shaderRoundingModeRTZFloat16",
    "fragmentDensityMapDynamic", 
    "textureCompressionASTC_HDR"
]

try:
    with open(file_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    ext_changes = 0
    feat_changes = 0

    for line in lines:
        original_line = line
        modified = False
        
        # 1. SUBSTITUIÇÃO CIRÚRGICA DE EXTENSÕES
        # Procura por: .NOME = (qualquer coisa),
        for ext in extensions_to_force:
            # Regex: encontrar .EXTENSAO = ... ,
            # Substituir por .EXTENSAO = true,
            # Ignora espaços em branco antes ou depois
            if f".{ext}" in line and "=" in line:
                # Usa regex para garantir que não estamos mudando algo errado
                # Captura: (espaços.NOME)(espaços=)(valor)(virgula/comentario)
                replacement = re.sub(rf'(\.{ext}\s*=\s*)([^,]+)(,?)', r'\1true\3', line)
                if replacement != line:
                    line = replacement
                    modified = True
                    ext_changes += 1
                    # Não quebra o loop, pois uma linha pode ter múltiplas (raro, mas possivel)
        
        # 2. SUBSTITUIÇÃO CIRÚRGICA DE FEATURES
        # Procura por: p->feature = ... ou features->feature = ...
        for feat in features_to_force:
            if f"->{feat}" in line and "=" in line:
                replacement = re.sub(rf'((?:p|features|props)->{feat}\s*=\s*)([^;]+)(;)', r'\1true\3', line)
                if replacement != line:
                    line = replacement
                    modified = True
                    feat_changes += 1

        # 3. DOT PRODUCT MASSIVO
        if "integerDotProduct" in line and "=" in line:
            replacement = re.sub(r'((?:p|features|props)->integerDotProduct\w+\s*=\s*)([^;]+)(;)', r'\1true\3', line)
            if replacement != line:
                line = replacement
                modified = True
                feat_changes += 1

        # 4. FORÇAR VULKAN 1.4 (Na linha do apiVersion)
        if "props->apiVersion =" in line:
             line = re.sub(r'(props->apiVersion\s*=\s*)([^;]+)(;)', r'\1TU_API_VERSION\3', line)

        new_lines.append(line)

    print(f"Surgical Patch Applied: {ext_changes} extensions forced, {feat_changes} features forced.")

    with open(file_path, 'w') as f:
        f.writelines(new_lines)

except Exception as e:
    print(f"PYTHON ERROR: {e}")
    sys.exit(1)
EOF_PYTHON

    python3 patch_tu.py || { echo -e "${red}Patch Failed!${nocolor}"; exit 1; }
    
    echo "Cloning SPIRV dependencies..."
    mkdir -p subprojects
    cd subprojects
    rm -rf spirv-tools spirv-headers
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Tools.git spirv-tools
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Headers.git spirv-headers
    cd .. 
    
	commit_hash=$(git rev-parse --short HEAD)
	version_str="Mesa-V11-SurgicalHybrid"
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
	local meta_name="Turnip-V11-Surgical-${short_hash}"
	cat <<EOF > meta.json
{
  "schemaVersion": 1,
  "name": "$meta_name",
  "description": "Vulkan 1.4 + A7xx + Strict Maint. Commit $short_hash",
  "author": "mesa-ci",
  "driverVersion": "$version_str",
  "libraryName": "vulkan.ad07XX.so"
}
EOF

	local zip_name="Turnip-V11-Surgical-${short_hash}.zip"
	zip -9 "$workdir/$zip_name" "vulkan.ad07XX.so" meta.json
	echo -e "${green}Package ready: $workdir/$zip_name${nocolor}"
}

generate_release_info() {
    echo -e "${green}Generating release info...${nocolor}"
    cd "$workdir"
    local date_tag=$(date +'%Y%m%d')
	local short_hash=${commit_hash:0:7}

    echo "Turnip-V11-Surgical-${date_tag}-${short_hash}" > tag
    echo "Turnip V11 (Surgical Hybrid) - ${date_tag}" > release
    echo "Line-by-line forced unlock of A7xx and Strict Maintenance extensions." > description
}

check_deps
prepare_ndk
prepare_source
compile_mesa
package_driver
generate_release_info

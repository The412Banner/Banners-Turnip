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

    # === APPLY MR !37802 (Autotuner Overhaul) ===
    echo -e "${green}Fetching and Merging MR !37802 (Autotuner Overhaul)...${nocolor}"
    # Busca a referência do Merge Request diretamente do GitLab
    git fetch https://gitlab.freedesktop.org/mesa/mesa.git refs/merge-requests/37802/head:mr-37802
    # Funde o MR no código atual
    git merge mr-37802 --no-edit --allow-unrelated-histories || { 
        echo -e "${red}Merge Failed! Attempting rebase...${nocolor}"
        git rebase mr-37802 || { echo -e "${red}Critical Error applying MR 37802${nocolor}"; exit 1; }
    }

    # === HACK V13: CLEAN INJECTION (No Comments) ===
    echo -e "${green}Applying V13 Clean Injection (Maintenance 7/8 + Strict Bypass)...${nocolor}"

cat << 'EOF_PYTHON' > inject_ultimate.py
import sys
import re

file_path = 'src/freedreno/vulkan/tu_device.cc'

# 1. FEATURES (Regex Simples)
force_features_true = [
    "shaderFloat64", "shaderStorageImageMultisample",
    "uniformAndStorageBuffer16BitAccess", "storagePushConstant16",
    "uniformAndStorageBuffer8BitAccess", "storagePushConstant8",
    "shaderSharedInt64Atomics", "shaderBufferInt64Atomics",
    "independentResolve", "independentResolveNone",
    "shaderDenormPreserveFloat16", "shaderDenormFlushToZeroFloat16",
    "shaderRoundingModeRTZFloat16", "samplerFilterMinmax",
    "fragmentDensityMapDynamic", "textureCompressionASTC_HDR",
    "integerDotProduct8BitUnsignedAccelerated",
]

try:
    with open(file_path, 'r') as f:
        content = f.read()

    # PATCH 1: Vulkan 1.4 Force
    version_regex = r'(props->apiVersion\s*=\s*)([^;]+)(;)'
    if re.search(version_regex, content):
        content = re.sub(version_regex, r'\1TU_API_VERSION\3', content)
        print("Vulkan 1.4 Forced.")

    # PATCH 2: Features Unlock
    feat_count = 0
    for prop in force_features_true:
        if "integerDotProduct" in prop:
             regex = r'((?:p|features|props)->integerDotProduct\w+\s*=\s*)([^;]+)(;)'
             content, n = re.subn(regex, r'\1true\3', content)
             feat_count += n
        else:
             regex = rf'((?:p|features|props)->{prop}\s*=\s*)([^;]+)(;)'
             if re.search(regex, content):
                 content = re.sub(regex, r'\1true\3', content)
                 feat_count += 1
    print(f"Features Unlocked: {feat_count}")
    
    # PATCH 3: EXTENSIONS (INJEÇÃO LIMPA PÓS-INICIALIZAÇÃO)
    match = re.search(r'get_device_extensions\s*\([^{]*struct\s+vk_device_extension_table\s*\*\s*(\w+)', content, re.DOTALL)
    
    if match:
        var_name = match.group(1)
        func_start = match.end()
        closure_match = re.search(r'\};', content[func_start:])
        
        if closure_match:
            insert_pos = func_start + closure_match.end()
            
            # Código de Injeção SEM COMENTÁRIOS
            injection = f"""
    {var_name}->KHR_maintenance5 = true;
    {var_name}->KHR_maintenance6 = true;
    {var_name}->KHR_maintenance7 = true;
    {var_name}->KHR_maintenance8 = true;
    {var_name}->EXT_primitives_generated_query = true;
    {var_name}->EXT_primitive_topology_list_restart = true;
    {var_name}->EXT_depth_clip_control = true;
    {var_name}->EXT_depth_clip_enable = true;
    {var_name}->EXT_attachment_feedback_loop_layout = true;
    {var_name}->EXT_attachment_feedback_loop_dynamic_state = true;
    {var_name}->KHR_compute_shader_derivatives = true;
    {var_name}->NV_compute_shader_derivatives = true;
    {var_name}->KHR_fragment_shading_rate = true;
    {var_name}->EXT_filter_cubic = true;
    {var_name}->IMG_filter_cubic = true;
    {var_name}->EXT_sample_locations = true;
    {var_name}->EXT_texture_compression_astc_hdr = true;
    {var_name}->EXT_calibrated_timestamps = true;
    {var_name}->EXT_conservative_rasterization = true;
    {var_name}->AMD_shader_fragment_mask = true;
    {var_name}->KHR_shader_atomic_int64 = true;
    {var_name}->KHR_8bit_storage = true;
    {var_name}->KHR_16bit_storage = true;
"""
            content = content[:insert_pos] + injection + content[insert_pos:]
            print("SUCCESS: Forced Extensions injected.")
        else:
            print("ERROR: Could not find struct closure '};'")
            sys.exit(1)
    else:
        # Fallback simples
        if "get_device_extensions" in content:
             idx = content.find("get_device_extensions")
             idx_brace = content.find("};", idx)
             if idx_brace != -1:
                 var_name = "ext"
                 insert_pos = idx_brace + 2
                 injection = f"\n    {var_name}->KHR_maintenance5 = true; {var_name}->KHR_maintenance6 = true; {var_name}->KHR_maintenance7 = true; {var_name}->KHR_maintenance8 = true; {var_name}->EXT_primitives_generated_query = true; {var_name}->EXT_primitive_topology_list_restart = true;\n"
                 content = content[:insert_pos] + injection + content[insert_pos:]
                 print("SUCCESS: Fallback injection applied.")
             else:
                 sys.exit(1)
        else:
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
	version_str="Mesa-V13-Autotuner"
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
	local meta_name="Turnip-V13-Autotuner-${short_hash}"
	cat <<EOF > meta.json
{
  "schemaVersion": 1,
  "name": "$meta_name",
  "description": "Vulkan 1.4 + Autotuner Overhaul + Forced Extensions. Commit $short_hash",
  "author": "mesa-ci",
  "driverVersion": "$version_str",
  "libraryName": "vulkan.ad07XX.so"
}
EOF

	local zip_name="Turnip-V13-Autotuner-${short_hash}.zip"
	zip -9 "$workdir/$zip_name" "vulkan.ad07XX.so" meta.json
	echo -e "${green}Package ready: $workdir/$zip_name${nocolor}"
}

generate_release_info() {
    echo -e "${green}Generating release info...${nocolor}"
    cd "$workdir"
    local date_tag=$(date +'%Y%m%d')
	local short_hash=${commit_hash:0:7}

    echo "Turnip-V13-Autotuner-${date_tag}-${short_hash}" > tag
    echo "Turnip V13 (Autotuner + Inject) - ${date_tag}" > release
    echo "Includes MR 37802 (Autotuner Overhaul) and cleaned up extension injection." > description
}

check_deps
prepare_ndk
prepare_source
compile_mesa
package_driver
generate_release_info

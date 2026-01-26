#!/bin/bash -e
set -o pipefail

green='\033[0;32m'
nocolor='\033[0m'

deps="ninja patchelf unzip curl pip flex bison zip git perl glslangValidator"
workdir="$(pwd)/turnip_workdir"
ndkver="android-ndk-r28"
target_sdk="35" 

check_deps(){
	for dep in $deps; do
		if ! command -v $dep >/dev/null 2>&1; then echo "Missing: $dep"; exit 1; fi
	done
	pip install meson mako --break-system-packages &> /dev/null || true
}

prepare_ndk(){
	mkdir -p "$workdir" && cd "$workdir"
	if [ ! -d "$ndkver" ]; then
		curl -L "https://dl.google.com/android/repository/${ndkver}-linux.zip" --output "${ndkver}-linux.zip" &> /dev/null
		unzip -q "${ndkver}-linux.zip" &> /dev/null
	fi
    export ANDROID_NDK_HOME="$workdir/$ndkver"
}

build_driver() {
    local repo_url=$1
    local branch=$2
    local build_name=$3
    local inject_type=$4

    echo -e "${green}=== BUILDING: $build_name ===${nocolor}"
    
    cd "$workdir"
    if [ -d mesa ]; then rm -rf mesa; fi
    git clone --depth 1 -b "$branch" "$repo_url" mesa
    cd mesa
    git config user.email "ci@turnip.builder" && git config user.name "Turnip CI Builder"

cat << 'EOF_PYTHON' > inject.py
import sys
import re

inject_type = sys.argv[1]
file_path = 'src/freedreno/vulkan/tu_device.cc'

try:
    with open(file_path, 'r') as f: content = f.read()

    if inject_type == "gen8_env":
        if "#include <stdlib.h>" not in content:
            content = "#include <stdlib.h>\n" + content

    feats = [
        "shaderFloat64", "shaderStorageImageMultisample",
        "uniformAndStorageBuffer16BitAccess", "storagePushConstant16",
        "uniformAndStorageBuffer8BitAccess", "storagePushConstant8",
        "shaderSharedInt64Atomics", "shaderBufferInt64Atomics",
        "independentResolve", "independentResolveNone",
        "shaderDenormPreserveFloat16", "shaderDenormFlushToZeroFloat16",
        "shaderRoundingModeRTZFloat16", "samplerFilterMinmax",
        "fragmentDensityMapDynamic", "textureCompressionASTC_HDR",
        "integerDotProduct8BitUnsignedAccelerated",
        "shaderObject", "mutableDescriptorType",
        "maintenance5", "maintenance6", "maintenance7", "maintenance8"
    ]
    
    version_regex = r'(props->apiVersion\s*=\s*)([^;]+)(;)'
    if re.search(version_regex, content):
        content = re.sub(version_regex, r'\1TU_API_VERSION\3', content)

    for prop in feats:
        if "integerDotProduct" in prop:
             regex = r'((?:p|features|props)->integerDotProduct\w+\s*=\s*)([^;]+)(;)'
             content, n = re.subn(regex, r'\1true\3', content)
        else:
             regex = rf'((?:p|features|props)->{prop}\s*=\s*)([^;]+)(;)'
             if re.search(regex, content):
                 content = re.sub(regex, r'\1true\3', content)

    sig_regex = re.search(r'get_device_extensions\s*\([^)]*struct\s+tu_physical_device\s*\*\s*(\w+)[^)]*struct\s+vk_device_extension_table\s*\*\s*(\w+)', content, re.DOTALL)
    
    if sig_regex:
        pdev_var = sig_regex.group(1)
        ext_var = sig_regex.group(2)
        
        func_start = sig_regex.end()
        closure = re.search(r'\};', content[func_start:])
        
        if closure:
            pos = func_start + closure.end()
            
            code = f"""
    {ext_var}->KHR_maintenance5 = true; {ext_var}->KHR_maintenance6 = true;
    {ext_var}->KHR_maintenance7 = true; {ext_var}->KHR_maintenance8 = true;
    {ext_var}->EXT_primitives_generated_query = true; {ext_var}->EXT_primitive_topology_list_restart = true;
    {ext_var}->EXT_depth_clip_control = true; {ext_var}->EXT_depth_clip_enable = true;
    {ext_var}->EXT_attachment_feedback_loop_layout = true; {ext_var}->EXT_attachment_feedback_loop_dynamic_state = true;
    {ext_var}->KHR_fragment_shading_rate = true;
    {ext_var}->EXT_filter_cubic = true; {ext_var}->IMG_filter_cubic = true;
    {ext_var}->EXT_sample_locations = true; {ext_var}->EXT_texture_compression_astc_hdr = true;
    {ext_var}->EXT_calibrated_timestamps = true; {ext_var}->EXT_conservative_rasterization = true;
    {ext_var}->AMD_shader_fragment_mask = true;
    {ext_var}->KHR_shader_atomic_int64 = true; {ext_var}->KHR_8bit_storage = true; {ext_var}->KHR_16bit_storage = true;
    {ext_var}->EXT_shader_object = true; {ext_var}->VALVE_mutable_descriptor_type = true;
    {ext_var}->EXT_memory_budget = true; {ext_var}->EXT_display_control = true;
"""
            if inject_type == "gen8_env":
                code = f"""
    setenv("WRAPPER_VK_VERSION", "1.4.340", 1);
""" + code

            content = content[:pos] + code + content[pos:]

    with open(file_path, 'w') as f: f.write(content)
except Exception as e:
    print(e)
    sys.exit(1)
EOF_PYTHON

    python3 inject.py "$inject_type" || exit 1
    
    mkdir -p subprojects && cd subprojects
    rm -rf spirv-tools spirv-headers
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Tools.git spirv-tools
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Headers.git spirv-headers
    cd ..

    local build_dir="$workdir/mesa/build"
    local ndk_bin="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin"
    local ndk_sys="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/sysroot"
    local cver="$target_sdk"
    [ ! -f "$ndk_bin/aarch64-linux-android${cver}-clang" ] && cver="34"

    
    cat <<EOF > android-cross.txt
[binaries]
ar = '$ndk_bin/llvm-ar'
c = ['ccache', '$ndk_bin/aarch64-linux-android${cver}-clang', '--sysroot=$ndk_sys']
cpp = ['ccache', '$ndk_bin/aarch64-linux-android${cver}-clang++', '--sysroot=$ndk_sys']
c_ld = 'lld'
cpp_ld = 'lld'
strip = '$ndk_bin/aarch64-linux-android-strip'
[host_machine]
system = 'android'
cpu_family = 'aarch64'
cpu = 'armv8'
endian = 'little'
[built-in options]
c_link_args = ['-static-libstdc++']
cpp_link_args = ['-static-libstdc++']
EOF
    
    export CFLAGS="-D__ANDROID__ -Wno-error"
    export CXXFLAGS="-D__ANDROID__ -Wno-error"

    meson setup "$build_dir" --cross-file android-cross.txt \
        -Dbuildtype=release -Dplatforms=android -Dplatform-sdk-version=36 -Dandroid-stub=true \
        -Dgallium-drivers= -Dvulkan-drivers=freedreno -Dfreedreno-kmds=kgsl -Degl=disabled -Dglx=disabled \
        -Dvulkan-beta=true -Ddefault_library=shared -Dzstd=disabled -Dwerror=false \
        --force-fallback-for=spirv-tools,spirv-headers
    
    ninja -C "$build_dir"

    local lib="$build_dir/src/freedreno/vulkan/libvulkan_freedreno.so"
    if [ ! -f "$lib" ]; then echo "Build Failed"; exit 1; fi
    
    local pkg_dir="$workdir/pkg_$build_name"
    mkdir -p "$pkg_dir"
    cp "$lib" "$pkg_dir/vulkan.ad07XX.so"
    cd "$pkg_dir"
    patchelf --set-soname "vulkan.adreno.so" vulkan.ad07XX.so
    
    local hash=$(git -C "$workdir/mesa" rev-parse --short HEAD)
    local desc=""
    if [ "$inject_type" == "gen8_env" ]; then desc="Gen8 + EnvVar 1.4.340 + StaticLink"; fi
    if [ "$inject_type" == "main_safe" ]; then desc="Main + StaticLink + Default Behavior"; fi

    echo "{
  \"schemaVersion\": 1,
  \"name\": \"Turnip-${build_name}-${hash}\",
  \"description\": \"$desc\",
  \"author\": \"mesa-ci\",
  \"driverVersion\": \"Mesa-V33-Static\",
  \"libraryName\": \"vulkan.ad07XX.so\"
}" > meta.json
    
    zip -9 "$workdir/Turnip-${build_name}-${hash}.zip" vulkan.ad07XX.so meta.json
    echo -e "${green}Done: Turnip-${build_name}-${hash}.zip${nocolor}"
    
    # Gera arquivos para facilitar a criacao de release manual
    echo "Turnip-${build_name}-${hash}" > "$workdir/tag"
    echo "Turnip V33 - $build_name" > "$workdir/release"
}

check_deps
prepare_ndk

# 
build_driver "https://github.com/whitebelyash/mesa-tu8.git" "gen8" "Gen8-Fix" "gen8_env"

#
build_driver "https://gitlab.freedesktop.org/mesa/mesa.git" "main" "Main-Fix" "main_safe"

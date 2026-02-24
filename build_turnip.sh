#!/bin/bash -e
set -o pipefail

deps="ninja patchelf unzip curl pip flex bison zip git perl glslangValidator python3 patch"
workdir="$(pwd)/turnip_workdir"
ndkver="android-ndk-r28"

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

fix_patch_rejects() {
    echo "Limpando configs oficiais da Mesa e injetando configs CLÁSSICAS do A8xx..."
    
    cat << 'EOF_PYTHON' > fix_devices.py
import os
import re

file_path = "src/freedreno/common/freedreno_devices.py"
if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # 1. DELETA as definições oficiais/bugadas da Mesa para evitar conflitos e glitches de SYSMEM
    content = re.sub(r'a8xx_830\s*=\s*GPUProps\([\s\S]*?\)\n', '', content)
    content = re.sub(r'a8xx_825\s*=\s*GPUProps\([\s\S]*?\)\n', '', content)
    content = re.sub(r'a8xx_810\s*=\s*GPUProps\([\s\S]*?\)\n', '', content)
    content = re.sub(r'a8xx_gen2\s*=\s*GPUProps\([\s\S]*?\)\n', '', content)
    content = re.sub(r'a8xx_gen2_raw_magic_regs\s*=\s*\[[\s\S]*?\]\n', '', content)
    content = re.sub(r'a8xx_base_raw_magic_regs\s*=\s*\[[\s\S]*?\]\n', '', content)

    # 2. INJETA o código clássico (do tu_gen8.patch original) puro e sem glitches visuais
    classic_code = """
a8xx_gen2 = GPUProps(
        has_salu_int_narrowing_quirk = True
)

a8xx_830 = GPUProps(
        sysmem_vpc_attr_buf_size = 131072,
        sysmem_vpc_pos_buf_size = 65536,
        sysmem_vpc_bv_pos_buf_size = 32768,
        sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.FULL.value,
        sysmem_per_ccu_color_cache_size = 128 * 1024,
        sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.THREE_QUARTER.value,
        sysmem_per_ccu_depth_cache_size = 192 * 1024,
        gmem_vpc_attr_buf_size = 49152,
        gmem_vpc_pos_buf_size = 24576,
        gmem_vpc_bv_pos_buf_size = 32768,
        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,
        gmem_per_ccu_color_cache_size = 16 * 1024,
        gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.FULL.value,
        gmem_per_ccu_depth_cache_size = 256 * 1024,
        has_fs_tex_prefetch = False,
        disable_gmem = True,
)

a8xx_825 = GPUProps(
        sysmem_vpc_attr_buf_size = 131072,
        sysmem_vpc_pos_buf_size = 65536,
        sysmem_vpc_bv_pos_buf_size = 32768,
        sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.FULL.value,
        sysmem_per_ccu_color_cache_size = 128 * 1024,
        sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.THREE_QUARTER.value,
        sysmem_per_ccu_depth_cache_size = 96 * 1024,
        gmem_vpc_attr_buf_size = 49152,
        gmem_vpc_pos_buf_size = 24576,
        gmem_vpc_bv_pos_buf_size = 32768,
        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,
        gmem_per_ccu_color_cache_size = 16 * 1024,
        gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.FULL.value,
        gmem_per_ccu_depth_cache_size = 127 * 1024,
        disable_gmem = True,
)

a8xx_810 = GPUProps(
        sysmem_vpc_attr_buf_size = 131072,
        sysmem_vpc_pos_buf_size = 65536,
        sysmem_vpc_bv_pos_buf_size = 32768,
        sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.FULL.value,
        sysmem_per_ccu_color_cache_size = 32 * 1024,
        sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.THREE_QUARTER.value,
        sysmem_per_ccu_depth_cache_size = 32 * 1024,
        gmem_vpc_attr_buf_size = 49152,
        gmem_vpc_pos_buf_size = 24576,
        gmem_vpc_bv_pos_buf_size = 32768,
        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,
        gmem_per_ccu_color_cache_size = 16 * 1024,
        gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.FULL.value,
        gmem_per_ccu_depth_cache_size = 64 * 1024,
        has_ray_intersection = False,
        has_sw_fuse = False,
        disable_gmem = True,
)

a8xx_gen2_raw_magic_regs = [
        [A6XXRegs.REG_A8XX_PC_MODE_CNTL,    0x00003f00],
]
"""
    # Encontra o local exato da classe A8XX e injeta o bloco Clássico antes
    a8xx_idx = content.find("CHIP.A8XX")
    if a8xx_idx != -1:
        insert_idx = content.rfind("add_gpus([", 0, a8xx_idx)
        if insert_idx == -1: 
            insert_idx = a8xx_idx
        content = content[:insert_idx] + classic_code + "\n" + content[insert_idx:]

    # Protege contra dependências do magic_regs oficial
    content = content.replace("raw_magic_regs = a8xx_base_raw_magic_regs", "raw_magic_regs = a8xx_gen2_raw_magic_regs")

    with open(file_path, 'w') as f:
        f.write(content)

# 3. Conserta o KGSL Backend para o UBWC_5
kgsl_file = "src/freedreno/vulkan/tu_knl_kgsl.cc"
if os.path.exists(kgsl_file):
    with open(kgsl_file, 'r') as f:
        kgsl_content = f.read()
    if "case KGSL_UBWC_4_0:" in kgsl_content and "case 5:" not in kgsl_content:
        kgsl_content = kgsl_content.replace("case KGSL_UBWC_4_0:", "case KGSL_UBWC_4_0:\n   case 5:\n   case 6:")
        with open(kgsl_file, 'w') as f:
            f.write(kgsl_content)
EOF_PYTHON

    python3 fix_devices.py
}

inject_mods() {
    DEV_FILE=$(find src/freedreno/vulkan -name "tu_device.c*" -print -quit)

    cat << 'EOF_PYTHON' > injector.py
import re
import sys

dev_file = sys.argv[1]

with open(dev_file, 'r') as f:
    content = f.read()

# Remove a inclusão de versão e aplica correção do nome
content = content.replace('#include "tu_version.h"', '')
pattern_revert = r"char\s+devname\[128\];[\s\S]*?strcat\(devname,[\s\S]*?strcpy\(props->deviceName,\s*devname\);"
if re.search(pattern_revert, content):
    content = re.sub(pattern_revert, "strcpy(props->deviceName, pdevice->name);", content)

# Remove FlushAll para Performance Máxima
content = re.sub(r'tu_env\.debug\s*\|=\s*TU_DEBUG_FLUSHALL;', '/* FLUSHALL REMOVED */', content)

# Limpa o setenv
if 'setenv("WRAPPER_VK_VERSION"' not in content:
    content = content.replace(
        "VkResult\ntu_CreateInstance(const VkInstanceCreateInfo *pCreateInfo,",
        "VkResult\ntu_CreateInstance(const VkInstanceCreateInfo *pCreateInfo,\n   const VkAllocationCallbacks *pAllocator,\n   VkInstance *pInstance)\n{\n"
    )
    content = content.replace(
        "   const VkAllocationCallbacks *pAllocator,\n   VkInstance *pInstance)\n{\n\n   const VkAllocationCallbacks *pAllocator,\n   VkInstance *pInstance)",
        ""
    )

features_to_enable = [
    "storageBuffer16BitAccess", "uniformAndStorageBuffer16BitAccess", "storagePushConstant16",
    "storageInputOutput16", "multiview", "multiviewGeometryShader", "multiviewTessellationShader",
    "variablePointersStorageBuffer", "variablePointers", "protectedMemory", "samplerYcbcrConversion",
    "shaderDrawParameters", "samplerMirrorClampToEdge", "drawIndirectCount", "storageBuffer8BitAccess", 
    "uniformAndStorageBuffer8BitAccess", "storagePushConstant8", "shaderBufferInt64Atomics", 
    "shaderSharedInt64Atomics", "shaderFloat16", "shaderInt8", "descriptorIndexing", 
    "shaderInputAttachmentArrayDynamicIndexing", "shaderUniformTexelBufferArrayDynamicIndexing", 
    "shaderStorageTexelBufferArrayDynamicIndexing", "shaderUniformBufferArrayNonUniformIndexing", 
    "shaderSampledImageArrayNonUniformIndexing", "shaderStorageBufferArrayNonUniformIndexing", 
    "shaderStorageImageArrayNonUniformIndexing", "shaderInputAttachmentArrayNonUniformIndexing", 
    "shaderUniformTexelBufferArrayNonUniformIndexing", "shaderStorageTexelBufferArrayNonUniformIndexing", 
    "descriptorBindingUniformBufferUpdateAfterBind", "descriptorBindingSampledImageUpdateAfterBind", 
    "descriptorBindingStorageImageUpdateAfterBind", "descriptorBindingStorageBufferUpdateAfterBind", 
    "descriptorBindingUniformTexelBufferUpdateAfterBind", "descriptorBindingStorageTexelBufferUpdateAfterBind", 
    "descriptorBindingUpdateUnusedWhilePending", "descriptorBindingPartiallyBound", 
    "descriptorBindingVariableDescriptorCount", "runtimeDescriptorArray", "samplerFilterMinmax", 
    "scalarBlockLayout", "imagelessFramebuffer", "uniformBufferStandardLayout", "shaderSubgroupExtendedTypes", 
    "separateDepthStencilLayouts", "hostQueryReset", "timelineSemaphore", "bufferDeviceAddress", 
    "bufferDeviceAddressCaptureReplay", "bufferDeviceAddressMultiDevice", "vulkanMemoryModel", 
    "vulkanMemoryModelDeviceScope", "vulkanMemoryModelAvailabilityVisibilityChains", "shaderOutputViewportIndex", 
    "shaderOutputLayer", "subgroupBroadcastDynamicId", "robustImageAccess", "inlineUniformBlock", 
    "descriptorBindingInlineUniformBlockUpdateAfterBind", "pipelineCreationCacheControl", "privateData", 
    "shaderDemoteToHelperInvocation", "shaderTerminateInvocation", "subgroupSizeControl", "computeFullSubgroups", 
    "synchronization2", "textureCompressionASTC_HDR", "shaderZeroInitializeWorkgroupMemory", "dynamicRendering", 
    "shaderIntegerDotProduct", "maintenance4"
]

unlock_code = "\n"
unlock_code += "".join([f"   features->{feat} = true;\n" for feat in features_to_enable])

if "static void\ntu_get_features" in content:
    pattern_func_end = r"(\n}\n\nstatic void\ntu_get_physical_device_properties)"
    if re.search(pattern_func_end, content):
        content = re.sub(pattern_func_end, unlock_code + r"\1", content, count=1)

with open(dev_file, 'w') as f:
    f.write(content)
EOF_PYTHON

    python3 injector.py "$DEV_FILE"
}

compile_mesa() {
    local repo_url="https://gitlab.freedesktop.org/mesa/mesa.git"
    local branch="main"
    local build_name="Turnip-A8xx-Ultimate-MR39751"
    local output_tag="V104-A8xx-Ultimate"

    echo "Cloning Mesa..."
    cd "$workdir"
    rm -rf mesa
    git clone --depth 100 -b "$branch" "$repo_url" mesa
    cd mesa

    # 1. Aplica o MR39751 (Timeline Sync)
    if [ -f "$workdir/../39751.patch" ]; then
        echo "Applying 39751.patch..."
        patch -p1 --fuzz=4 < "$workdir/../39751.patch" || true
    fi

    # 2. Aplica o patch Clássico (O que renderiza direito, sem glitches)
    if [ -f "$workdir/../tu_gen8.patch" ]; then
        echo "Applying tu_gen8.patch..."
        # Force continua mesmo se bater na configuração oficial da Mesa
        patch -p1 --fuzz=4 --force < "$workdir/../tu_gen8.patch" || true
    fi
    
    # 3. Costura o código blindado: DESTRÓI as configs oficiais bugadas e PÕE AS SUAS.
    fix_patch_rejects

    # 4. Aplica desativação do FlushAll e libera features
    inject_mods

    mkdir -p subprojects && cd subprojects
    rm -rf spirv-tools spirv-headers
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Tools.git spirv-tools
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Headers.git spirv-headers
    cd ..

    local build_dir="$workdir/mesa/build"
    rm -rf "$build_dir"

    local ndk_bin="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin"
    local ndk_sys="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/sysroot"
    local cver="35"
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
    
    export CFLAGS="-D__ANDROID__ -Wno-error -Wno-deprecated-declarations"
    export CXXFLAGS="-D__ANDROID__ -Wno-error -Wno-deprecated-declarations"

    meson setup "$build_dir" --cross-file android-cross.txt \
        -Dbuildtype=release \
        -Dplatforms=android \
        -Dplatform-sdk-version=36 \
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
        --force-fallback-for=spirv-tools,spirv-headers
    
    ninja -C "$build_dir"

    local lib="$build_dir/src/freedreno/vulkan/libvulkan_freedreno.so"
    if [ ! -f "$lib" ]; then echo "Build Failed"; exit 1; fi
    
    local pkg_dir="$workdir/pkg_$output_tag"
    mkdir -p "$pkg_dir"
    cp "$lib" "$pkg_dir/vulkan.ad07XX.so"
    cd "$pkg_dir"
    patchelf --set-soname "vulkan.adreno.so" vulkan.ad07XX.so
    
    echo "{
  \"schemaVersion\": 1,
  \"name\": \"$build_name\",
  \"description\": \"A8xx (Classic Props) + MR39751 + No FlushAll\",
  \"author\": \"StevenMX\",
  \"packageVersion\": \"1\",
  \"vendor\": \"Mesa\",
  \"driverVersion\": \"$output_tag\",
  \"minApi\": 28,
  \"libraryName\": \"vulkan.ad07XX.so\"
}" > meta.json
    
    zip -9 "$workdir/Turnip-${output_tag}.zip" vulkan.ad07XX.so meta.json
    echo "Done: Turnip-${output_tag}.zip"
}

check_deps
prepare_ndk
compile_mesa

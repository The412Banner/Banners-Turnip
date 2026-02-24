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

inject_mods() {
    DEV_FILE=$(find src/freedreno/vulkan -name "tu_device.c*" -print -quit)

    if [ -z "$DEV_FILE" ]; then
        echo "ERRO: Arquivo tu_device não encontrado."
        exit 1
    fi

    cat << 'EOF_PYTHON' > injector.py
import re
import sys

dev_file = sys.argv[1]

with open(dev_file, 'r') as f:
    content = f.read()

content = content.replace('#include "tu_version.h"', '')
pattern_revert = r"char\s+devname\[128\];[\s\S]*?strcat\(devname,[\s\S]*?strcpy\(props->deviceName,\s*devname\);"
if re.search(pattern_revert, content):
    content = re.sub(pattern_revert, "strcpy(props->deviceName, pdevice->name);", content)

if 'tu_env.debug |= TU_DEBUG_FLUSHALL;' in content:
    content = content.replace('tu_env.debug |= TU_DEBUG_FLUSHALL;', '')

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
    "shaderDrawParameters",
    "samplerMirrorClampToEdge", "drawIndirectCount", "storageBuffer8BitAccess", "uniformAndStorageBuffer8BitAccess",
    "storagePushConstant8", "shaderBufferInt64Atomics", "shaderSharedInt64Atomics", "shaderFloat16",
    "shaderInt8", "descriptorIndexing", "shaderInputAttachmentArrayDynamicIndexing",
    "shaderUniformTexelBufferArrayDynamicIndexing", "shaderStorageTexelBufferArrayDynamicIndexing",
    "shaderUniformBufferArrayNonUniformIndexing", "shaderSampledImageArrayNonUniformIndexing",
    "shaderStorageBufferArrayNonUniformIndexing", "shaderStorageImageArrayNonUniformIndexing",
    "shaderInputAttachmentArrayNonUniformIndexing", "shaderUniformTexelBufferArrayNonUniformIndexing",
    "shaderStorageTexelBufferArrayNonUniformIndexing", "descriptorBindingUniformBufferUpdateAfterBind",
    "descriptorBindingSampledImageUpdateAfterBind", "descriptorBindingStorageImageUpdateAfterBind",
    "descriptorBindingStorageBufferUpdateAfterBind", "descriptorBindingUniformTexelBufferUpdateAfterBind",
    "descriptorBindingStorageTexelBufferUpdateAfterBind", "descriptorBindingUpdateUnusedWhilePending",
    "descriptorBindingPartiallyBound", "descriptorBindingVariableDescriptorCount", "runtimeDescriptorArray",
    "samplerFilterMinmax", "scalarBlockLayout", "imagelessFramebuffer", "uniformBufferStandardLayout",
    "shaderSubgroupExtendedTypes", "separateDepthStencilLayouts", "hostQueryReset", "timelineSemaphore",
    "bufferDeviceAddress", "bufferDeviceAddressCaptureReplay", "bufferDeviceAddressMultiDevice",
    "vulkanMemoryModel", "vulkanMemoryModelDeviceScope", "vulkanMemoryModelAvailabilityVisibilityChains",
    "shaderOutputViewportIndex", "shaderOutputLayer", "subgroupBroadcastDynamicId",
    "robustImageAccess", "inlineUniformBlock", "descriptorBindingInlineUniformBlockUpdateAfterBind",
    "pipelineCreationCacheControl", "privateData", "shaderDemoteToHelperInvocation", "shaderTerminateInvocation",
    "subgroupSizeControl", "computeFullSubgroups", "synchronization2", "textureCompressionASTC_HDR",
    "shaderZeroInitializeWorkgroupMemory", "dynamicRendering", "shaderIntegerDotProduct", "maintenance4"
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
    local build_name="Turnip-A8xx-Forced-MR39751"
    local output_tag="V99-A8xx-Forced-MR39751"

    echo "Cloning Mesa..."
    cd "$workdir"
    rm -rf mesa
    git clone --depth 100 -b "$branch" "$repo_url" mesa
    cd mesa

    # 1º - Aplica o patch Gen8 forçando a aplicação
    if [ -f "$workdir/../tu_gen8.patch" ]; then
        echo "Applying tu_gen8.patch (Forced)..."
        # O || true garante que o script não pare mesmo se houverem rejects
        patch -p1 --fuzz=4 --force --ignore-whitespace < "$workdir/../tu_gen8.patch" || {
            echo "AVISO: Houveram rejeições no tu_gen8.patch. Continuando a compilação mesmo assim..."
        }
    fi

    # 2º - Aplica o patch MR39751 logo em seguida
    if [ -f "$workdir/../39751.patch" ]; then
        echo "Applying 39751.patch..."
        patch -p1 --fuzz=4 --ignore-whitespace < "$workdir/../39751.patch" || {
            echo "AVISO: Houveram rejeições no 39751.patch. Continuando a compilação..."
        }
    fi

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
  \"description\": \"Mesa Main + A8xx (Forced) + MR 39751 + Feats Unlocked + No FlushAll\",
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

#!/bin/bash -e
set -o pipefail

# Dependências
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
    # Verificação de segurança antes de rodar o Python
    if [ ! -f "src/freedreno/vulkan/tu_physical_device.cc" ]; then
        echo "ERRO CRÍTICO: Código fonte do Mesa não encontrado em $(pwd)!"
        echo "O git clone falhou ou estamos no diretório errado."
        ls -F
        exit 1
    fi

    cat << 'EOF_PYTHON' > injector.py
import re
import os
import sys

phys_dev_file = "src/freedreno/vulkan/tu_physical_device.cc"
device_file = "src/freedreno/vulkan/tu_device.cc"

if not os.path.exists(phys_dev_file):
    print(f"Erro: Arquivo {phys_dev_file} nao encontrado!")
    sys.exit(1)

# 1. Limpa Includes e Versoes Antigas
with open(device_file, 'r') as f:
    dev_content = f.read()

dev_content = dev_content.replace('#include "tu_version.h"', '')

pattern_revert = r"char\s+devname\[128\];[\s\S]*?strcat\(devname,[\s\S]*?strcpy\(props->deviceName,\s*devname\);"
replacement_revert = "strcpy(props->deviceName, pdevice->name);"

if re.search(pattern_revert, dev_content):
    dev_content = re.sub(pattern_revert, replacement_revert, dev_content)

# 2. Injeta Variavel de Ambiente
if 'setenv("WRAPPER_VK_VERSION"' not in dev_content:
    dev_content = dev_content.replace(
        "VkResult\ntu_CreateInstance(const VkInstanceCreateInfo *pCreateInfo,",
        "VkResult\ntu_CreateInstance(const VkInstanceCreateInfo *pCreateInfo,\n   const VkAllocationCallbacks *pAllocator,\n   VkInstance *pInstance)\n{\n   setenv(\"WRAPPER_VK_VERSION\", \"1.4.340\", 1);\n"
    )
    # Limpa duplicata se houver
    dev_content = dev_content.replace(
        "   const VkAllocationCallbacks *pAllocator,\n   VkInstance *pInstance)\n{\n   setenv(\"WRAPPER_VK_VERSION\", \"1.4.340\", 1);\n\n   const VkAllocationCallbacks *pAllocator,\n   VkInstance *pInstance)",
        ""
    )

with open(device_file, 'w') as f:
    f.write(dev_content)

# 3. Forca Versao Vulkan 1.4.340
with open(phys_dev_file, 'r') as f:
    phys_content = f.read()

phys_content = re.sub(
    r"return VK_MAKE_VERSION\(1, [0-9]+, [0-9]+\);",
    "return VK_MAKE_VERSION(1, 4, 340);",
    phys_content
)

# 4. Desbloqueia Features
features_1_1 = [
    "storageBuffer16BitAccess", "uniformAndStorageBuffer16BitAccess", "storagePushConstant16",
    "storageInputOutput16", "multiview", "multiviewGeometryShader", "multiviewTessellationShader",
    "variablePointersStorageBuffer", "variablePointers", "protectedMemory", "samplerYcbcrConversion",
    "shaderDrawParameters"
]

features_1_2 = [
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
    "shaderOutputViewportIndex", "shaderOutputLayer", "subgroupBroadcastDynamicId"
]

features_1_3 = [
    "robustImageAccess", "inlineUniformBlock", "descriptorBindingInlineUniformBlockUpdateAfterBind",
    "pipelineCreationCacheControl", "privateData", "shaderDemoteToHelperInvocation", "shaderTerminateInvocation",
    "subgroupSizeControl", "computeFullSubgroups", "synchronization2", "textureCompressionASTC_HDR",
    "shaderZeroInitializeWorkgroupMemory", "dynamicRendering", "shaderIntegerDotProduct", "maintenance4"
]

def inject_features(content, struct_name, feat_list, struct_type):
    code = "".join([f"      f->{feat} = VK_TRUE;\n" for feat in feat_list])
    pattern = rf"(case {struct_name}:[\s\S]*?)(\s+break;)"
    replacement = f"\\1\n      {struct_type} *f = ({struct_type} *)ext;\n{code}\\2"
    return re.sub(pattern, replacement, content, count=1)

phys_content = inject_features(phys_content, "VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_1_FEATURES", features_1_1, "VkPhysicalDeviceVulkan11Features")
phys_content = inject_features(phys_content, "VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES", features_1_2, "VkPhysicalDeviceVulkan12Features")
phys_content = inject_features(phys_content, "VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES", features_1_3, "VkPhysicalDeviceVulkan13Features")

with open(phys_dev_file, 'w') as f:
    f.write(phys_content)
EOF_PYTHON
    
    python3 injector.py
}

compile_mesa() {
    local repo_url="https://gitlab.freedesktop.org/mesa/mesa.git"
    local branch="main"
    local build_name="Turnip-A8xx-Final"
    local output_tag="V78-A8xx-Final-1.4.340"

    echo "Cloning Mesa..."
    
    cd "$workdir"
    rm -rf mesa
    
    git clone --depth 100 -b "$branch" "$repo_url" mesa
    cd mesa

    # Aplica o Patch se existir na raiz do workdir
    if [ -f "$workdir/../tu_gen8.patch" ]; then
        echo "Applying tu_gen8.patch..."
        patch -p1 --fuzz=4 --ignore-whitespace < "$workdir/../tu_gen8.patch" || true
    else
        echo "AVISO: tu_gen8.patch nao encontrado. Pulando."
    fi

    inject_mods

    # Backup para garantir versão no device.cc caso o python tenha falhado
    sed -i 's/VK_MAKE_VERSION(1, 3, [0-9]*)/VK_MAKE_VERSION(1, 4, 340)/g' src/freedreno/vulkan/tu_device.cc || true
    sed -i 's/VK_MAKE_VERSION(1, 4, [0-9]*)/VK_MAKE_VERSION(1, 4, 340)/g' src/freedreno/vulkan/tu_device.cc || true

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
  \"description\": \"Mesa Main + A8xx Patch + VK 1.4.340 + All Feats\",
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

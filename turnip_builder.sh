#!/bin/bash -e
set -o pipefail

green='\033[0;32m'
nocolor='\033[0m'
red='\033[0;31m'

deps="ninja patchelf unzip curl pip flex bison zip git perl glslangValidator"
workdir="$(pwd)/turnip_workdir"
ndkver="android-ndk-r28"
target_sdk="36" 

check_deps(){
	for dep in $deps; do
		if ! command -v $dep >/dev/null 2>&1; then echo -e "$red Missing: $dep $nocolor"; exit 1; fi
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
    local repo_url="https://gitlab.freedesktop.org/mesa/mesa.git"
    local branch="main"
    local build_name="Main-SDK36-FeatsOnly"

    echo -e "${green}=== BUILDING: $build_name ===${nocolor}"
    
    cd "$workdir"
    if [ -d mesa ]; then rm -rf mesa; fi
    
    git clone --depth 100 -b "$branch" "$repo_url" mesa
    cd mesa
    git config user.email "ci@turnip.builder" && git config user.name "Turnip CI Builder"

    # ==============================================================================
    # INJEÇÃO DE FEATURES (SEM EXTENSÕES)
    # ==============================================================================
cat << 'EOF_PYTHON' > inject.py
import sys
import re

file_path = 'src/freedreno/vulkan/tu_device.cc'

try:
    with open(file_path, 'r') as f: content = f.read()

    # LISTA DE FEATURES ESSENCIAIS PARA DXVK/VKD3D
    # (Forçamos o suporte interno, mas NÃO forçamos a extensão na lista pública)
    feats = [
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
        "samplerFilterMinmax",
        "fragmentDensityMapDynamic", 
        "textureCompressionASTC_HDR",
        "integerDotProduct8BitUnsignedAccelerated",
        # Features "Modernas" (Sem forçar a extensão, o driver só usa se o app pedir o feature bit)
        "shaderObject", 
        "mutableDescriptorType"
    ]
    
    # Nota: Removi RT e Mesh da lista de features forçadas para evitar instabilidade.

    # Aplica o Force True nas Features
    count = 0
    for prop in feats:
        if "integerDotProduct" in prop:
             regex = r'((?:p|features|props)->integerDotProduct\w+\s*=\s*)([^;]+)(;)'
             content, n = re.subn(regex, r'\1true\3', content)
             count += n
        else:
             regex = rf'((?:p|features|props)->{prop}\s*=\s*)([^;]+)(;)'
             if re.search(regex, content):
                 content = re.sub(regex, r'\1true\3', content)
                 count += 1
    
    print(f"Features unlocked: {count}")
    
    # NÃO HÁ BLOCO DE INJEÇÃO DE EXTENSÕES AQUI.
    # O driver vai reportar apenas as extensões que ele nativamente suporta.

    with open(file_path, 'w') as f: f.write(content)

except Exception as e:
    print(f"Injection Error: {e}")
    sys.exit(1)
EOF_PYTHON

    python3 inject.py || exit 1
    
    # ==============================================================================
    # COMPILAÇÃO (SDK 36 + STATIC LINK)
    # ==============================================================================
    mkdir -p subprojects && cd subprojects
    rm -rf spirv-tools spirv-headers
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Tools.git spirv-tools
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Headers.git spirv-headers
    cd ..

    local build_dir="$workdir/mesa/build"
    local ndk_bin="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin"
    local ndk_sys="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/sysroot"
    local cver="35" # SDK 36 usa tools do 35/34 geralmente
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
    
    local pkg_dir="$workdir/pkg_$build_name"
    mkdir -p "$pkg_dir"
    cp "$lib" "$pkg_dir/vulkan.ad07XX.so"
    cd "$pkg_dir"
    patchelf --set-soname "vulkan.adreno.so" vulkan.ad07XX.so
    
    local hash=$(git -C "$workdir/mesa" rev-parse --short HEAD)
    local desc="Mesa Main SDK36 + Features Unlocked (No Exts forced)."

    echo "{
  \"schemaVersion\": 1,
  \"name\": \"Turnip-${build_name}-${hash}\",
  \"description\": \"$desc\",
  \"author\": \"mesa-ci\",
  \"driverVersion\": \"Mesa-V40-FeatsOnly\",
  \"libraryName\": \"vulkan.ad07XX.so\"
}" > meta.json
    
    zip -9 "$workdir/Turnip-${build_name}-${hash}.zip" vulkan.ad07XX.so meta.json
    echo -e "${green}Done: Turnip-${build_name}-${hash}.zip${nocolor}"
    
    echo "Turnip-${build_name}-${hash}" > "$workdir/tag"
    echo "Turnip V40 - Features Only" > "$workdir/release"
}

check_deps
prepare_ndk
build_driver

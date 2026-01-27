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
    local repo_url="https://gitlab.freedesktop.org/mesa/mesa.git"
    local branch="main"
    local build_name="Main-26.1-AutotunerPatch"

    echo -e "${green}Building: $build_name (Direct Patch Method)${nocolor}"
    
    cd "$workdir"
    if [ -d mesa ]; then rm -rf mesa; fi
    
    # 1. Clona a MAIN (26.1.0)
    git clone --depth 100 -b "$branch" "$repo_url" mesa
    cd mesa
    git config user.email "ci@turnip.builder" && git config user.name "Turnip CI Builder"

    # 2. Baixa o DIFF do MR !37802 diretamente do GitLab
    # Isso ignora histórico git e branches, pegando apenas as mudanças de código
    echo -e "${green}Downloading Autotuner Patch (!37802.diff)...${nocolor}"
    curl -L "https://gitlab.freedesktop.org/mesa/mesa/-/merge_requests/37802.diff" -o autotuner.patch
    
    # 3. Aplica o Patch
    echo -e "${green}Applying Autotuner Patch...${nocolor}"
    # Tenta aplicar. Se falhar (conflito de linha), continua mas avisa.
    # O 'git apply' é mais inteligente que o 'patch' comum para lidar com arquivos novos/renomeados
    if git apply --3way --ignore-space-change --ignore-whitespace autotuner.patch; then
        echo -e "${green}Patch Applied Successfully!${nocolor}"
        desc_extra="+ Autotuner Rewrite"
    else
        echo -e "${red}Patch Application Failed (Conflict). Skipping Autotuner.${nocolor}"
        echo "Building clean Main 26.1.0 instead."
        # Remove alterações parciais se falhou
        git reset --hard HEAD
        desc_extra="(Autotuner Skipped)"
    fi

    # 4. Força a versão 26.1.0
    echo "26.1.0-devel" > VERSION

    # 5. Aplica o UE4 Fix (Surgical)
    # Remove cache apenas das Queries
    grep -l "tu_bo_init_new_cached" src/freedreno/vulkan/tu_query*.cc | xargs sed -i 's/tu_bo_init_new_cached/tu_bo_init_new/g' || true

    mkdir -p subprojects && cd subprojects
    rm -rf spirv-tools spirv-headers
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Tools.git spirv-tools
    git clone --depth=1 https://github.com/KhronosGroup/SPIRV-Headers.git spirv-headers
    cd ..

    local build_dir="$workdir/mesa/build"
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
    
    local pkg_dir="$workdir/pkg_$build_name"
    mkdir -p "$pkg_dir"
    cp "$lib" "$pkg_dir/vulkan.ad07XX.so"
    cd "$pkg_dir"
    patchelf --set-soname "vulkan.adreno.so" vulkan.ad07XX.so
    
    local hash=$(git -C "$workdir/mesa" rev-parse --short HEAD)
    
    echo "{
  \"schemaVersion\": 1,
  \"name\": \"Turnip-${build_name}-${hash}\",
  \"description\": \"Mesa 26.1.0 ${desc_extra} + UE4 Fix\",
  \"author\": \"mesa-ci\",
  \"driverVersion\": \"Mesa-V48-26.1.0\",
  \"libraryName\": \"vulkan.ad07XX.so\"
}" > meta.json
    
    zip -9 "$workdir/Turnip-${build_name}-${hash}.zip" vulkan.ad07XX.so meta.json
    echo -e "${green}Done: Turnip-${build_name}-${hash}.zip${nocolor}"
    
    echo "Turnip-${build_name}-${hash}" > "$workdir/tag"
    echo "Turnip V48" > "$workdir/release"
}

check_deps
prepare_ndk
build_driver

#!/usr/bin/env bash
# Builds Pipetto-crypto's Vulkan wrapper (mesa, branch wrapper-dev) for Bannerlator testing.
# Taken from GameNative/mesa .github/scripts/build-wrapper-gamenative.sh; changes: REPO_ROOT is the
# Mesa checkout passed in $MESA_DIR, and the archive is named after the Pipetto commit.
set -euo pipefail

REPO_ROOT="${MESA_DIR:?set MESA_DIR to the mesa checkout}"
WORKDIR="${WORKDIR:-$REPO_ROOT/work}"
OUT_DIR="${OUT_DIR:-$REPO_ROOT/out}"
NDK_VERSION="${NDK_VERSION:-r29}"
ADRENOTOOLS_NDK_VERSION="${ADRENOTOOLS_NDK_VERSION:-r28c}"
ANDROID_API="${ANDROID_API:-24}"
ICD_API_VERSION="${ICD_API_VERSION:-1.3.289}"
BUILD_DATE="${BUILD_DATE:-$(date -u +%Y%m%d)}"
TERMUX_PREFIX=/data/data/com.termux/files/usr
TERMUX_REPO="${TERMUX_REPO:-https://packages-cf.termux.dev/apt/termux-main}"
TERMUX_PACKAGES="libdrm libandroid-shmem libxcb libx11 libxshmfence libxext libxrandr libxrender xorgproto libxau libxdmcp"

log() { printf '\033[0;32m==> %s\033[0m\n' "$*"; }
die() { printf '\033[0;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

mkdir -p "$WORKDIR" "$OUT_DIR"

fetch_ndk() {
    local ver="$1" dir="$WORKDIR/android-ndk-$1"
    if [ ! -d "$dir" ]; then
        log "Downloading NDK $ver" >&2
        curl -fsSL --retry 3 -o "$WORKDIR/ndk-$ver.zip" "https://dl.google.com/android/repository/android-ndk-$ver-linux.zip"
        unzip -q "$WORKDIR/ndk-$ver.zip" -d "$WORKDIR"
        rm -f "$WORKDIR/ndk-$ver.zip"
    fi
    echo "$dir"
}

termux_sysroot() {
    if [ -f "$TERMUX_PREFIX/lib/pkgconfig/xcb.pc" ]; then
        return
    fi
    log "Unpacking Termux packages into $TERMUX_PREFIX"
    local dl="$WORKDIR/termux-debs"
    mkdir -p "$dl"
    curl -fsSL --retry 3 "$TERMUX_REPO/dists/stable/main/binary-aarch64/Packages" > "$dl/Packages"
    sudo mkdir -p "$TERMUX_PREFIX"
    sudo chown -R "$(id -u):$(id -g)" /data
    local pkg path
    for pkg in $TERMUX_PACKAGES; do
        path=$(awk -v p="Package: $pkg" '$0==p{f=1} f && /^Filename:/{print $2; exit}' "$dl/Packages")
        [ -n "$path" ] || die "Termux package not found: $pkg"
        log "  $path"
        curl -fsSL --retry 3 -o "$dl/$(basename "$path")" "$TERMUX_REPO/$path"
        dpkg-deb -x "$dl/$(basename "$path")" "$dl/root"
    done
    cp -a "$dl/root/data/." /data/
    chmod -R u+rwX,go+rX /data
}

build_wrapper() {
    local ndk_bin="$NDK_DIR/toolchains/llvm/prebuilt/linux-x86_64/bin"
    local cross="$WORKDIR/wrapper-cross.txt"
    cat > "$cross" <<CROSS
[binaries]
c = '$ndk_bin/aarch64-linux-android${ANDROID_API}-clang'
cpp = '$ndk_bin/aarch64-linux-android${ANDROID_API}-clang++'
ar = '$ndk_bin/llvm-ar'
strip = '$ndk_bin/llvm-strip'
pkg-config = 'pkg-config'

[constants]
termux_dir = '$TERMUX_PREFIX'

[properties]
pkg_config_libdir = termux_dir + '/lib/pkgconfig:' + termux_dir + '/share/pkgconfig'

[built-in options]
c_args = ['-D__ANDROID_UNAVAILABLE_SYMBOLS_ARE_WEAK__', '-D__TERMUX__', '-D__USE_GNU', '-U__ANDROID__', '-I' + termux_dir + '/include', '-include', 'fcntl.h', '-include', 'unistd.h']
cpp_args = ['-D__ANDROID_UNAVAILABLE_SYMBOLS_ARE_WEAK__', '-D__TERMUX__', '-D__USE_GNU', '-U__ANDROID__', '-I' + termux_dir + '/include', '-include', 'fcntl.h', '-include', 'unistd.h']
c_link_args = ['-L' + termux_dir + '/lib', '-landroid-shmem']
cpp_link_args = ['-L' + termux_dir + '/lib', '-landroid-shmem']

[host_machine]
system = 'android'
cpu_family = 'aarch64'
cpu = 'armv8-a'
endian = 'little'
CROSS
    local build="$WORKDIR/build-wrapper"
    rm -rf "$build"
    cd "$REPO_ROOT"
    meson setup "$build" --cross-file "$cross" \
        -Dbuildtype=release \
        -Dcpp_rtti=false \
        -Dgbm=disabled \
        -Dopengl=false \
        -Dllvm=disabled \
        -Dshared-llvm=disabled \
        -Dplatforms=x11 \
        -Dgallium-drivers= \
        -Dxmlconfig=disabled \
        -Dvulkan-drivers=wrapper
    ninja -C "$build" src/vulkan/wrapper/libvulkan_wrapper.so
    WRAPPER_SO="$build/src/vulkan/wrapper/libvulkan_wrapper.so"
    ADRENOTOOLS_SRC="$REPO_ROOT/subprojects/libadrenotools"
    [ -f "$WRAPPER_SO" ] || die "libvulkan_wrapper.so was not built"
}

build_adrenotools() {
    local ndk="$1" build="$WORKDIR/build-adrenotools"
    rm -rf "$build"
    cmake -S "$ADRENOTOOLS_SRC" -B "$build" -G Ninja \
        -DCMAKE_TOOLCHAIN_FILE="$ndk/build/cmake/android.toolchain.cmake" \
        -DANDROID_ABI=arm64-v8a \
        -DANDROID_PLATFORM="android-$ANDROID_API" \
        -DANDROID_STL=c++_shared \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=ON \
        "-DCMAKE_SHARED_LINKER_FLAGS=-Wl,--as-needed -Wl,--exclude-libs,ALL -llog"
    cmake --build "$build" --target adrenotools hook_impl main_hook file_redirect_hook gsl_alloc_hook
    ADRENOTOOLS_BUILD="$build"
}

package() {
    local strip="$NDK_DIR/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip"
    local stage="$WORKDIR/stage"
    rm -rf "$stage"
    mkdir -p "$stage/usr/lib" "$stage/usr/share/vulkan/icd.d"

    cp "$WRAPPER_SO" "$OUT_DIR/libvulkan_wrapper.so.unstripped"
    "$strip" --strip-unneeded -o "$stage/usr/lib/libvulkan_wrapper.so" "$WRAPPER_SO"

    local lib f
    for lib in libadrenotools.so libhook_impl.so libmain_hook.so libfile_redirect_hook.so libgsl_alloc_hook.so; do
        f=$(find "$ADRENOTOOLS_BUILD" -name "$lib" -type f | head -n1)
        [ -n "$f" ] || die "$lib was not built"
        "$strip" --strip-unneeded -o "$stage/usr/lib/$lib" "$f"
    done

    cat > "$stage/usr/share/vulkan/icd.d/wrapper_icd.aarch64.json" <<JSON
{
    "ICD": {
        "api_version": "$ICD_API_VERSION",
        "library_path": "libvulkan_wrapper.so"
    },
    "file_format_version": "1.0.0"
}
JSON

    find "$stage" -type d -exec chmod 700 {} +
    find "$stage" -type f -exec chmod 600 {} +

    TZST_NAME="wrapper-pipetto-dev-$(git -C "$REPO_ROOT" rev-parse --short=8 HEAD)-$BUILD_DATE.tzst"
    tar -C "$stage" --owner=0 --group=0 --numeric-owner --sort=name -cf - usr | zstd -19 -T0 -q -o "$OUT_DIR/$TZST_NAME" -f
    (cd "$OUT_DIR" && sha256sum "$TZST_NAME" > "$TZST_NAME.sha256")
}

verify() {
    log "Archive listing"
    zstd -dc "$OUT_DIR/$TZST_NAME" | tar -tvf -
    local tmp="$WORKDIR/verify"
    rm -rf "$tmp"; mkdir -p "$tmp"
    zstd -dc "$OUT_DIR/$TZST_NAME" | tar -xf - -C "$tmp"
    local expected="usr/lib/libadrenotools.so
usr/lib/libfile_redirect_hook.so
usr/lib/libgsl_alloc_hook.so
usr/lib/libhook_impl.so
usr/lib/libmain_hook.so
usr/lib/libvulkan_wrapper.so
usr/share/vulkan/icd.d/wrapper_icd.aarch64.json"
    local actual
    actual=$(cd "$tmp" && find usr -type f | LC_ALL=C sort)
    [ "$actual" = "$expected" ] || die "Archive layout mismatch:
$actual"
    local so
    for so in "$tmp"/usr/lib/*.so; do
        file "$so"
        file "$so" | grep -q 'ELF 64-bit LSB shared object, ARM aarch64' || die "$so is not an aarch64 ELF shared object"
    done
    python3 -m json.tool "$tmp/usr/share/vulkan/icd.d/wrapper_icd.aarch64.json" >/dev/null
    ls -l "$OUT_DIR"
}

termux_sysroot
NDK_DIR="$(fetch_ndk "$NDK_VERSION")"
build_wrapper
log "libadrenotools commit: $(git -C "$ADRENOTOOLS_SRC" rev-parse HEAD 2>/dev/null || echo unknown)"
build_adrenotools "$(fetch_ndk "$ADRENOTOOLS_NDK_VERSION")"
package
verify

if [ -n "${GITHUB_OUTPUT:-}" ]; then
    {
        echo "tzst_name=$TZST_NAME"
        echo "tzst_path=$OUT_DIR/$TZST_NAME"
        echo "mesa_commit=$(git -C "$REPO_ROOT" rev-parse --short=10 HEAD)"
        echo "adrenotools_commit=$(git -C "$ADRENOTOOLS_SRC" rev-parse --short=10 HEAD 2>/dev/null || echo unknown)"
    } >> "$GITHUB_OUTPUT"
fi

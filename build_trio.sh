#!/bin/bash -e
set -o pipefail

green='\033[0;32m'
nocolor='\033[0m'

deps="ninja patchelf unzip curl pip flex bison zip git perl glslangValidator python3 patch"
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

apply_timeline_hack() {
cat << 'EOF_PATCH' > timeline_hack.patch
diff --git a/src/vulkan/runtime/vk_sync_timeline.c b/src/vulkan/runtime/vk_sync_timeline.c
index 4df11d81bda..6119126932d 100644
--- a/src/vulkan/runtime/vk_sync_timeline.c
+++ b/src/vulkan/runtime/vk_sync_timeline.c
@@ -507,46 +507,46 @@ vk_sync_timeline_wait_locked(struct vk_device *device,
                              enum vk_sync_wait_flags wait_flags,
                              uint64_t abs_timeout_ns)
 {
-   struct timespec abs_timeout_ts;
-   timespec_from_nsec(&abs_timeout_ts, abs_timeout_ns);
+    struct timespec abs_timeout_ts;
+    timespec_from_nsec(&abs_timeout_ts, abs_timeout_ns);
 
-   /* Wait on the queue_submit condition variable until the timeline has a
-    * time point pending that's at least as high as wait_value.
-    */
-   while (state->highest_pending < wait_value) {
-      int ret = u_cnd_monotonic_timedwait(&state->cond, &state->mutex,
-                                          &abs_timeout_ts);
-      if (ret == thrd_timedout)
-         return VK_TIMEOUT;
-
-      if (ret != thrd_success)
-         return vk_errorf(device, VK_ERROR_UNKNOWN, "cnd_timedwait failed");
-   }
-
-   if (wait_flags & VK_SYNC_WAIT_PENDING)
-      return VK_SUCCESS;
-
-   VkResult result = vk_sync_timeline_gc_locked(device, state, false);
-   if (result != VK_SUCCESS)
-      return result;
-
-   while (state->highest_past < wait_value) {
-      struct vk_sync_timeline_point *point = vk_sync_timeline_first_point(state);
-
-      /* Drop the lock while we wait. */
-      vk_sync_timeline_ref_point_locked(point);
-      mtx_unlock(&state->mutex);
-
-      result = vk_sync_wait(device, &point->sync, 0,
-                            VK_SYNC_WAIT_COMPLETE,
-                            abs_timeout_ns);
+    /* Wait until the timeline reaches the requested value */
+    while (state->highest_past < wait_value) {
+        struct vk_sync_timeline_point *point = NULL;
 
-      /* Pick the mutex back up */
-      mtx_lock(&state->mutex);
-      vk_sync_timeline_unref_point_locked(device, state, point);
-
-      /* This covers both VK_TIMEOUT and VK_ERROR_DEVICE_LOST */
-      if (result != VK_SUCCESS)
-         return result;
-
-      vk_sync_timeline_complete_point_locked(device, state, point);
-   }
-
-   return VK_SUCCESS;
+        /* Get the first pending point >= wait_value */
+        list_for_each_entry(struct vk_sync_timeline_point, p,
+                            &state->pending_points, link) {
+            if (p->value >= wait_value) {
+                vk_sync_timeline_ref_point_locked(p);
+                point = p;
+                break;
+            }
+        }
+
+        if (!point) {
+            /* Nothing pending, just wait on condition variable */
+            int ret = u_cnd_monotonic_timedwait(&state->cond, &state->mutex, &abs_timeout_ts);
+            if (ret == thrd_timedout)
+                return VK_TIMEOUT;
+            if (ret != thrd_success)
+                return vk_errorf(device, VK_ERROR_UNKNOWN, "cnd_timedwait failed");
+            continue;
+        }
+
+        /* Unlock while waiting on this specific timeline point */
+        mtx_unlock(&state->mutex);
+        VkResult r = vk_sync_wait(device, &point->sync, 0, VK_SYNC_WAIT_COMPLETE, abs_timeout_ns);
+        mtx_lock(&state->mutex);
+
+        vk_sync_timeline_unref_point_locked(device, state, point);
+
+        if (r != VK_SUCCESS)
+            return r;
+
+        vk_sync_timeline_complete_point_locked(device, state, point);
+    }
+
+    return VK_SUCCESS;
 }
 
+
 static VkResult
 vk_sync_timeline_wait(struct vk_device *device,
                       struct vk_sync *sync,
EOF_PATCH
    patch -p1 --fuzz=3 --ignore-whitespace < timeline_hack.patch || true
}

apply_a8xx_patch() {
    if [ -f "$workdir/tu_gen8_clean.patch" ]; then
        patch -p1 --fuzz=3 --ignore-whitespace < "$workdir/tu_gen8_clean.patch" || { echo "A8xx patch failed!"; exit 1; }
    else
        echo "Missing tu_gen8_clean.patch in $workdir"
        exit 1
    fi
}

apply_a6xx_fix() {
    grep -l "tu_bo_init_new_cached" src/freedreno/vulkan/tu_query*.cc | xargs sed -i 's/tu_bo_init_new_cached/tu_bo_init_new/g' || true
}

compile_mesa() {
    local build_name=$1
    local output_tag=$2
    
    echo -e "${green}Building: $build_name${nocolor}"
    
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
  \"name\": \"Turnip-${output_tag}\",
  \"description\": \"$build_name\",
  \"author\": \"StevenMX\",
  \"packageVersion\": \"1\",
  \"vendor\": \"Mesa\",
  \"driverVersion\": \"$output_tag\",
  \"minApi\": 28,
  \"libraryName\": \"vulkan.ad07XX.so\"
}" > meta.json
    
    zip -9 "$workdir/Turnip-${output_tag}.zip" vulkan.ad07XX.so meta.json
    echo -e "${green}Done: Turnip-${output_tag}.zip${nocolor}"
}

check_deps
prepare_ndk

cd "$workdir"
if [ -d mesa ]; then rm -rf mesa; fi
git clone --depth 100 -b main https://gitlab.freedesktop.org/mesa/mesa.git mesa
cd mesa
git config user.email "ci@turnip.builder" && git config user.name "Turnip CI Builder"
apply_a8xx_patch
apply_timeline_hack
compile_mesa "Mesa Main + A8xx + Timeline" "V68-A8xx-Timeline"

cd "$workdir"
rm -rf mesa
git clone --depth 100 -b tu-newat https://gitlab.freedesktop.org/PixelyIon/mesa.git mesa
cd mesa
git config user.email "ci@turnip.builder" && git config user.name "Turnip CI Builder"
apply_a8xx_patch
apply_timeline_hack
apply_a6xx_fix
compile_mesa "PixelyIon Autotuner + A8xx + Timeline + A6xx Fix" "V68-Autotuner-Full"

cd "$workdir"
rm -rf mesa
git clone --depth 100 -b main https://gitlab.freedesktop.org/mesa/mesa.git mesa
cd mesa
git config user.email "ci@turnip.builder" && git config user.name "Turnip CI Builder"
compile_mesa "Mesa Main Vanilla" "V68-Main-Vanilla"

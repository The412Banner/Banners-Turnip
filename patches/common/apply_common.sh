#!/usr/bin/env bash
# Patches every leg ships - Android, Wayland, Linux, perf. Run from the Mesa tree:
# apply_common.sh <mesa-dir>. Any patch that does not apply, or whose result is not in the tree
# afterwards, fails the build: a driver without the fix must not be zipped. When Mesa upstream
# carries a fix, delete the patch here (see SOURCE). Our two KGSL fixes went upstream in Mesa MR 44838
# (2026-10-08), so this script now only asserts that Mesa still has them.
set -eu
cd "${1:?usage: apply_common.sh <mesa-dir>}"
here="$(cd "$(dirname "$0")" && pwd)"

# Max's WinNative series (patches/a8xx-winnative/0001-0005: mesh shaders, wave32, A8xx hang fixes)
# goes on the A8xx driver only. Mesh shaders and wave32 also switch on for A7xx (and wave32 for
# A6xx gen4), where they can steer DX12 games onto slower emulated paths, so the A6xx/A7xx drivers
# carry no patches at all. The A8xx driver is the one whose EXTRA_PATCH is the gen8 stack.
a8xx=0
case "${EXTRA_PATCH:-}" in *a8xx_gen8*) a8xx=1 ;; esac
series=()
if [ "$a8xx" = 1 ]; then
	series+=("$here"/../a8xx-winnative/0*.patch)
	[ "$(ls "$here"/../a8xx-winnative/0*.patch | wc -l)" = 5 ] \
		|| { echo "[common] expected 5 patches in a8xx-winnative/" >&2; exit 1; }
fi
echo "[common] driver: $([ "$a8xx" = 1 ] && echo "A8xx (Max's series)" || echo "A6xx/A7xx (no patches: both KGSL fixes are in Mesa)")"

for p in ${series[@]+"${series[@]}"}; do
	echo "[common] applying $(basename "$p")"
	rc=0
	out="$(patch -p1 -N --fuzz=3 --no-backup-if-mismatch < "$p" 2>&1)" || rc=$?
	echo "$out" | sed 's/^/    /'
	[ "$rc" = 0 ] || { echo "[common] $(basename "$p") did not apply cleanly (patch exit $rc) - rebase it onto this Mesa, or drop it if upstream has the fix" >&2; exit 1; }
done

# Assert the tree rather than trust the patches.
# kgsl_syncobj_merge: Mesa carries the fix since 1da50a1b (MR 44838, 2026-10-08), which rewrote the
# function around a tu_device parameter. A tree without it is older than this script supports.
grep -q "kgsl_syncobj_merge(struct tu_device \*device" src/freedreno/vulkan/tu_knl_kgsl.cc \
	|| { echo "[common] Mesa lacks the upstream kgsl_syncobj_merge fix (MR 44838); this Mesa is too old" >&2; exit 1; }
if [ "$a8xx" = 1 ]; then
	[ -f src/freedreno/vulkan/tu_mesh.cc ] && grep -q "EXT_mesh_shader = tu_has_mesh_shader(device)" src/freedreno/vulkan/tu_device.cc \
		|| { echo "[common] winnative/0001 (mesh shaders) did not reach tu_mesh.cc / tu_device.cc" >&2; exit 1; }
	grep -q "tu_mesh.cc" src/freedreno/vulkan/meson.build \
		|| { echo "[common] winnative/0001 (mesh shaders) did not reach meson.build" >&2; exit 1; }
	grep -q "HALF_SUBGROUP_SIZE 32" src/freedreno/ir3/ir3_lower_subgroups.c \
		|| { echo "[common] winnative/0002 (wave32 subgroups) did not reach ir3_lower_subgroups.c" >&2; exit 1; }
	grep -q "cube_coord_hang_quirk = True" src/freedreno/common/freedreno_devices.py \
		|| { echo "[common] winnative/0003 (cube-coord sanitize) did not reach freedreno_devices.py" >&2; exit 1; }
	grep -q "SP_GFX_BINDLESS_INVALIDATE" src/freedreno/vulkan/tu_cmd_buffer.h \
		|| { echo "[common] winnative/0004 (bindless invalidate) did not reach tu_cmd_buffer.h" >&2; exit 1; }
	grep -q "KGSL_MEMFLAGS_VBO" src/freedreno/vulkan/tu_knl_kgsl.cc \
		|| { echo "[common] winnative/0005 (IB VBO alias) did not reach tu_knl_kgsl.cc" >&2; exit 1; }
else
	[ ! -f src/freedreno/vulkan/tu_mesh.cc ] \
		|| { echo "[common] Max's mesh patch reached a non-A8xx driver" >&2; exit 1; }
fi
# Zero-timeout polls: Mesa carries the fix since e984ef29 (MR 44838, 2026-10-08): a zero timeout
# reads the retired timestamp (kgsl_poll_timestamp) instead of reaching the wait ioctl.
grep -q "return kgsl_poll_timestamp(device, context_id, timestamp);" src/freedreno/vulkan/tu_knl_kgsl.cc \
	|| { echo "[common] Mesa lacks the upstream zero-timeout poll fix (MR 44838); this Mesa is too old" >&2; exit 1; }

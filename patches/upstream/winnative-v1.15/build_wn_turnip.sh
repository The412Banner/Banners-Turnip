#!/bin/bash -e
set -o pipefail
#
# WN-Turnip production build driver — produces both balanced (b) and
# performance (p) variants from latest upstream mesa main with the WinNative
# A8xx workaround set applied.
#
# Set BUILD_VARIANTS to override which are built, e.g. BUILD_VARIANTS="p".
#
# Output ZIPs:
#   ../WN-Turnip-${BUILD_VERSION}-b_Axxx.zip
#   ../WN-Turnip-${BUILD_VERSION}-p_Axxx.zip

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

export BUILD_VERSION="${BUILD_VERSION:-1.0}"
export EXTRA_PATCH=""
export EXTRA_SCRIPT="patches/fix_gralloc_flushall.py:patches/fix_a8xx_dev_info.py:patches/apply_a8xx_gpus.py:patches/apply_a7xx_gen1_quirks.py:patches/apply_a7xx_gen2_ubwc_hint.py:patches/add_aimapper_gralloc.py:patches/add_ubwc_swapchain_usage.py"

# Clone mesa once and build every variant from that same tree. Cloning per
# variant let upstream advance between them, so a release could ship a -b and a
# -p built from different mesa commits, and the release notes could only name
# one of them. Set MESA_LOCAL_SRC to reuse an existing checkout instead.
if [ -z "${MESA_LOCAL_SRC:-}" ]; then
	mesa_ref="$SCRIPT_DIR/mesa_ref"
	rm -rf "$mesa_ref"
	echo "Cloning mesa main once for all variants..."
	git clone --depth=1 -b main https://gitlab.freedesktop.org/mesa/mesa "$mesa_ref"
	export MESA_LOCAL_SRC="$mesa_ref"
fi

MESA_COMMIT="$(git -C "$MESA_LOCAL_SRC" rev-parse HEAD)"
MESA_VERSION="$(tr -d '[:space:]' < "$MESA_LOCAL_SRC/VERSION" 2>/dev/null || echo unknown)"
echo "$MESA_COMMIT" > "$SCRIPT_DIR/mesa_hash.txt"
echo "$MESA_VERSION" > "$SCRIPT_DIR/mesa_version.txt"
echo "Mesa: $MESA_COMMIT ($MESA_VERSION)"

read -ra variants <<< "${BUILD_VARIANTS:-b p}"

for variant in "${variants[@]}"; do
	echo ""
	echo "============================================"
	echo "  Building WN-Turnip-${BUILD_VERSION}-${variant}"
	echo "============================================"

	rm -rf turnip_workdir /tmp/turnip-main
	export BUILD_VARIANT="$variant"

	log_file="build_log_${variant}.txt"
	./build_turnip.sh 2>&1 | tee "$log_file"

	zipname="WN-Turnip-${BUILD_VERSION}-${variant}_Axxx.zip"
	cp "turnip_workdir/${zipname}" "./${zipname}" 2>/dev/null || true
	cp "./${zipname}" "${ROOT_DIR}/${zipname}" 2>/dev/null || true
done

echo ""
echo "============================================"
echo "  Build Summary"
echo "============================================"
echo "mesa: ${MESA_COMMIT} (${MESA_VERSION})"
for variant in "${variants[@]}"; do
	zipname="WN-Turnip-${BUILD_VERSION}-${variant}_Axxx.zip"
	echo "${variant}: $(ls -lh "${ROOT_DIR}/${zipname}" 2>/dev/null | awk '{print $5}' || echo 'MISSING')"
done

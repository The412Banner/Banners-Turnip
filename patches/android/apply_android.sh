#!/usr/bin/env bash
# Android-only gralloc / swapchain changes from Droid-Deck/Drivers (patches/scripts; Leb-Sun, Max).
# Only the AdrenoTools (X11) legs build Mesa's Android platform, so only build_turnip.sh runs this,
# after EXTRA_PATCH. Every script exits non-zero when its anchor is gone: a driver without them
# is not zipped. Run from the Mesa tree: apply_android.sh <mesa-dir>. Notes: SOURCE.
set -eu
cd "${1:?usage: apply_android.sh <mesa-dir>}"
here="$(cd "$(dirname "$0")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$here${PYTHONPATH:+:$PYTHONPATH}"

for s in gralloc_ubwc_detect.py add_aimapper_gralloc.py add_ubwc_swapchain_usage.py; do
	echo "[android] $s"
	python3 "$here/$s" || { echo "[android] $s failed" >&2; exit 1; }
done

# Assert the result rather than trust the scripts.
grep -q "U_GRALLOC_TYPE_AIMAPPER" src/util/u_gralloc/u_gralloc.c \
	|| { echo "[android] IMapper5 backend did not reach u_gralloc.c" >&2; exit 1; }
[ -f src/util/u_gralloc/u_gralloc_aimapper.c ] \
	|| { echo "[android] u_gralloc_aimapper.c missing" >&2; exit 1; }
grep -q "ahb_vendor_usage_compressed = 0x10000000ull" src/freedreno/vulkan/tu_device.cc \
	|| { echo "[android] UBWC swapchain usage did not reach tu_device.cc" >&2; exit 1; }

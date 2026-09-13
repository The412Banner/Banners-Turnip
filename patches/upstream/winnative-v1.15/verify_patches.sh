#!/bin/bash
set -uo pipefail
#
# Assert that every patch reported itself applied, per variant.
#
# A patch script that finds no anchor logs a warning and moves on, so the build
# still succeeds and the zip still installs — it is just silently missing the
# fix. Checking exit codes cannot catch that; only the log can. Run after
# build_wn_turnip.sh, from the directory holding build_log_<variant>.txt.
#
# Usage: ./verify_patches.sh [variant ...]   (default: b p)

variants=("$@")
[ ${#variants[@]} -gt 0 ] || variants=(b p)

if [ -n "${GITHUB_ACTIONS:-}" ]; then
	err() { echo "::error::$*"; }
	warn() { echo "::warning::$*"; }
else
	err() { echo "ERROR: $*" >&2; }
	warn() { echo "WARNING: $*" >&2; }
fi

# Reported by every variant. The RedMagic display fixes ride EXTRA_SCRIPT, so a
# variant missing any of these has no green-screen fix in it.
common=(
	"fix_a8xx_dev_info.py: done"
	"apply_a8xx_gpus.py: done"
	"apply_a7xx_gen1_quirks.py: done"
	"apply_a7xx_gen2_ubwc_hint.py: done"
	"add_aimapper_gralloc.py: done"
	"backend selection table"
	"u_gralloc_type enum"
	"create() declaration"
	"meson source list"
	"add_ubwc_swapchain_usage.py: done"
	"vendor UBWC bit on the AHB usage answer"
	"vk_physical_device vendor-usage field"
	"turnip sets the vendor usage bit"
)

# -p only: without these the archive is a -b wearing a -p name.
perf=(
	"KGSL_CONTEXT_PWR_CONSTRAINT to context flags"
	"PWR_MAX helper"
	"initial PWR_MAX constraint setup"
	"KGSL_CMDBATCH_PWR_CONSTRAINT"
	"periodic PWR_MAX refresh"
)

fail=0

for v in "${variants[@]}"; do
	log="build_log_${v}.txt"
	if [ ! -f "$log" ]; then
		err "missing $log"
		fail=1
		continue
	fi

	missing=0

	for line in "${common[@]}"; do
		grep -qF "$line" "$log" || {
			err "variant ${v}: '${line}' never reported — the RedMagic display fix is NOT in this build"
			missing=1
		}
	done

	if [ "$v" = "p" ] || [ "$v" = "p1" ] || [ "$v" = "p2" ]; then
		for line in "${perf[@]}"; do
			grep -qF "$line" "$log" || {
				err "variant ${v}: '${line}' never reported — no PWR_MAX clock forcing"
				missing=1
			}
		done
	fi

	# Anchor drift, excluding the autotune drawcall gate upstream restructured
	# away on purpose (see MAINTENANCE.md).
	drift=$(grep -E "anchor absent" "$log" | grep -v "drawcall anchor absent" || true)
	if [ -n "$drift" ]; then
		warn "variant ${v} has a drifted anchor:"
		printf '%s\n' "$drift"
	fi

	if [ "$missing" -eq 0 ]; then
		echo "  ${v}: all patches reported"
	else
		echo "  ${v}: INCOMPLETE — see the errors above"
		fail=1
	fi
done

[ "$fail" -eq 0 ] || exit 1
echo "verify_patches.sh: OK"

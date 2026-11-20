#!/usr/bin/env python3
# From: Vauzi-17
"""A8XX: Set FORCE_BI_DIR_LRZ_DISABLE in sysmem and disabled LRZ render passes.

On Adreno 8xx, hardware traces show GRAS_SC_BIN_CNTL (0x8231) sets bit 14
(FORCE_BI_DIR_LRZ_DISABLE = 1, e.g. 0x30004000) during sysmem rendering passes
to prevent LRZ cache corruption from bi-directional depth testing across multi-draw
passes. In GMEM passes where LRZ is disabled, bi-directional updates are likewise
disabled to preserve consistent hardware depth-culling state.

Run from Mesa source root. Idempotent and safe to run multiple times.
"""
import sys

NAME = "53-a8xx-lrz-bidir-disable.py"
MARKER = "force_bi_dir_lrz_disable"

CMD_BUF = "src/freedreno/vulkan/tu_cmd_buffer.cc"
LRZ_CC = "src/freedreno/vulkan/tu_lrz.cc"

EDITS = [
    (
        CMD_BUF,
        "   bool cons_vis_in_binning;\n};\n",
        "   bool cons_vis_in_binning;\n   bool force_bi_dir_lrz_disable;\n};\n",
        1,
    ),
    (
        CMD_BUF,
        "                                 .cons_vis_in_binning = p.cons_vis_in_binning, ));\n",
        "                                 .cons_vis_in_binning = p.cons_vis_in_binning,\n"
        "                                 .force_bi_dir_lrz_disable = p.force_bi_dir_lrz_disable, ));\n",
        1,
    ),
    (
        CMD_BUF,
        "         .force_lrz_dis = CHIP >= A7XX && disable_lrz,\n      });\n",
        "         .force_lrz_dis = CHIP >= A7XX && disable_lrz,\n"
        "         .force_bi_dir_lrz_disable = CHIP >= A8XX && disable_lrz,\n      });\n",
        1,
    ),
    (
        CMD_BUF,
        "         cmd->device->physical_device->info->props.has_lrz_feedback\n"
        "            ? LRZ_FEEDBACK_EARLY_Z_OR_EARLY_Z_LATE_Z\n"
        "            : LRZ_FEEDBACK_NONE,\n   });\n",
        "         cmd->device->physical_device->info->props.has_lrz_feedback\n"
        "            ? LRZ_FEEDBACK_EARLY_Z_OR_EARLY_Z_LATE_Z\n"
        "            : LRZ_FEEDBACK_NONE,\n"
        "      .force_bi_dir_lrz_disable = CHIP >= A8XX,\n   });\n",
        1,
    ),
    (
        LRZ_CC,
        "      const struct tu_reg_value reg = GRAS_SC_BIN_CNTL(CHIP, .force_lrz_dis = true);\n",
        "      const struct tu_reg_value reg = GRAS_SC_BIN_CNTL(CHIP, .force_lrz_dis = true,\n"
        "                                                             .force_bi_dir_lrz_disable = CHIP >= A8XX);\n",
        1,
    ),
]


def main():
    files = {}
    for path, _, _, _ in EDITS:
        if path not in files:
            try:
                files[path] = open(path, "r", encoding="utf-8").read()
            except OSError as e:
                print(f"{NAME}: WARNING cannot read {path}: {e}; skipped")
                return 0

    already = all(MARKER in files[path] for path in files)
    if already:
        print(f"{NAME}: already applied ({MARKER} present in all targets)")
        return 0

    for path, old, _, count in EDITS:
        actual = files[path].count(old)
        if actual != count:
            print(
                f"{NAME}: ERROR in {path}: expected {count} occurrence(s) of anchor, found {actual}",
                file=sys.stderr,
            )
            return 1

    for path, old, new, _ in EDITS:
        files[path] = files[path].replace(old, new, 1)

    for path, content in files.items():
        try:
            open(path, "w", encoding="utf-8").write(content)
        except OSError as e:
            print(f"{NAME}: ERROR cannot write {path}: {e}", file=sys.stderr)
            return 1

    print(f"{NAME}: applied successfully (A8xx FORCE_BI_DIR_LRZ_DISABLE configured)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

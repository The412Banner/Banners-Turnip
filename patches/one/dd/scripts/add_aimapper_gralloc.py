import shutil
from pathlib import Path

from mesa_edit import replace

GRALLOC = Path('src/util/u_gralloc')
SOURCE = Path(__file__).resolve().parent.parent / 'aimapper' / 'u_gralloc_aimapper.c'

shutil.copyfile(SOURCE, GRALLOC / SOURCE.name)
print(f'{GRALLOC / SOURCE.name}: backend source installed')

replace(
    GRALLOC / 'meson.build',
    "  'u_gralloc_qcom.c',\n)",
    "  'u_gralloc_qcom.c',\n  'u_gralloc_aimapper.c',\n)",
    'meson source list',
)
replace(
    GRALLOC / 'u_gralloc.h',
    '   U_GRALLOC_TYPE_GRALLOC4,\n   U_GRALLOC_TYPE_CROS,',
    '   U_GRALLOC_TYPE_GRALLOC4,\n   U_GRALLOC_TYPE_AIMAPPER,\n   U_GRALLOC_TYPE_CROS,',
    'u_gralloc_type enum',
)
replace(
    GRALLOC / 'u_gralloc_internal.h',
    'extern struct u_gralloc *u_gralloc_qcom_create(void);',
    'extern struct u_gralloc *u_gralloc_aimapper_create(void);\n'
    'extern struct u_gralloc *u_gralloc_qcom_create(void);',
    'create() declaration',
)
replace(
    GRALLOC / 'u_gralloc.c',
    '   {.type = U_GRALLOC_TYPE_LIBDRM, .create = u_gralloc_libdrm_create},',
    '   {.type = U_GRALLOC_TYPE_AIMAPPER, .create = u_gralloc_aimapper_create},\n'
    '   {.type = U_GRALLOC_TYPE_LIBDRM, .create = u_gralloc_libdrm_create},',
    'backend selection table',
)

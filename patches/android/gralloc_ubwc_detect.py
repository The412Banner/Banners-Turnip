# Droid-Deck/Drivers patches/scripts/gralloc_ubwc_detect.py, plus a skip for the A8xx gen8 stack,
# whose "HACK: u_gralloc: always use ubwc detection path" already dropped the gmsm check.
from pathlib import Path
from mesa_edit import replace

PATH = 'src/util/u_gralloc/u_gralloc_fallback.c'
GEN8_MARKER = 'TODO: Actually find a way to detect a Qualcomm vendor allocated buffer'

if GEN8_MARKER in Path(PATH).read_text():
    print(f'{PATH}: gmsm check already removed by the gen8 stack, skipping')
else:
    replace(
        PATH,
        """   uint32_t gmsm = ('g' << 24) | ('m' << 16) | ('s' << 8) | 'm';
   if (hnd->handle->numInts >= 2 && hnd->handle->data[hnd->handle->numFds] == gmsm) {
      /* This UBWC flag was introduced in a5xx. */
      bool ubwc = hnd->handle->data[hnd->handle->numFds + 1] & 0x08000000;""",
        """   if (hnd->handle->numInts >= 2) {
      bool ubwc = hnd->handle->data[hnd->handle->numFds + 1] & 0x08000000;""",
        'UBWC detection without the legacy gmsm header',
    )

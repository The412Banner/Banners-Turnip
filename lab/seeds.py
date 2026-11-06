"""Code pointers stored in a driver's data: the start addresses of functions that are only reached
through tables (Vulkan entry points, format packers, NIR folding tables). Same rules as DriverLab's
Kotlin version: RELATIVE/ABS64/GLOB_DAT relocations (RELA) and RELR-packed relocations, values that
land 4-byte aligned inside an executable section."""
import struct

R_ABS64, R_GLOB_DAT, R_JUMP_SLOT, R_RELATIVE = 257, 1025, 1026, 1027

def code_pointers(path):
    b = open(path, 'rb').read()
    if b[:4] != b'\x7fELF' or b[4] != 2 or b[5] != 1: return set()
    shoff, = struct.unpack_from('<Q', b, 0x28); shentsize, shnum = struct.unpack_from('<HH', b, 0x3A)
    secs = []
    for i in range(shnum):
        o = shoff + i * shentsize
        name, typ, flags, addr, off, size, link, info, align, entsize = struct.unpack_from('<IIQQQQIIQQ', b, o)
        secs.append(dict(type=typ, flags=flags, addr=addr, off=off, size=size, link=link, entsize=entsize))
    exe = [(s['addr'], s['addr'] + s['size']) for s in secs if s['flags'] & 4 and s['size']]
    def in_code(v): return v % 4 == 0 and any(a <= v < e for a, e in exe)
    def read64(va):
        for s in secs:
            if s['type'] != 8 and s['addr'] <= va < s['addr'] + s['size'] and s['addr']:   # not NOBITS
                return struct.unpack_from('<Q', b, s['off'] + va - s['addr'])[0]
        return None
    def symval(symtab, idx):
        s = secs[symtab]; o = s['off'] + idx * 24
        _, _, _, shndx, value, _ = struct.unpack_from('<IBBHQQ', b, o)
        return value if shndx else None
    out = set()
    for s in secs:
        if s['type'] == 4 and s['entsize'] == 24:                              # SHT_RELA
            for i in range(s['size'] // 24):
                off, info, add = struct.unpack_from('<QQq', b, s['off'] + i * 24)
                t, sym = info & 0xffffffff, info >> 32
                if t == R_RELATIVE: v = add
                elif t in (R_ABS64, R_GLOB_DAT, R_JUMP_SLOT) and sym:
                    sv = symval(s['link'], sym); v = None if sv is None else sv + add
                else: v = None
                if v is not None and in_code(v): out.add(v)
        elif s['type'] in (19, 0x6fffff00):                                    # SHT_RELR, SHT_ANDROID_RELR
            base = 0
            for i in range(s['size'] // 8):
                e, = struct.unpack_from('<Q', b, s['off'] + i * 8)
                locs = []
                if e & 1 == 0: locs.append(e); base = e + 8
                else:
                    for k in range(1, 64):
                        if e >> k & 1: locs.append(base + (k - 1) * 8)
                    base += 63 * 8
                for va in locs:
                    v = read64(va)
                    if v is not None and in_code(v): out.add(v)
    return out

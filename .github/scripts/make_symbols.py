#!/usr/bin/env python3
"""Names file for DriverLab: the function names (and Mesa source file and line) of one released
Android driver, so DriverLab's source-code view can show real names for a stripped driver.

The released driver is the unstripped build stripped with llvm-strip; this checks that, reads the
function symbols of the unstripped copy, and looks up each function's source line in the -g build
of the same source by name (the -g build is never shipped). Output: symbols-<build-id>.tsv.gz,
named by the driver's GNU build ID so DriverLab can find it from the driver file alone.

Columns: address (hex, in the released file), size, name (demangled), symbol (as in the file),
source file (relative to the Mesa tree; "build:" = generated during the build), line.
"""
import argparse, gzip, hashlib, os, re, struct, subprocess, sys, tempfile, zipfile

ap = argparse.ArgumentParser()
ap.add_argument('--zip', required=True)
ap.add_argument('--unstripped', required=True)
ap.add_argument('--debug')
ap.add_argument('--ndk-bin', required=True)
ap.add_argument('--tag', required=True)
ap.add_argument('--variant', required=True)
ap.add_argument('--mesa-commit', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()
tool = lambda n: os.path.join(a.ndk_bin, n)

def build_id(data):
    """GNU build ID from the section headers (.note.gnu.build-id)."""
    shoff, = struct.unpack_from('<Q', data, 0x28); shentsize, shnum, shstrndx = struct.unpack_from('<HHH', data, 0x3A)
    sec = lambda i: struct.unpack_from('<IIQQQQIIQQ', data, shoff + i * shentsize)
    stroff = sec(shstrndx)[4]
    for i in range(shnum):
        name, typ, _, _, off, size, *_ = sec(i)
        if typ != 7: continue                                  # SHT_NOTE
        p = off
        while p + 12 <= off + size:
            nsz, dsz, nt = struct.unpack_from('<III', data, p)
            n = data[p + 12:p + 12 + nsz]; d = p + 12 + (nsz + 3) // 4 * 4
            if nt == 3 and n.rstrip(b'\0') == b'GNU': return data[d:d + dsz].hex()
            p = d + (dsz + 3) // 4 * 4
    return None

with zipfile.ZipFile(a.zip) as z:
    shipped = z.read('libvulkan_freedreno.so')
sha = hashlib.sha256(shipped).hexdigest()
bid = build_id(shipped)
if not bid: sys.exit('no GNU build ID in the released driver')

with tempfile.TemporaryDirectory() as t:
    s = os.path.join(t, 's.so')
    subprocess.run([tool('llvm-strip'), '-o', s, a.unstripped], check=True)
    if hashlib.sha256(open(s, 'rb').read()).hexdigest() != sha:
        sys.exit('the unstripped build stripped is not the released driver; no names file')

def functions(path):
    """address -> (size, symbol); global names win over local ones at the same address."""
    out = {}
    nm = subprocess.run([tool('llvm-nm'), '--defined-only', '--print-size', '--numeric-sort', path],
                        capture_output=True, text=True, check=True).stdout
    for line in nm.splitlines():
        p = line.split(None, 3)
        if len(p) != 4 or p[2] not in ('t', 'T', 'W', 'w'): continue
        addr, size = int(p[0], 16), int(p[1], 16)
        if not size: continue
        if addr not in out or (p[2] in 'TW' and out[addr][2] in 'tw'): out[addr] = (size, p[3], p[2])
    return out

fns = functions(a.unstripped)
syms = [v[1] for _, v in sorted(fns.items())]
dem = subprocess.run([tool('llvm-cxxfilt')], input='\n'.join(syms), capture_output=True, text=True, check=True).stdout.splitlines()
demangled = dict(zip(syms, dem)) if len(dem) == len(syms) else {}

src = {}
if a.debug and os.path.exists(a.debug):
    by_name = {v[1]: addr for addr, v in functions(a.debug).items()}
    q = [(n, by_name[n]) for n in syms if n in by_name]
    out = subprocess.run([tool('llvm-symbolizer'), '--obj=' + a.debug, '--no-inlines', '--output-style=GNU', '--functions=none'],
                         input='\n'.join(f'{x:#x}' for _, x in q), capture_output=True, text=True).stdout.splitlines()
    for (n, _), loc in zip(q, out):
        m = re.match(r'^(.*):(\d+)(?: \(discriminator \d+\))?$', loc)
        if not m or m.group(2) == '0': continue
        f = os.path.normpath(m.group(1))
        i = f.find('/turnip_workdir/mesa/')
        if i < 0: continue                                     # NDK / libc++ code: not Mesa
        f = f[i + len('/turnip_workdir/mesa/'):]
        f = re.sub(r'^build-android-aarch64(-g)?/', 'build:', f)
        src[n] = (f, m.group(2))

os.makedirs(a.out, exist_ok=True)
name = os.path.join(a.out, f'symbols-{bid}.tsv.gz')
with gzip.open(name, 'wt', compresslevel=9) as g:
    g.write('# DriverLab names file 1\n')
    g.write(f'# driver\t{os.path.basename(a.zip)}\n# variant\t{a.variant}\n# release\t{a.tag}\n')
    g.write(f'# mesa\t{a.mesa_commit}\n# build-id\t{bid}\n# sha256\t{sha}\n')
    g.write('# address\tsize\tname\tsymbol\tfile\tline\n')
    for addr, (size, sym, _) in sorted(fns.items()):
        f, l = src.get(sym, ('', ''))
        g.write(f'{addr:x}\t{size}\t{demangled.get(sym, sym)}\t{sym}\t{f}\t{l}\n')
print(f'{name}: {len(fns)} functions, {len(src)} with a source line, build ID {bid}')

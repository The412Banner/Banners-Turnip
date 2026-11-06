#!/usr/bin/env python3
"""Speed and rule probe for the DriverLab fixes (lab only).

A: aaa, then af at each code pointer it missed (what the app does now), timed.
B: a flag at each code pointer before aaa (aa analyses sym.* flags), timed.
C: xref kinds (axt) of every start in A: which rule separates switch pieces from real functions.
D: names file path: flags only (no af), timing, then pdg of sample functions to see whether the
   decompiler prints the real names of the functions they call.
usage: probe.py RELEASED_SO SYMTAB_SO NAMES_TSV_GZ OUT_DIR   (env as score.py)
"""
import gzip, json, os, re, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seeds as seedmod
from elftools.elf.elffile import ELFFile
REL, SYM, NAMES, OUT = sys.argv[1:5]
RIZIN, PLUGIN, SLEIGH = os.environ['RIZIN'], os.environ['GHIDRA_PLUGIN'], os.environ['SLEIGH']
AFL = re.compile(r'^(0x[0-9a-fA-F]+)\s+(\d+)\s+(\d+)(?:\s+->\s+(\d+))?\s+(.+)$')
os.makedirs(OUT, exist_ok=True)

class Engine:
    def __init__(self, path):
        self.p = subprocess.Popen([RIZIN, '-q0', '-N', '-e', 'scr.color=0', '-e', 'scr.utf8=false', '-e', 'scr.interactive=false',
                                   '-e', 'bin.cache=true', '-l', PLUGIN, path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=open(os.path.join(OUT, 'rizin-stderr.log'), 'ab'))
        self.read(); self.cmd('e ghidra.sleighhome=' + SLEIGH)
    def read(self):
        buf = bytearray()
        while True:
            b = self.p.stdout.read(1)
            if not b: raise IOError('engine stopped')
            if b == b'\0': return buf.decode('utf-8', 'replace')
            buf += b
    def cmd(self, c):
        self.p.stdin.write((c + '\n').encode()); self.p.stdin.flush(); return self.read()
    def close(self): self.p.kill()

def afl(e):
    out = {}
    for l in e.cmd('afl').splitlines():
        m = AFL.match(l.strip())
        if m: out[int(m.group(1), 16)] = (int(m.group(4) or m.group(3)), m.group(5))
    return out

f = ELFFile(open(SYM, 'rb')); t = f.get_section_by_name('.text'); ta, tl = t['sh_addr'], t['sh_size']
truth = {}
for s in f.get_section_by_name('.symtab').iter_symbols():
    if s['st_info']['type'] == 'STT_FUNC' and s['st_size'] and ta <= s['st_value'] < ta + tl: truth.setdefault(s['st_value'], s['st_size'])
T = set(truth)
def sc(fl):
    F = {a for a in fl if ta <= a < ta + tl}; h = T & F
    return {'found': len(F), 'recall': round(100 * len(h) / len(T), 2), 'precision': round(100 * len(h) / max(1, len(F)), 2)}
SEEDS = seedmod.code_pointers(REL)
r = {}

# A
e = Engine(REL); t0 = time.time(); e.cmd('aaa'); ta_ = time.time() - t0
a0 = afl(e); new = sorted(SEEDS - set(a0)); t1 = time.time()
for i in range(0, len(new), 100): e.cmd(';'.join(f'af @ {x:#x}' for x in new[i:i + 100]))
tA = time.time() - t1; A = afl(e)
r['A_aaa_then_af'] = {'aaa_s': round(ta_, 1), 'af_s': round(tA, 1), **sc(A)}
# C: xref kinds for every start
kinds = {}
t2 = time.time()
for a in sorted(A):
    ks = set()
    for l in e.cmd(f'axt @ {a:#x}').splitlines():
        m = re.search(r'\[(CALL|CODE|DATA|STRING|NULL)[^\]]*\]', l)
        if m: ks.add(m.group(1))
        elif l.strip(): ks.add(l.split()[0][:12])
    kinds[a] = ks
r['C_axt_seconds'] = round(time.time() - t2, 1)
def k(ks): return 'call' if 'CALL' in ks else 'code-only' if 'CODE' in ks else 'data-only' if 'DATA' in ks else 'none' if not ks else 'other'
from collections import Counter
r['C_real'] = Counter(k(kinds[a]) for a in A if a in T)
r['C_fake'] = Counter(k(kinds[a]) for a in A if a not in T and ta <= a < ta + tl)
for rule, keep in {
    'drop code-only': lambda a: k(kinds[a]) != 'code-only' or a in SEEDS,
    'drop code-only and none': lambda a: k(kinds[a]) not in ('code-only', 'none') or a in SEEDS,
}.items():
    r['C_rule ' + rule] = sc({a: v for a, v in A.items() if keep(a)})
e.close()
# B
e = Engine(REL); t0 = time.time()
for i in range(0, len(SEEDS), 200): e.cmd(';'.join(f'f sym.dlptr_{x:x} @ {x:#x}' for x in sorted(SEEDS)[i:i + 200]))
e.cmd('aaa'); tB = time.time() - t0; B = afl(e)
r['B_flags_then_aaa'] = {'s': round(tB, 1), **sc(B)}
e.close()
# D: names file, flags only
names = []
with gzip.open(NAMES, 'rt') as g:
    for l in g:
        if l.startswith('#'): continue
        p = l.rstrip('\n').split('\t'); names.append((int(p[0], 16), int(p[1]), p[2], p[3]))
def eng(n):
    n = n.split('(')[0] if '(' in n and not n.startswith('(') else n
    n = n.split(' ')[-1]
    return re.sub(r'[^A-Za-z0-9_.]', '_', n.replace('::', '.')).rstrip('_') or 'x'
e = Engine(REL); t0 = time.time()
for i in range(0, len(names), 200): e.cmd(';'.join(f'f {eng(n[2])} {n[1]} @ {n[0]:#x}' for n in names[i:i + 200]))
tD = time.time() - t0
samples = [n for n in names if n[2].startswith(('tu_CreateDevice', 'tu_SetEvent', '_vk_device_set_lost', 'tu_physical_device_init'))][:4]
outs = {}
t1 = time.time()
for a, sz, n, sym in samples:
    c = e.cmd(f'af @ {a:#x};afn {eng(n)} @ {a:#x};pdg @ {a:#x}')
    outs[n[:40]] = c
    open(os.path.join(OUT, f'D-{a:x}.c'), 'w').write(c)
tDp = time.time() - t1
called_named = sum(len(re.findall(r'\b(fcn\.[0-9a-f]+)\(', c)) for c in outs.values())
called_real = sum(len(re.findall(r'\b(?!fcn\.)([A-Za-z_][A-Za-z0-9_.]{2,})\(', c)) for c in outs.values())
r['D_names_flags'] = {'flags_s': round(tD, 1), 'pdg4_s': round(tDp, 1), 'calls_shown_as_fcn': called_named, 'calls_with_names': called_real}
e.close()
json.dump(r, open(os.path.join(OUT, 'probe.json'), 'w'), indent=1, default=dict)
print(json.dumps(r, indent=1, default=dict))

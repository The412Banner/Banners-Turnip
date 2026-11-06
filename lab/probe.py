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

def seed(e, xs, pre='', post=''):
    if pre: e.cmd(pre)
    t1 = time.time()
    for i in range(0, len(xs), 100): e.cmd(';'.join(f'af @ {x:#x}' for x in xs[i:i + 100]))
    dt = time.time() - t1
    if post: e.cmd(post)
    return dt
# H: exactly the app (DriverLab prepare + finishList): af at every pointer with vars off, aaa, then
# drop starts with no reference or only jumps (kept: pointers and named functions).
e = Engine(REL); t0 = time.time()
e.cmd('e anal.vars=false')
for i in range(0, len(SEEDS), 100): e.cmd(';'.join(f'af @ {x:#x}' for x in sorted(SEEDS)[i:i + 100]))
e.cmd('e anal.vars=true'); t_af = time.time() - t0
t0 = time.time(); e.cmd('aaa'); t_aaa = time.time() - t0
H = afl(e); t0 = time.time(); keep = {}
for a, v in H.items():
    if a in SEEDS or not v[1].startswith('fcn.'): keep[a] = v; continue
    ks = {(re.search(r'\[(CALL|CODE|DATA|STRING|NULL)', l) or [None, 'other'])[1] for l in e.cmd(f'axt @ {a:#x}').splitlines() if l.strip()}
    if not ks or ('CALL' not in ks and 'CODE' in ks): continue
    keep[a] = v
t_axt = time.time() - t0
size_exact = sum(1 for a in keep if a in truth and keep[a][0] == truth[a])
hit = sum(1 for a in keep if a in truth)
r['H_app'] = {'af_s': round(t_af, 1), 'aaa_s': round(t_aaa, 1), 'axt_s': round(t_axt, 1), 'before_rule': sc(H), **sc(keep),
              'size_exact_pct': round(100 * size_exact / max(1, hit), 2)}
e.close()
json.dump(r, open(os.path.join(OUT, 'probe.json'), 'w'), indent=1, default=dict)
print(json.dumps(r, indent=1, default=dict))

#!/usr/bin/env python3
"""DriverLab source-code accuracy check on a stripped Turnip driver (lab only).

Runs the DriverLab inspector engine (rizin + rz-ghidra, the versions the app bundles) with the
app's commands on the released driver: aaa, afl, then pdg @ <addr> for every function (skipping
functions longer than 256 KiB, restarting the engine when the decompiler dies), and scores the
result against the symbol table of a non-stripped build of the same driver. File and line come
from a -g build of the same source, matched by function name.

usage: score.py RELEASED_SO SYMTAB_SO DEBUG_SO OUT_DIR
env:   RIZIN (rizin binary), GHIDRA_PLUGIN (core_ghidra.so), SLEIGH (dir with AARCH64.sla),
       SYMBOLIZER (llvm-symbolizer)
"""
import json, os, re, subprocess, sys, threading, time
from elftools.elf.elffile import ELFFile

REL, SYM, DBG, OUT = sys.argv[1:5]
RIZIN, PLUGIN, SLEIGH = os.environ['RIZIN'], os.environ['GHIDRA_PLUGIN'], os.environ['SLEIGH']
SYMBOLIZER = os.environ.get('SYMBOLIZER', 'llvm-symbolizer')
MAX_DECOMPILE = 256 * 1024          # Inspector.MAX_DECOMPILE
RSS_LIMIT_KB = 2560 * 1024          # the app stops the engine at 35 % of RAM (~2.5 GB on the Elite)
AFL = re.compile(r'^(0x[0-9a-fA-F]+)\s+(\d+)\s+(\d+)(?:\s+->\s+(\d+))?\s+(.+)$')   # Inspector.AFL_LINE
os.makedirs(OUT, exist_ok=True)

def text_section(p):
    f = ELFFile(open(p, 'rb')); s = f.get_section_by_name('.text')
    return s['sh_addr'], s.data()

def truth_functions(p):
    """STT_FUNC symbols with a size inside .text: address -> (size, [names])."""
    f = ELFFile(open(p, 'rb')); ta, td = text_section(p); out = {}
    for sec in f.iter_sections():
        if sec['sh_type'] not in ('SHT_SYMTAB',): continue
        for s in sec.iter_symbols():
            if s['st_info']['type'] != 'STT_FUNC' or not s['st_size'] or not s.name: continue
            a = s['st_value']
            if not (ta <= a < ta + len(td)): continue
            e = out.setdefault(a, [s['st_size'], []]); e[1].append(s.name)
    return out

class Engine:
    """rizin -q0 like DriverLab's RzSession: every answer ends with a zero byte."""
    def __init__(self, path):
        args = [RIZIN, '-q0', '-N', '-e', 'scr.color=0', '-e', 'scr.utf8=false', '-e', 'scr.interactive=false',
                '-e', 'bin.cache=true', '-l', PLUGIN, path]
        self.p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(os.path.join(OUT, 'rizin-stderr.log'), 'ab'))
        self.peak = 0; self.killed = False; self.alive = True
        threading.Thread(target=self.watch, daemon=True).start()
        self.read(); self.cmd('e ghidra.sleighhome=' + SLEIGH)
    def watch(self):
        while self.alive and self.p.poll() is None:
            try:
                kb = int(next(l for l in open(f'/proc/{self.p.pid}/status') if l.startswith('VmRSS:')).split()[1])
                self.peak = max(self.peak, kb)
                if kb > RSS_LIMIT_KB: self.killed = True; self.p.kill()
            except Exception: pass
            time.sleep(0.2)
    def read(self):
        buf = bytearray()
        while True:
            b = self.p.stdout.read(1)
            if not b: raise IOError('engine stopped' + (' (over the memory limit)' if self.killed else ''))
            if b == b'\0': return buf.decode('utf-8', 'replace')
            buf += b
    def cmd(self, c):
        self.p.stdin.write((c + '\n').encode()); self.p.stdin.flush(); return self.read()
    def close(self):
        self.alive = False
        try: self.p.kill()
        except Exception: pass

# 1. Is the symbol-table build the released code?
ra, rt = text_section(REL); sa, st = text_section(SYM)
same_code = (ra, rt) == (sa, st)
truth = truth_functions(SYM)
tsize = sum(v[0] for v in truth.values())

# 2. Engine on the released (stripped) driver, as Make source code does it
t0 = time.time(); eng = Engine(REL); eng.cmd('aaa'); t_aaa = time.time() - t0
found = []
for line in eng.cmd('afl').splitlines():
    m = AFL.match(line.strip())
    if m:
        a = int(m.group(1), 16); span = int(m.group(3)); real = int(m.group(4) or m.group(3))
        found.append((a, real, span, m.group(5)))
peak_aaa = eng.peak
fa = {f[0]: f for f in found}
in_text = [f for f in found if ra <= f[0] < ra + len(rt)]

# 3. Decompile every function (pdg), restarting on a crash like the app
dec = {}; restarts = 0; t1 = time.time(); peak = peak_aaa
both = sorted(set(truth) & set(f[0] for f in in_text))
pick = set(both[::max(1, len(both) // 30)])          # decompiled C kept for ~30 functions, next to their real names
os.makedirs(os.path.join(OUT, 'c'), exist_ok=True)
for i, (a, real, span, name) in enumerate(found):
    if real > MAX_DECOMPILE: dec[a] = 'too large'; continue
    try:
        c = eng.cmd(f'pdg @ {a:#x}')
        dec[a] = 'ok' if c.strip() and 'Ghidra Decompiler Error' not in c else 'error'
        if dec[a] == 'ok' and a in pick:
            open(os.path.join(OUT, 'c', f'{a:x}-{truth[a][1][0][:80]}.c'), 'w').write(f'// real name: {", ".join(truth[a][1])}, real size {truth[a][0]} B; engine: {name}, {real} B\n' + c)
    except IOError as e:
        peak = max(peak, eng.peak); restarts += 1; dec[a] = 'engine stopped'
        eng.close(); eng = Engine(REL); eng.cmd('aaa')
    peak = max(peak, eng.peak)
t_pdg = time.time() - t1; eng.close()

# 4. Score
T = set(truth); F = set(f[0] for f in in_text)
hit = T & F
size_exact = sum(1 for a in hit if fa[a][1] == truth[a][0])
size_close = sum(1 for a in hit if abs(fa[a][1] - truth[a][0]) <= 16)
named = [a for a in hit if not fa[a][3].startswith('fcn.')]
name_right = sum(1 for a in named if any(fa[a][3].split('.', 1)[-1] in (n, n.split('@')[0]) or fa[a][3].endswith(n) for n in truth[a][1]))
extra = sorted(F - T)
import bisect
_ts = sorted(truth)
def owner(a):
    i = bisect.bisect_right(_ts, a) - 1
    if i >= 0 and _ts[i] < a < _ts[i] + truth[_ts[i]][0]: return _ts[i]
    return None
extra_inside = sum(1 for a in extra if owner(a) is not None)
missed = sorted(T - F); missed_bytes = sum(truth[a][0] for a in missed)
deco = {}
for a in F: deco[dec.get(a, 'n/a')] = deco.get(dec.get(a, 'n/a'), 0) + 1

# 5. File:line a symbol file would add: names of the released functions looked up in the -g build
dbg_funcs = {}
for a, (sz, names) in truth_functions(DBG).items():
    for n in names: dbg_funcs.setdefault(n, a)
q = []
for a in sorted(T):
    n = next((n for n in truth[a][1] if n in dbg_funcs), None)
    if n: q.append((a, n, dbg_funcs[n]))
lines = subprocess.run([SYMBOLIZER, '--obj=' + DBG, '--functions=linkage', '--output-style=GNU', '--no-inlines'], input='\n'.join(f'{d:#x}' for _, _, d in q),
                       capture_output=True, text=True).stdout.splitlines()
with_line = 0; sample = []
for i, (a, n, d) in enumerate(q):
    loc = lines[2 * i + 1] if 2 * i + 1 < len(lines) else '??:0'
    if not loc.startswith('??') and not loc.endswith(':0'): with_line += 1
    if len(sample) < 40 and i % max(1, len(q) // 40) == 0: sample.append((f'{a:#x}', n, loc))

r = {
  'released_text_equals_symtab_build': same_code,
  'truth_functions': len(T), 'truth_bytes': tsize,
  'engine': {'aaa_seconds': round(t_aaa, 1), 'pdg_seconds': round(t_pdg, 1), 'peak_rss_mb': peak // 1024, 'restarts': restarts},
  'found_functions_in_text': len(F), 'found_all': len(found),
  'starts_found': len(hit), 'recall_pct': round(100 * len(hit) / len(T), 2), 'precision_pct': round(100 * len(hit) / max(1, len(F)), 2),
  'missed': len(missed), 'missed_bytes': missed_bytes, 'extra_starts': len(extra), 'extra_inside_a_real_function': extra_inside,
  'size_exact_pct': round(100 * size_exact / max(1, len(hit)), 2), 'size_within_16B_pct': round(100 * size_close / max(1, len(hit)), 2),
  'named_by_engine': len(named), 'named_right': name_right, 'named_pct_of_truth': round(100 * len(named) / len(T), 2),
  'decompile': deco,
  'symbol_file_would_name_pct': round(100 * len(q) / len(T), 2), 'symbol_file_file_line_pct': round(100 * with_line / len(T), 2),
}
json.dump(r, open(os.path.join(OUT, 'score.json'), 'w'), indent=1)
with open(os.path.join(OUT, 'missed.tsv'), 'w') as f:
    for a in missed: f.write(f'{a:#x}\t{truth[a][0]}\t{truth[a][1][0]}\n')
with open(os.path.join(OUT, 'extra.tsv'), 'w') as f:
    for a in extra: o = owner(a); f.write(f'{a:#x}\t{fa[a][1]}\t{fa[a][3]}\t' + (f'inside {o:#x} {truth[o][1][0]}' if o else 'outside') + '\n')
with open(os.path.join(OUT, 'file-line-sample.tsv'), 'w') as f:
    for s in sample: f.write('\t'.join(s) + '\n')
print(json.dumps(r, indent=1))

import re
import sys
from pathlib import Path

DEVICES = Path('src/freedreno/common/freedreno_devices.py')
KEYS = ('has_early_preamble', 'has_scalar_predicates')

content = DEVICES.read_text()
match = re.search(r'^a7xx_gen1 = GPUProps\(\n((?:[ \t]+.*\n|\n)*?)^[ \t]*\)', content, re.M)
if not match:
    sys.exit(f'{DEVICES}: a7xx_gen1 GPUProps block not found')

body = match.group(1)
for key in KEYS:
    entry = re.compile(rf'^([ \t]*{key}[ \t]*=[ \t]*)\w+', re.M)
    if entry.search(body):
        body = entry.sub(r'\g<1>False', body, count=1)
    else:
        body += f'        {key} = False,\n'

content = content[:match.start(1)] + body + content[match.end(1):]
compile(content, str(DEVICES), 'exec')
DEVICES.write_text(content)
print(f'{DEVICES}: a7xx_gen1 has_early_preamble=False, has_scalar_predicates=False')

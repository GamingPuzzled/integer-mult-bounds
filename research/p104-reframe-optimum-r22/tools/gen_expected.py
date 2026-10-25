"""Write EXPECTED.json + WORD.json.gz for the package from a candidate word (values recomputed independently in verify.py)."""
import sys, json, gzip, shutil
from collections import Counter
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib; V = importlib.import_module('verify')
P = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
rd = lambda p: json.loads(gzip.decompress(open(p, 'rb').read()))
base, word = rd(P + 'inputs/pr5580-WORD.json.gz'), rd(sys.argv[1])
open(P + 'WORD.json.gz', 'wb').write(gzip.compress(json.dumps(word, separators=(',', ':')).encode(), mtime=0))
old, new = V.scalar(base['program']), V.scalar(word['program'])
match = V.trace_equivalent(old, new)
charts = [[i, old[i], new[match[i]][-1] if new[match[i]][0] not in ('INIT', 'CLEAR') else new[match[i]][2]] for i in range(len(old)) if new[match[i]] != old[i]]
# relocated = operations whose relative order changed (minimal set: not on a longest increasing subsequence)
import bisect
seq = match; tails = []; idx = []; prev = [-1]*len(seq); tailidx = []
for i, x in enumerate(seq):
    k = bisect.bisect_left(tails, x)
    if k == len(tails): tails.append(x); tailidx.append(i)
    else: tails[k] = x; tailidx[k] = i
    prev[i] = tailidx[k-1] if k else -1
lis = set(); i = tailidx[-1]
while i >= 0: lis.add(i); i = prev[i]
reloc = [[i, old[i]] for i in range(len(old)) if i not in lis]
bill = lambda w: Counter(abs(len(w['frames'][e[2]]) - len(w['frames'][e[3]])) for e in w['program'] if e[0] == 'MOVE')
b0, b1 = bill(base), bill(word)
delta = {str(r): b1[r] - b0[r] for r in sorted(b0.keys() | b1.keys()) if b1[r] != b0[r]}
live = set(base['live']); main = live | {r+112 for r in live}
hel = lambda w: Counter(len(w['frames'][w['final'][r]]) - len(w['frames'][w['initial'][r]]) for r in range(735) if r not in main)
h0, h1 = hel(base), hel(word)
hd = {str(r): h1[r] - h0[r] for r in sorted(h0.keys() | h1.keys()) if h1[r] != h0[r]}
starts = {str(r): [a, b] for r, (a, b) in enumerate(zip(base['initial'], word['initial'])) if a != b}
pairs = lambda w: {(tuple(w['frames'][e[2]]), tuple(w['frames'][e[3]])) for e in w['program'] if e[0] == 'MOVE'} | {(tuple(w['frames'][w['initial'][r]]), tuple(w['frames'][w['final'][r]])) for r in range(735) if r not in main}
finals = {str(r): [a, b] for r, (a, b) in enumerate(zip(base['final'], word['final'])) if a != b}
E = dict(status=sys.argv[2], helper_starts=starts, helper_finals=finals, changed_charts=charts, relocated_operations=reloc, local_paid_delta=delta,
         helper_credit_delta=hd, new_native_maps=len(pairs(word) - pairs(base)))
json.dump(E, open(P + 'EXPECTED.json', 'w'), indent=1)
print(json.dumps({k: (v if k not in ('changed_charts', 'relocated_operations') else len(v)) for k, v in E.items()}))

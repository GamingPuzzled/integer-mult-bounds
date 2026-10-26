"""Exact commutation poset + frame bounds/domains for a P104 native word (R13 model ported).

Word grammar (PR5545 local.py): ops ADD r+=q*s @f, COPY r=q*s @f (owned r), SCALE r @f, INIT/CLEAR owned @f;
MOVE events are chart changes, synthesized from op frames.  Per register the op frames form a chain
(public: increasing in time, owned: decreasing).  Paid = sum of |dim jumps| of MOVEs; helper credit =
dim(final)-dim(initial) with FREE helper endpoints (#5561/#5567): initial = first op frame, final = last.
Main X initial ([q]) / final and Y initial / final (q^perp) are pinned.

Types per register: ADD target T, ADD/COPY source S, everything else X.  (T,T),(S,S) commute exactly
(a+=cb, d+=ef commute iff a!=f and d!=b).  Owned registers: every op typed X (order kept), and ops
touching owned registers are pinned to their current frame.  INIT/CLEAR also hit a virtual OWN register.
"""
import gzip, json, sys
from collections import defaultdict, Counter

NH = int(__import__('os').environ.get('P104_NPUB', '735'))
import os
FIXED = bool(os.environ.get('FIXED'))
OWNED_FREE = bool(os.environ.get('OWNED_FREE'))   # free owned charts; owned lifetimes as decreasing paths
FULLMASK = None


def load(path):
    return json.load(gzip.open(path)) if str(path).endswith('.gz') else json.load(open(path))


# ---------------- subspaces of F2^9 as 512-bit membership masks ----------------
class Sub:
    """Interned subspaces. id -> mask, dim, basis."""
    def __init__(s):
        s.mask, s.dim, s.basis, s.ix = [], [], [], {}

    def of_basis(s, b):
        sp = {0}
        bb = []
        for v in b:
            if v not in sp:
                sp |= {x ^ v for x in sp}; bb.append(v)
        m = 0
        for x in sp: m |= 1 << x
        if m not in s.ix:
            s.ix[m] = len(s.mask); s.mask.append(m); s.dim.append(len(bb)); s.basis.append(sorted(bb, reverse=True))
        return s.ix[m]

    def of_mask(s, m):
        if m in s.ix: return s.ix[m]
        xs = [x for x in range(512) if m >> x & 1]
        return s.of_basis(xs)

    def le(s, a, b): return s.mask[a] & ~s.mask[b] == 0

    def lt(s, a, b): return a != b and s.le(a, b)

    def comp(s, a, b): return s.le(a, b) or s.le(b, a)

    def join(s, *ids):
        b = []
        for i in ids: b += s.basis[i]
        return s.of_basis(b)

    def meet(s, *ids):
        m = (1 << 512) - 1
        for i in ids: m &= s.mask[i]
        return s.of_mask(m)


def roles(w):
    live = set(w['live'])
    def role(r):
        if r >= NH: return 'O'
        if r in live: return 'X'
        if r - 112 in live: return 'Y'
        return 'H'
    return role


def reg_types(e):
    op = e[0]
    if op == 'ADD':
        out = [(e[1], 'T'), (e[2], 'S')]
    elif op == 'COPY':
        out = [(e[1], 'X'), (e[2], 'S')]
    elif op in ('INIT', 'CLEAR'):
        return [(e[1], 'X'), ('OWN', 'X')]
    else:
        out = [(e[1], 'X')]
    return [(r, 'X' if r >= NH else t) for r, t in out]


def op_frame(e):
    return e[2] if e[0] in ('INIT', 'CLEAR') else e[-1]


def build(w):
    prog = w['program']
    opsidx = [k for k, e in enumerate(prog) if e[0] != 'MOVE']
    p = [prog[k] for k in opsidx]
    groups = defaultdict(list)            # reg -> [[type, [op ids]]]
    pos = defaultdict(dict)               # op -> reg -> group index
    for i, e in enumerate(p):
        for r, t in reg_types(e):
            g = groups[r]
            if FIXED: t = 'X'
            if g and g[-1][0] == t and t != 'X':
                g[-1][1].append(i)
            else:
                g.append([t, [i]])
            pos[i][r] = len(g) - 1
    return dict(p=p, opsidx=opsidx, groups=groups, pos=pos)


def setup(w):
    S = Sub()
    W = [S.of_basis(b) for b in w['frames']]           # word frame id -> Sub id
    P = build(w)
    p, groups, pos = P['p'], P['groups'], P['pos']
    role = roles(w)
    cur = [W[op_frame(e)] for e in p]
    pinned = {i for i, e in enumerate(p) if any(r != 'OWN' and r >= NH for r, _ in reg_types(e))}
    if __import__('os').environ.get('P104_UNPIN_OWNED') or OWNED_FREE:   # owned charts free (OWNED_FREE: chains modelled)
        pinned = set()
    # owned lifetimes: (r, k) = k-th INIT..CLEAR of owned register r
    nlt, own = defaultdict(int), defaultdict(dict)
    for i, e in enumerate(p):
        for r, _ in reg_types(e):
            if r == 'OWN' or r < NH: continue
            if e[0] == 'INIT': nlt[r] += 1
            own[i][r] = (r, nlt[r] - 1)
    P['own'] = own
    # pinned register ends (main registers only); helpers free
    start, final = {}, {}
    for r in range(NH):
        if role(r) in 'XY':
            start[r] = W[w['initial'][r]]; final[r] = W[w['final'][r]]
    P.update(S=S, W=W, cur=cur, pinned=pinned, start=start, final=final, role=role)
    return P


def pub_regs(P, i):
    return [r for r in P['pos'][i] if r != 'OWN' and r < NH]


def own_keys(P, i):
    return list(P['own'].get(i, {}).values())


def bounds(P, dom=None):
    """lows/ups valid for every linear extension; with dom, tightened by domain meets/joins."""
    S, p, groups, pos = P['S'], P['p'], P['groups'], P['pos']
    n = len(p); ZERO = S.of_basis([]); FULL = S.of_basis([1 << k for k in range(9)])
    lows = [ZERO] * n; ups = [FULL] * n
    eff_lo = [None] * n; eff_up = [None] * n          # what the op's frame certainly contains / is contained in
    gl = {}
    for i in range(n):
        parts = []
        for r in pub_regs(P, i):
            k = pos[i][r]
            if k == 0:
                if r in P['start']: parts.append(P['start'][r])
            else:
                key = (r, k - 1)
                if key not in gl: gl[key] = S.join(*[eff_lo[j] for j in groups[r][k - 1][1]])
                parts.append(gl[key])
        if i in P['pinned']: parts.append(P['cur'][i])
        lows[i] = S.join(*parts) if parts else ZERO
        if dom is not None and dom.get(i):
            eff_lo[i] = S.meet(*dom[i])
            eff_lo[i] = S.join(eff_lo[i], lows[i])
        else:
            eff_lo[i] = lows[i]
    gu = {}
    for i in range(n - 1, -1, -1):
        parts = []
        for r in pub_regs(P, i):
            k = pos[i][r]; G = groups[r]
            if k == len(G) - 1:
                if r in P['final']: parts.append(P['final'][r])
            else:
                key = (r, k + 1)
                if key not in gu: gu[key] = S.meet(*[eff_up[j] for j in G[k + 1][1]])
                parts.append(gu[key])
        if i in P['pinned']: parts.append(P['cur'][i])
        ups[i] = S.meet(*parts) if parts else FULL
        if dom is not None and dom.get(i):
            eff_up[i] = S.meet(S.join(*dom[i]), ups[i])
        else:
            eff_up[i] = ups[i]
    return lows, ups


def subspaces_between(S, lo, hi, maxgap):
    """all subspaces X with lo <= X <= hi if dim gap <= maxgap (else None)."""
    from itertools import combinations
    lb = list(S.basis[lo]); q = []
    j = lb[:]
    for v in S.basis[hi]:
        t = S.of_basis(j + [v])
        if S.dim[t] > len(j): j.append(v); q.append(v)
    if len(q) > maxgap: return None
    out = []
    for d in range(len(q) + 1):
        for piv in combinations(range(len(q)), d):
            free = [(a, b) for a, pv in enumerate(piv) for b in range(pv + 1, len(q)) if b not in piv]
            for m in range(1 << len(free)):
                rows = [1 << pv for pv in piv]
                for k, (a, b) in enumerate(free):
                    if m >> k & 1: rows[a] |= 1 << b
                vb = lb[:]
                for row in rows:
                    v = 0
                    for k, x in enumerate(q):
                        if row >> k & 1: v ^= x
                    vb.append(v)
                out.append(S.of_basis(vb))
    return out


def domains(P, w, mode='restricted', maxgap=3, verbose=True):
    S, p, groups, pos, cur = P['S'], P['p'], P['groups'], P['pos'], P['cur']
    n = len(p)
    lows, ups = bounds(P)
    bad = [i for i in range(n) if not (S.le(lows[i], cur[i]) and S.le(cur[i], ups[i]))]
    assert not bad, ('current frame outside bounds', bad[:5])
    regfr = defaultdict(set)
    for i in range(n):
        for r in pub_regs(P, i): regfr[r].add(cur[i])
    for r, x in P['start'].items(): regfr[r].add(x)
    for r, x in P['final'].items(): regfr[r].add(x)
    allfr = sorted(set(P['W']))
    dom = {}
    cache = {}
    win = os.environ.get('WIN')   # large-neighbourhood search: only ops lo..hi-1 are free
    win = tuple(map(int, win.split(':'))) if win else (0, n)
    winregs = os.environ.get('WINREGS')   # register neighbourhood: only ops touching these public registers are free
    winregs = set(map(int, winregs.split(','))) if winregs else None
    for i in range(n):
        if i in P['pinned'] or not win[0] <= i < win[1] or (winregs is not None and not winregs & set(pub_regs(P, i))):
            dom[i] = {cur[i]}; continue
        if mode == 'restricted':
            pool = set().union(*(regfr[r] for r in pub_regs(P, i)))
        elif mode == 'medium':
            pool = allfr
        else:
            key = (lows[i], ups[i])
            if key not in cache:
                cache[key] = subspaces_between(S, lows[i], ups[i], maxgap)
            pool = cache[key] if cache[key] is not None else set().union(*(regfr[r] for r in pub_regs(P, i))) | set(allfr)
        dom[i] = {x for x in pool if S.le(lows[i], x) and S.le(x, ups[i])} | {cur[i]}
    if OWNED_FREE:   # owned-only ops (INIT/CLEAR/SCALE/owned-to-owned) take the union of their lifetime's charts
        lt = defaultdict(set)
        for i in range(n):
            if pub_regs(P, i):
                for key in own_keys(P, i): lt[key] |= dom[i]
        for i in range(n):
            if not pub_regs(P, i) and own_keys(P, i) and i not in P['pinned']:
                dom[i] = set().union(*(lt[key] for key in own_keys(P, i))) | {cur[i]}
    # fixpoint: tightened bounds + comparability with forced frames of each register
    for rnd in range(20):
        lows, ups = bounds(P, dom)
        forced = defaultdict(set)
        for i in range(n):
            if len(dom[i]) == 1:
                for r in pub_regs(P, i): forced[r] |= dom[i]
        for r, x in P['start'].items(): forced[r].add(x)
        for r, x in P['final'].items(): forced[r].add(x)
        ch = 0
        for i in range(n):
            if len(dom[i]) == 1: continue
            nd = {x for x in dom[i] if S.le(lows[i], x) and S.le(x, ups[i])
                  and all(S.comp(x, y) for r in pub_regs(P, i) for y in forced[r])}
            assert cur[i] in nd, ('pruned current', i)
            if nd != dom[i]: dom[i] = nd; ch += 1
        if verbose: print('prune round', rnd, 'changed', ch, 'free', sum(len(d) > 1 for d in dom.values()),
                          'sum dom', sum(len(d) for d in dom.values()), flush=True)
        if not ch: break
    return dom, forced

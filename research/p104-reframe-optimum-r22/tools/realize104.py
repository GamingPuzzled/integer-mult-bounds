"""Realize a frame assignment on the P104 poset as a native word.
Order = stable topological sort (priority = original position) of conflict edges (consecutive groups,
via hubs) + per-public-register frame-order edges (dim levels).  MOVEs synthesized just before the op
needing them; helper initial/final = first/last op frame (free endpoints), main ends pinned.
keep_ends=True keeps every register's original initial/final (positive control)."""
import sys, os, heapq, json, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from poset104 import *


def realize(w, P, frames, keep_ends=False, move_order=None):
    S, p, groups = P['S'], P['p'], P['groups']
    n = len(p)
    succ = defaultdict(list); indeg = defaultdict(int); prio = {}
    for i in range(n): prio[i] = P['opsidx'][i]
    hub = [n]
    def newhub():
        h = hub[0]; hub[0] += 1; prio[h] = -1; return h
    def edge(a, b): succ[a].append(b); indeg[b] += 1
    for r, gl in groups.items():
        for (t0, A), (t1, B) in zip(gl, gl[1:]):
            if len(A) == 1 or len(B) == 1:
                for a in A:
                    for b in B: edge(a, b)
            else:
                h = newhub()
                for a in A: edge(a, h)
                for b in B: edge(h, b)
    lev = defaultdict(lambda: defaultdict(list))
    for i in range(n):
        for r in pub_regs(P, i): lev[r][S.dim[frames[i]]].append(i)
    for r, L in lev.items():
        ls = sorted(L)
        for l1, l2 in zip(ls, ls[1:]):
            h = newhub()
            for a in L[l1]: edge(a, h)
            for b in L[l2]: edge(h, b)
    nodes = list(range(hub[0]))
    heap = [(prio[v], v) for v in nodes if indeg[v] == 0]; heapq.heapify(heap); order = []
    while heap:
        _, v = heapq.heappop(heap)
        if v < n: order.append(v)
        for u in succ[v]:
            indeg[u] -= 1
            if indeg[u] == 0: heapq.heappush(heap, (prio[u], u))
    assert len(order) == n, 'cycle'
    # frames table
    w2 = json.loads(json.dumps(w)); ftab = {}
    for k, b in enumerate(w['frames']):
        ftab.setdefault(P['W'][k], k)
    def fid(x):
        if x not in ftab:
            w2['frames'].append(list(S.basis[x])); ftab[x] = len(w2['frames']) - 1
        return ftab[x]
    # endpoints
    first, last = {}, {}
    for i in order:
        for r in pub_regs(P, i):
            first.setdefault(r, frames[i]); last[r] = frames[i]
    init = list(w['initial']); fin = list(w['final'])
    if not keep_ends:
        for r in range(NH):
            if P['role'](r) == 'H' and r in first:
                init[r] = fid(first[r]); fin[r] = fid(last[r])
                if first[r] == last[r]:   # rank 0: the MIP path ends at an op-free node; keep the original final above
                    of = P['W'][w['final'][r]]
                    assert S.lt(last[r], of), ('rank-0 helper', r)
                    fin[r] = w['final'][r]
    cur = {r: init[r] for r in range(NH)}
    out = []
    def need(r, f):
        if cur.get(r) is not None and cur[r] != f:
            out.append(['MOVE', r, cur[r], f, r >= NH])
        cur[r] = f
    for i in order:
        e = list(p[i]); op = e[0]; f = fid(frames[i])
        if op == 'INIT':
            e[2] = f; cur[e[1]] = f
        elif op == 'CLEAR':
            need(e[1], f); e[2] = f; cur[e[1]] = None
        elif op in ('ADD', 'COPY'):
            for r in (move_order(e) if move_order else (e[1], e[2])): need(r, f)
            e[-1] = f
        else:
            need(e[1], f); e[-1] = f
        out.append(e)
    for r in range(NH): need(r, fin[r])
    w2['program'] = out; w2['initial'] = init; w2['final'] = fin
    return w2, order

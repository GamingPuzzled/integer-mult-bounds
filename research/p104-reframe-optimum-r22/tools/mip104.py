"""Exact subspace MIP over reorder (commutation poset) + re-frame on a P104 word.
Per public register: a unit path over its candidate frames between consecutive forced frames
(virtual SRC/SNK for free helper endpoints), op frame choices must lie on the path of each of
their registers, consecutive conflict groups are dims-monotone (hubs).  Cost = sum f(jump) over
path arcs - sum_helpers f(final-initial),  f(x) = x^(1-kappa)  (exact linearization of the root).
Usage: python mip104.py WORD MODE TL [maxgap]   MODE in restricted|medium|wide"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from poset104 import *
import numpy as np, scipy.sparse as sp

KAPPA = 0.0030818949686616
EPS = float(os.environ.get('EPS', '1e-6'))


def fw(x, k=KAPPA): return x ** (1 - k) if x > 0 else 0.0


def chain_cost(P, frames, k=KAPPA):
    """frames: op -> Sub id. Returns (cost, paid Counter, credit Counter) over public registers."""
    S = P['S']; regs = defaultdict(set)
    for i, x in enumerate(frames):
        for r in pub_regs(P, i): regs[r].add(x)
    for r, x in P['start'].items(): regs[r].add(x)
    for r, x in P['final'].items(): regs[r].add(x)
    paid, cred = Counter(), Counter()
    for r, fs in regs.items():
        ch = sorted(fs, key=lambda x: S.dim[x])
        for a, b in zip(ch, ch[1:]):
            assert S.lt(a, b), ('not a chain', r)
            paid[S.dim[b] - S.dim[a]] += 1
        if P['role'](r) == 'H':
            cred[S.dim[ch[-1]] - S.dim[ch[0]]] += 1
    cost = sum(n * fw(d, k) for d, n in paid.items()) - sum(n * fw(d, k) for d, n in cred.items())
    return cost, paid, cred


def closure(P):
    if 'anc' in P: return P['anc']
    p, groups, pos = P['p'], P['groups'], P['pos']
    anc = [0] * len(p); hub = {}
    for i in range(len(p)):
        a = 0
        for r, k in pos[i].items():
            if k == 0: continue
            key = (r, k - 1)
            if key not in hub:
                h = 0
                for j in groups[r][k - 1][1]: h |= anc[j] | (1 << j)
                hub[key] = h
            a |= hub[key]
        anc[i] = a
    P['anc'] = anc
    return anc


def build_mip(P, dom, forced, k=KAPPA, cuts=None):
    S, p, groups = P['S'], P['p'], P['groups']
    n = len(p)
    ops_of = defaultdict(list)
    for i in range(n):
        for r in pub_regs(P, i): ops_of[r].append(i)
    cost, integ, lo_, up_ = [], [], [], []
    def var(c=0.0, it=True, lo=0.0, up=1.0):
        cost.append(c); integ.append(it); lo_.append(lo); up_.append(up); return len(cost) - 1
    rows, cols, vals, rlb, rub = [], [], [], [], []
    def row(ent, a, b):
        kk = len(rlb)
        for j, c in ent: rows.append(kk); cols.append(j); vals.append(c)
        rlb.append(a); rub.append(b)
    free = [i for i in range(n) if len(dom[i]) > 1]
    V = {}
    for i in free:
        for x in sorted(dom[i]): V[i, x] = var(0.0 if x == P['cur'][i] else EPS)
        row([(V[i, x], 1) for x in dom[i]], 1, 1)
    SRC, SNK = -1, -2
    inflow = {}            # (r, x) -> list of arc vars into x
    arcsinfo = {}
    nz_reg = 0
    for r, ops in ops_of.items():
        cand = set().union(*(dom[i] for i in ops))
        ff = set(forced.get(r, set()))
        if r in P['start']: ff.add(P['start'][r])
        if r in P['final']: ff.add(P['final'][r])
        ffl = sorted(ff, key=lambda x: S.dim[x])
        for a, b in zip(ffl, ffl[1:]): assert S.lt(a, b), ('forced not chain', r)
        hel = P['role'](r) == 'H'
        ends = ([SRC] if r not in P['start'] else []) + ffl + ([SNK] if r not in P['final'] else [])
        gaps = list(zip(ends, ends[1:]))
        gc = defaultdict(list)
        for x in cand - ff:
            for g, (a, b) in enumerate(gaps):
                if (a == SRC or S.lt(a, x)) and (b == SNK or S.lt(x, b)):
                    gc[g].append(x); break
            else:
                raise AssertionError(('candidate in no gap', r, x))
        sdim, edim = defaultdict(list), defaultdict(list)
        for g, (a, b) in enumerate(gaps):
            nodes = [a] + sorted(gc[g], key=lambda x: S.dim[x]) + [b]
            out, inl = defaultdict(list), defaultdict(list)
            for u in nodes:
                for v in nodes:
                    if u == v or u == SNK or v == SRC: continue
                    if u == SRC and v == SNK: continue
                    if u != SRC and v != SNK and not S.lt(u, v): continue
                    c = 0.0 if (u == SRC or v == SNK) else fw(S.dim[v] - S.dim[u], k)
                    j = var(c); out[u].append(j); inl[v].append(j)
                    if v != SNK: inflow.setdefault((r, v), []).append(j)
                    if u == SRC: sdim[S.dim[v]].append(j)
                    if v == SNK: edim[S.dim[u]].append(j)
            for u in nodes:
                rhs = 1 if u == a else (-1 if u == b else 0)
                row([(j, 1) for j in out[u]] + [(j, -1) for j in inl[u]], rhs, rhs)
        if hel:
            ds, de = sorted(sdim), sorted(edim)
            Z = {}
            for d0 in ds:
                for d1 in de:
                    if d1 > d0: Z[d0, d1] = var(-fw(d1 - d0, k), False)
            for d0 in ds: row([(Z[d0, d1], 1) for d1 in de if (d0, d1) in Z] + [(j, -1) for j in sdim[d0]], 0, 0)
            for d1 in de: row([(Z[d0, d1], 1) for d0 in ds if (d0, d1) in Z] + [(j, -1) for j in edim[d1]], 0, 0)
        # op frame on path
        for i in ops:
            if len(dom[i]) == 1:
                continue
            for x in dom[i]:
                if x in ff: continue
                row([(V[i, x], 1)] + [(j, -1) for j in inflow[(r, x)]], -np.inf, 0)
    # monotone conflict groups
    def cum(i, l):
        if len(dom[i]) == 1:
            return [], 1.0 if S.dim[next(iter(dom[i]))] <= l else 0.0
        return [(V[i, x], 1) for x in dom[i] if S.dim[x] <= l], 0.0
    nh = 0
    for r, gl in groups.items():
        if r == 'OWN' or r >= NH: continue
        for (t0, A), (t1, B) in zip(gl, gl[1:]):
            da = [S.dim[x] for j in A for x in dom[j]]; db = [S.dim[x] for j in B for x in dom[j]]
            if max(da) <= min(db): continue
            nh += 1
            for l in range(min(da + db), max(da + db)):
                H = var(0.0, False)
                for j in A:
                    e, c0 = cum(j, l); row(e + [(H, -1)], -c0, np.inf)
                for j in B:
                    e, c0 = cum(j, l); row([(H, 1)] + [(x, -a) for x, a in e], c0, np.inf)
    # transitive conflict closure: ops of one commuting group on r that are ordered through other registers
    anc = closure(P)
    ncl = 0
    for r, gl in groups.items():
        if r == 'OWN' or r >= NH: continue
        for t, G in gl:
            if t == 'X' or len(G) < 2: continue
            for bi, b in enumerate(G):
                for a in G[:bi]:
                    if not (anc[b] >> a & 1): continue
                    if max(S.dim[x] for x in dom[a]) <= min(S.dim[x] for x in dom[b]): continue
                    ncl += 1
                    for l in range(min(S.dim[x] for x in dom[a] | dom[b]), max(S.dim[x] for x in dom[a] | dom[b])):
                        ea, ca = cum(a, l); eb, cb = cum(b, l)
                        # P(dim b <= l) <= P(dim a <= l)
                        row(ea + [(x, -c) for x, c in eb], cb - ca, np.inf)
    U = {}
    def uvar(c, d):   # u >= [dim c < dim d]
        if (c, d) in U: return U[c, d]
        u = var(0.0, True); U[c, d] = u
        ds = [S.dim[x] for x in dom[c] | dom[d]]
        for l in range(min(ds), max(ds)):
            ec, cc = cum(c, l); ed, cd = cum(d, l)
            # u - P(c<=l) + P(d<=l) >= 0
            row([(u, 1)] + [(x, -a) for x, a in ec] + ed, cc - cd, np.inf)
        return u
    for cut in (cuts or []):
        row([(uvar(c, d), 1) for c, d in cut], -np.inf, len(cut) - 1)
    A = sp.csc_matrix((vals, (rows, cols)), shape=(len(rlb), len(cost)))
    return dict(V=V, free=free, cost=np.array(cost), integ=integ, lo=np.array(lo_), up=np.array(up_),
                A=A, rlb=np.array(rlb, float), rub=np.array(rub, float), nh=nh, ncl=ncl)


def solve(M, tl, lp_only=False, threads=1):
    import highspy
    h = highspy.Highs(); h.setOptionValue('output_flag', bool(os.environ.get('HVERB')))
    h.setOptionValue('threads', threads); h.setOptionValue('time_limit', float(tl)); h.setOptionValue('mip_rel_gap', 1e-9)
    h.setOptionValue('mip_abs_gap', 1e-9)
    lp = highspy.HighsLp(); A = M['A']; nv = A.shape[1]; inf = highspy.kHighsInf
    lp.num_col_ = nv; lp.num_row_ = A.shape[0]; lp.col_cost_ = M['cost']; lp.col_lower_ = M['lo']; lp.col_upper_ = M['up']
    lp.row_lower_ = np.where(np.isinf(M['rlb']), -inf, M['rlb']); lp.row_upper_ = np.where(np.isinf(M['rub']), inf, M['rub'])
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = A.indptr; lp.a_matrix_.index_ = A.indices; lp.a_matrix_.value_ = A.data
    if lp_only:
        h.setOptionValue('solver', 'ipm'); h.setOptionValue('run_crossover', 'off')
    if not lp_only:
        lp.integrality_ = [highspy.HighsVarType.kInteger if t else highspy.HighsVarType.kContinuous for t in M['integ']]
    h.passModel(lp); h.run()
    return h


def extract(M, P, dom, x):
    fr = list(P['cur'])
    for i in M['free']:
        fr[i] = max(dom[i], key=lambda X: x[M['V'][i, X]])
    return fr


if __name__ == '__main__':
    word, mode, tl = sys.argv[1], sys.argv[2], float(sys.argv[3])
    maxgap = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    t = time.time(); w = load(word); P = setup(w)
    dom, forced = domains(P, w, mode, maxgap)
    c0, p0, c0r = chain_cost(P, P['cur'])
    print('current chain cost', c0, dict(sorted(p0.items())), dict(sorted(c0r.items())), flush=True)
    M = build_mip(P, dom, forced)
    print('vars', len(M['cost']), 'rows', len(M['rlb']), 'V', len(M['V']), 'hubs', M['nh'], 't %.1f' % (time.time() - t), flush=True)
    lp_only = bool(os.environ.get('LPONLY'))
    h = solve(M, tl, lp_only)
    info = h.getInfo(); x = np.array(h.getSolution().col_value)
    obj = info.objective_function_value
    print('status', h.modelStatusToString(h.getModelStatus()), 'obj', repr(obj),
          'bound', repr(getattr(info, 'mip_dual_bound', float('nan'))), 't %.1f' % (time.time() - t), flush=True)
    if not lp_only:
        fr = extract(M, P, dom, x)
        c1, p1, c1r = chain_cost(P, fr)
        print('solution chain cost', c1, 'gain', c0 - c1, dict(sorted(p1.items())), dict(sorted(c1r.items())))
        out = os.environ.get('OUT') or f'sol-{mode}.json'
        json.dump(dict(frames={i: P['S'].basis[fr[i]] for i in range(len(fr)) if fr[i] != P['cur'][i]}, cost=c1, base=c0), open(out, 'w'))

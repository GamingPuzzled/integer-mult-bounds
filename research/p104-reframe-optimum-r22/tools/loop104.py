"""Lazy loop: exact MIP -> realize -> cycle no-good cuts -> exact price.  usage: loop104.py WORD MODE TL [maxgap] [OUTWORD]"""
import sys, os, time, json, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.environ.get('TK_INFRA', os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../p104-designer-toolkit/infra')))  # PR5568 legal.py/price_exact.py
from mip104 import *
from realize104 import realize
import legal, price_exact as X

def find_cycle(P, fr):
    S, p, groups = P['S'], P['p'], P['groups']; n = len(p)
    E = defaultdict(list)
    for r, gl in groups.items():
        for (t0, A), (t1, B) in zip(gl, gl[1:]):
            for a in A:
                for b in B: E[a].append(b)
    lev = defaultdict(lambda: defaultdict(list))
    for i in range(n):
        for r in pub_regs(P, i): lev[r][S.dim[fr[i]]].append(i)
    for r, L in lev.items():
        ls = sorted(L)
        for l1, l2 in zip(ls, ls[1:]):
            for a in L[l1]:
                for b in L[l2]: E[a].append(b)
    color = [0] * n; par = {}
    for s in range(n):
        if color[s]: continue
        st = [(s, iter(E[s]))]; color[s] = 1
        while st:
            v, it = st[-1]
            for u in it:
                if color[u] == 0: color[u] = 1; par[u] = v; st.append((u, iter(E[u]))); break
                if color[u] == 1:
                    cyc = [v]; x = v
                    while x != u: x = par[x]; cyc.append(x)
                    return cyc
            else: color[v] = 2; st.pop()
    return None

def all_cycles(P, fr, cap=40):
    """Several cycles: after each, drop its frame edges that run against base order and search again."""
    S, p, groups = P['S'], P['p'], P['groups']; n = len(p)
    conf = conf_succ(P)
    E = defaultdict(set)
    for a, bs in conf.items(): E[a] |= bs
    lev = defaultdict(lambda: defaultdict(list))
    for i in range(n):
        for r in pub_regs(P, i): lev[r][S.dim[fr[i]]].append(i)
    for r, L in lev.items():
        ls = sorted(L)
        for l1, l2 in zip(ls, ls[1:]):
            for a in L[l1]:
                for b in L[l2]: E[a].add(b)
    cuts = []
    for _ in range(cap):
        color = [0] * n; par = {}; found = None
        for s in range(n):
            if color[s] or found: continue
            st = [(s, iter(E[s]))]; color[s] = 1
            while st and not found:
                v, it = st[-1]
                for u in it:
                    if color[u] == 0: color[u] = 1; par[u] = v; st.append((u, iter(E[u]))); break
                    if color[u] == 1:
                        cyc = [v]; x = v
                        while x != u: x = par[x]; cyc.append(x)
                        found = cyc[::-1]; break
                else: color[v] = 2; st.pop()
        if not found: break
        cut = [(a, b) for a, b in zip(found, found[1:] + found[:1]) if b not in conf[a]]
        cuts.append(cut)
        back = [(a, b) for a, b in cut if a > b]
        for a, b in (back or cut[:1]): E[a].discard(b)
    return cuts

def conf_succ(P):
    if 'conf' in P: return P['conf']
    E = defaultdict(set)
    for r, gl in P['groups'].items():
        for (t0, A), (t1, B) in zip(gl, gl[1:]):
            for a in A: E[a].update(B)
    P['conf'] = E; return E

def mo(e):
    return (e[2], e[1]) if (e[0] == 'ADD' and e[1] == 451 and e[2] == 228 and e[3] == '1') else (e[1], e[2])

if __name__ == '__main__':
    word, mode, tl = sys.argv[1], sys.argv[2], float(sys.argv[3])
    maxgap = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    outw = sys.argv[5] if len(sys.argv) > 5 else None
    t = time.time(); w = load(word); P = setup(w)
    dom, forced = domains(P, w, mode, maxgap, verbose=False)
    print('free ops', sum(len(d) > 1 for d in dom.values()), 'sum dom', sum(len(d) for d in dom.values()), flush=True)
    c0, p0, _ = chain_cost(P, P['cur']); cuts = []
    rep0 = legal.check(w); T0, P0 = X.invoice(rep0); k0 = X.kappa_dec(T0, P0)
    for it in range(60):
        M = build_mip(P, dom, forced, cuts=cuts)
        if it == 0: print('vars', len(M['cost']), 'rows', len(M['rlb']), 'V', len(M['V']), 'hubs', M['nh'], 'closure pairs', M['ncl'], 't %.1f' % (time.time() - t), flush=True)
        h = solve(M, tl); info = h.getInfo(); x = np.array(h.getSolution().col_value)
        st = h.modelStatusToString(h.getModelStatus())
        fr = extract(M, P, dom, x); c1, p1, cr1 = chain_cost(P, fr)
        cyc = find_cycle(P, fr)
        extra = all_cycles(P, fr) if cyc is not None else []
        print('it', it, st, 'obj %.9f bound %.9f' % (info.objective_function_value, info.mip_dual_bound), 'cur %.9f gain %.9f' % (c0, c0 - c1),
              'cycle', None if cyc is None else len(cyc), 't %.1f' % (time.time() - t), flush=True)
        if cyc is None: break
        cyc = cyc[::-1]   # path order v0 -> v1 -> ... (find_cycle returns reversed)
        conf = conf_succ(P)
        cut = []
        for a, b in zip(cyc, cyc[1:] + cyc[:1]):
            if b in conf[a]: continue
            cut.append((a, b))
        assert cut, 'cycle without frame edges'
        print('   cut frame edges', [(P['opsidx'][a], P['opsidx'][b]) for a, b in cut], flush=True)
        cuts.append(cut)
        for c in extra:
            if c not in cuts: cuts.append(c); print('   extra cut', [(P['opsidx'][a], P['opsidx'][b]) for a, b in c], flush=True)
    changed = [i for i in range(len(fr)) if fr[i] != P['cur'][i]]
    print('changed ops', len(changed))
    for i in changed[:40]: print('  op', i, 'ev', P['opsidx'][i], P['p'][i], 'dim', P['S'].dim[P['cur'][i]], '->', P['S'].dim[fr[i]])
    if c0 - c1 > 1e-12:
        w2, order = realize(w, P, fr, move_order=mo)
        rep = legal.check(w2); T, Pp = X.invoice(rep); k = X.kappa_dec(T, Pp)
        print('REALIZED legal', rep['ok'], rep['violations'][:3], 'paid', rep['paid'], 'helpers', rep['helpers'], 'events', len(w2['program']))
        print('EXACT kappa', str(k)[:22], 'base', str(k0)[:22], 'gain %.6e' % float(k - k0), 'side', X.side(T, Pp)['ok'])
        if outw: open(outw, 'wb').write(gzip.compress(json.dumps(w2, separators=(',', ':')).encode(), mtime=0))

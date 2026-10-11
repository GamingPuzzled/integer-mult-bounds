#!/usr/bin/env python3
"""Independent re-scoring of a PR249-format p=10 word (bit side only).

Shares no code with the PR's price.py/moment.py. Every MOVE and COPY rank is
recomputed from frame dimensions (dim = number of basis rows); the record's own
rank fields are only compared, never used. The five-stage profile formula is the
one stated in the PR's price.py docstring and PROOF; it is a framework input.
Exact enclosures: ln via 2*atanh((x-1)/(x+1)) after binary reduction, with a
geometric tail; exp via Taylor with a geometric tail. Decimal only proposes.
usage: indep_score.py WORD_DIR [claimed_bit_coarse]
"""
import json, sys
from collections import Counter
from decimal import Decimal, getcontext
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path


def ln_unit(x):  # 1 <= x <= 2
    z = (x - 1) / (x + 1); z2 = z * z; t = z; s = Q(0)
    for j in range(70):
        s += t / (2 * j + 1); t *= z2
    return 2 * s, 2 * (s + t / (141 * (1 - z2)))


@lru_cache(None)
def ln(x):
    k = 0
    while x > 2:
        x /= 2; k += 1
    lo, hi = ln_unit(x); l2, h2 = ln_unit(Q(2))
    return lo + k * l2, hi + k * h2


def exp(x, upper):
    assert 0 <= x < Q(1, 10)
    s = t = Q(1)
    for j in range(1, 30):
        t = t * x / j; s += t
    return s + (t * x / 30 / (1 - x / 31) if upper else 0)


def moment(H, m, W, a, fallback):
    lo = hi = Q(0)
    items = list(H.items()) + [(1, fallback)]
    for r, p in items:
        l, u = ln(Q(m, r))
        lo += p * exp(a * l, False); hi += p * exp(a * u, True)
    return lo, hi


def score(d, claimed=None):
    d = Path(d); h = 20
    st = json.loads((d / '249-states.json').read_text())
    frames = json.loads((d / 'frames.json').read_text())['frames']
    dim = {int(k): len(f['B']) for k, f in frames.items()}
    raw = (d / '249-records.bin').read_bytes(); assert len(raw) % 24 == 0
    import struct
    recs = struct.iter_unpack('<6i', raw)
    v, n = st['v'], st['n']
    local = Counter(); mismatch = 0
    for o, a, b, c, f, z in recs:
        if o == 0:
            r = dim[c] - dim[b]; assert r >= 0
            mismatch += r != f
            if r: local[r] += 1
        elif o == 2:
            r = dim[c]; mismatch += r != z; local[r] += 1
    assert mismatch == 0, ('record rank fields disagree with frames', mismatch)
    resid = sum(dim[st['final'][str(r)]] - dim[st['initial'][str(r)]] for r in range(2 * v, n))
    m = 5 * h; W = 4 * v + Q(resid, h)
    H = Counter({r: 5 * c for r, c in local.items()})
    for r in (2 * h - 2, h - 1, 2 * h + 2, 4): H[r] += 2 * v
    mass = sum(r * c for r, c in H.items())
    deficit = m * W - mass
    assert deficit == 4 * v - 5 * h * (h - 2), deficit
    P = {r: Q(r * c) / (m * W) for r, c in H.items()}
    fallback = Q(32 * m * sum(H.values())) / (10**16 * W)
    # Decimal proposal of the root, then exact grid certification.
    getcontext().prec = 60
    terms = [(Decimal(p.numerator) / Decimal(p.denominator), (Decimal(m) / r).ln()) for r, p in P.items()]
    fb = Decimal(fallback.numerator) / Decimal(fallback.denominator); lm = Decimal(m).ln()
    lo_, hi_ = Decimal(0), Decimal('0.01')
    for _ in range(200):
        mid = (lo_ + hi_) / 2
        val = sum(p * (mid * l).exp() for p, l in terms) + fb * (mid * lm).exp()
        lo_, hi_ = (mid, hi_) if val < 1 else (lo_, mid)
    grid = 10**18
    c = Q(int(lo_ * grid), grid)
    for _ in range(3):  # walk to the exact boundary if the proposal is off by a tick
        if moment(P, m, 1, c, fallback)[1] >= 1: c -= Q(1, grid); continue
        if moment(P, m, 1, c + Q(1, grid), fallback)[1] < 1: c += Q(1, grid); continue
        break
    up = moment(P, m, 1, c, fallback)[1]; nxt = moment(P, m, 1, c + Q(1, grid), fallback)[0]
    assert up < 1 < nxt, (float(up), float(nxt))
    out = dict(word=str(d), v=v, n=n, resid=resid, W=str(W), local=dict(sorted(local.items())),
               rank_fields_match_frames=True, deficit=str(deficit), bit_coarse=str(c),
               certified=dict(moment_upper_at_c=float(up - 1), moment_lower_at_next=float(nxt - 1)))
    if claimed is not None:
        out['claimed_bit_coarse'] = str(claimed); out['agrees'] = Q(claimed) == c
    return out


if __name__ == '__main__':
    print(json.dumps(score(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), indent=1))

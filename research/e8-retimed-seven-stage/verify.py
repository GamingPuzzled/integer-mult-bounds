#!/usr/bin/env python3
"""Compose PR #365's retimed E8 complex unit with PR #363/#373's seven-stage bridged word.

Steps (all vendored inputs are hash-checked first):
 1. PR #365's own verifier: the retimed certificate has the same rational scalar
    operator as Sussman's E8 unit, legal frame paths, and four rejected damaged inputs.
 2. PR #363's seven-stage complex guard on the ORIGINAL certificate must reproduce
    PR #363's own pins (regression).
 3. The same guard on the RETIMED certificate, with every regression count pinned in
    pins-e8-b3-retimed.json. A sign-flipped retimed certificate must be rejected.
 4. b3 from the guard's own seven-stage histogram: both vendored rational engines,
    the 10^-16 fallback, adjacent 10^-18 grid point rejected; plus an independent
    exact enclosure written here.
 5. kappa with PR #373's outer assembly and PR #373's seven-stage bit coarse saving
    c = 968197503705007/10^18 (an input, certified by PR #373's verify.sh); all 47
    strict constraints, adjacent kappa tick and complex leaf cap rejected.
usage: verify.py NEW_OUTPUT_DIR
"""
import copy, gzip, hashlib, importlib.util, json, os, subprocess, sys
from fractions import Fraction as Q
from pathlib import Path

if not __debug__:
    raise SystemExit('Assertions must remain enabled')
HERE = Path(__file__).resolve().parent
V = HERE / 'vendor'
CX = V / 'pr363-complex'
CERT_DIR = CX / 'inputs/e8/tools/certificate'
EXPECTED = json.loads((HERE / 'EXPECTED.json').read_text())
GRID = Q(1, 10**18)


def sha(b): return hashlib.sha256(b).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def check_manifest():
    manifest = json.loads((HERE / 'MANIFEST.json').read_text())
    files = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files -= {'MANIFEST.json'}
    assert files == set(manifest), ('manifest membership', sorted(files ^ set(manifest))[:10])
    for name, digest in manifest.items():
        assert sha((HERE / name).read_bytes()) == digest, ('hash mismatch', name)
    return sha((HERE / 'MANIFEST.json').read_bytes())


def guard(out, tag, cert_bytes, pins_path):
    """Run PR #363's unchanged guard with the given certificate bound through source pins."""
    work = out / tag; work.mkdir()
    cert = work / 'gcert.json.gz'; cert.write_bytes(cert_bytes)
    sp = json.loads((CX / 'inputs/complex/source-pins.json').read_text())
    rel = os.path.relpath(cert, CX)
    sp['certificate'].update(path=rel, compressed_sha256=sha(cert_bytes),
                             uncompressed_sha256=sha(gzip.decompress(cert_bytes)))
    (work / 'source-pins.json').write_text(json.dumps(sp))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', CX_PINS=str(pins_path),
               CX_SOURCE_PINS=str(work / 'source-pins.json'), CX_RECORD=str(work / 'record.json'))
    r = subprocess.run([sys.executable, '-B', str(CX / 'portable_complex.py')], capture_output=True, text=True, env=env)
    (work / 'stderr.txt').write_text(r.stderr)
    if r.returncode:
        return None, r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'rc=%d' % r.returncode
    res = json.loads(r.stdout)
    assert res['status'] == 'PASS_FRESH_COMPLEX_LABEL_SCALAR_SPLICE_PRECISION'
    assert not (work / 'record.json').exists(), 'unpinned regression value recorded'
    return res, None


def coarse(H, m, W):
    moment = load('moment', V / 'pr373-pricing/moment.py'); other = load('base_two_moment', V / 'pr373-pricing/base_two_moment.py')
    root = moment.certify(dict(H), m, W, True); b = Q(int(Q(root['lower']) * 10**18), 10**18)
    cm = moment.moment(H, m, W, b, True); nm = moment.moment(H, m, W, b + GRID, True); assert cm[1] < 1 < nm[0]
    fb = 32 * m * m * sum(H.values())
    _, up = other.moment(m, W, list(H.items()), b); _, bad = other.moment(m, W, [(1, fb)], b)
    lo, _ = other.moment(m, W, list(H.items()), b + GRID); bl, _ = other.moment(m, W, [(1, fb)], b + GRID)
    assert up + Q(1, 10**16) * bad < 1 < lo + Q(1, 10**16) * bl
    return b


def independent_moment(H, m, W, a):
    """Own enclosure: ln via 2 atanh after binary reduction, exp via Taylor, geometric tails."""
    def ln_unit(x):
        z = (x - 1) / (x + 1); z2 = z * z; t = z; s = Q(0)
        for j in range(60): s += t / (2 * j + 1); t *= z2
        return 2 * s, 2 * (s + t / (121 * (1 - z2)))
    def ln(x):
        k = 0
        while x > 2: x /= 2; k += 1
        lo, hi = ln_unit(x); l2, h2 = ln_unit(Q(2)); return lo + k * l2, hi + k * h2
    def ex(x, up):
        s = t = Q(1)
        for j in range(1, 26): t = t * x / j; s += t
        return s + (t * x / 26 / (1 - x / 27) if up else 0)
    fb = Q(32 * m * sum(H.values()), 10**16 * W)
    lo = hi = Q(0)
    for r, n in list(H.items()) + [(1, None)]:
        p = fb if n is None else Q(r * n, m * W)
        l, u = ln(Q(m, r)); lo += p * ex(a * l, False); hi += p * ex(a * u, True)
    return lo, hi


def kappa(c, b):
    outer = load('outer', V / 'pr373-pricing/outer.py')
    eta, beta = Q(1, 10**12), Q(1, 10**9); cap = (1 - beta) * b
    sv = min(c, Q(((cap - GRID) * 10**18).__floor__(), 10**18)); binding = 'bit' if sv == c else 'complex'
    chain = [Q(384599, 10**10)]
    for _ in range(3):
        a = (1 - sv) * sv + sv * chain[-1]; assert chain[-1] < a < sv < 1 - a; chain.append(a)
    bit = chain[-1]
    bridge = dict(proof='PROOF.md', representation='Exact powers with source-bound finite overcharges',
                  semantic=dict(G=dict(base=2, exponent=30000), E=dict(base=2, exponent=100000), B_upper=dict(base=2, exponent=100001),
                                C0=dict(base=2, exponent=210000), C1=1, strict_literal_gap=1, induction_gap_lower=1),
                  rows=dict(coefficient=20161, degree=10**6, suffix_slope=4 * 10**6, degree_gap=Q(10**6) - Q(51 * 20161, 25)))
    q = bit * (1 - 2 * eta); mn = (1 - eta) * q / (1 + q); t = mn * 10**18; k = Q((t.numerator - 1) // t.denominator, 10**18)
    asm = outer.assembly(bit, b, bridge, k, eta=eta, beta=beta)
    assert len(asm['strict_constraints']) == 47 and min(asm['strict_constraints'].values()) > 0
    try:
        outer.assembly(bit, b, bridge, k + GRID, eta=eta, beta=beta); raise SystemExit('ADJACENT KAPPA ADMITTED')
    except AssertionError: pass
    if binding == 'complex':
        try: outer.assembly(cap, b, bridge, k, eta=eta, beta=beta)
        except AssertionError as e: assert 'leaf_saving_above_bit' in str(e)
        else: raise SystemExit('complex leaf cap admitted')
    return k, binding


def main():
    out = Path(sys.argv[1]).resolve()
    assert not out.exists() and not out.is_relative_to(HERE), 'output must be new and outside the package'
    out.mkdir(parents=True)
    manifest = check_manifest(); print('PASS manifest', manifest, flush=True)

    r = subprocess.run([sys.executable, '-B', str(V / 'pr365/verify.py')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    v365 = json.loads(r.stdout); assert v365['status'] == 'PASS'
    (out / 'pr365-verification.json').write_text(r.stdout)
    print('PASS PR #365 verifier: retimed E8 unit, same scalar operator, frame paths, damaged inputs rejected', flush=True)

    original = (CERT_DIR / 'gcert1-e8-r783.json.gz').read_bytes()
    retimed = (V / 'pr365/data/retimed.json.gz').read_bytes()
    assert sha(gzip.decompress(original)) == EXPECTED['original_certificate_sha256']
    assert sha(gzip.decompress(retimed)) == EXPECTED['retimed_certificate_sha256']
    assert json.loads(gzip.decompress((V / 'pr365/data/original.json.gz').read_bytes())) == json.loads(gzip.decompress(original)), \
        'PR #365 did not start from the PR #363 certificate'

    g0, err = guard(out, 'guard-original', original, CX / 'pins-e8-b3.json'); assert g0, err
    print('PASS seven-stage guard on the original certificate reproduces PR #363 pins', flush=True)
    g1, err = guard(out, 'guard-retimed', retimed, HERE / 'pins-e8-b3-retimed.json'); assert g1, err
    print('PASS seven-stage guard on the retimed certificate (all regression counts pinned)', flush=True)

    cert = json.loads(gzip.decompress(retimed)); bad = copy.deepcopy(cert)
    for gg in bad['A']:
        if gg[0] in ('out', 'in') and gg[3]:
            t, a, b = gg[3][0]; gg[3][0] = [t, -a, b]; break
    damaged = gzip.compress(json.dumps(bad, separators=(',', ':')).encode(), mtime=0)
    g2, err = guard(out, 'guard-damaged', damaged, HERE / 'pins-e8-b3-retimed.json')
    assert g2 is None, 'sign-flipped retimed certificate accepted'
    print('PASS sign-flipped retimed certificate rejected:', err[:120], flush=True)

    m, W = g1['precision_guard']['m'], g1['precision_guard']['live_per_vertex']
    assert (m, W) == (63, 1503) and g1['ledger']['deficit'] == 216
    H0 = {int(k): n for k, n in g0['five_stage_histogram'].items()}
    H1 = {int(k): n for k, n in g1['five_stage_histogram'].items()}
    b0, b1 = coarse(H0, m, W), coarse(H1, m, W)
    assert b0 == Q(EXPECTED['b3_original']) and b1 == Q(EXPECTED['b3_retimed']), (b0, b1)
    lo, hi = independent_moment(H1, m, W, b1); lo2, hi2 = independent_moment(H1, m, W, b1 + GRID)
    assert hi < 1 < lo2, 'independent enclosure disagrees'
    print('PASS b3: original %s (= PR #363), retimed %s (%+.5f%%); independent enclosure agrees'
          % (b0, b1, 100 * float(b1 / b0 - 1)), flush=True)

    c = Q(EXPECTED['pr373_bit_coarse'])
    k0, bind0 = kappa(c, b0); k1, bind1 = kappa(c, b1)
    assert k0 == Q(EXPECTED['pr373_kappa']) and bind0 == 'complex', k0
    assert k1 == Q(EXPECTED['kappa']) and bind1 == 'complex', k1
    result = dict(status='PASS_CONDITIONAL_COMPOSITION', manifest_sha256=manifest, b3_original=str(b0), b3_retimed=str(b1),
                  bit_coarse_input=str(c), pr373_kappa=str(k0), kappa=str(k1), kappa_float=float(k1), binding=bind1,
                  improvement_over_pr373=float(k1 / k0 - 1), seven_stage_histogram=g1['five_stage_histogram'],
                  ledger=g1['ledger'])
    (out / 'RESULT.json').write_text(json.dumps(result, indent=2))
    print('PASS conditional kappa = %s = %.15e (complex-bound; PR #373 %s, %+.5f%%)'
          % (k1, float(k1), k0, 100 * float(k1 / k0 - 1)), flush=True)


if __name__ == '__main__':
    main()

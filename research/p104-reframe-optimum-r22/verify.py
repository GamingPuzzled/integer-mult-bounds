"""Check the R22 reorder+reframe word on PR5580's P104 word: exact commutation, complete caller, kappa.

Joel Pulikkan (GamingPuzzled) with Claude Opus 5.5 (Anthropic) via Claude Code. Apache-2.0.
Retained sources and their contributors are listed in SOURCES.json and README.md.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction as Q
from hashlib import sha1, sha256
from pathlib import Path
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from common import closure, load, need, read
from construct import construct

EXPECTED = json.loads((HERE/'EXPECTED.json').read_text())
PARENT_INTERVAL = [Q('0.00308189496866'), Q('0.00308189496867')]   # PR5580 RESULT.json raw crossing
DENSE = REPO/'research/p104-contact-independent-audit/capsule/outputs/p104-native-contact-audit-20261025'


def kinds(e):
    """(register, type) per touched register; T/T and S/S commute exactly, everything else conflicts.
    Owned registers keep every operation exclusive; INIT/CLEAR also share the owned-lifetime token."""
    op = e[0]
    if op == 'ADD':
        out = [(e[1], 'T'), (e[2], 'S')]
    elif op == 'COPY':
        out = [(e[1], 'X'), (e[2], 'S')]
    elif op in ('INIT', 'CLEAR'):
        return [(e[1], 'X'), ('owned-lifetime', 'X')]
    else:
        out = [(e[1], 'X')]
    return [(r, 'X' if r >= 735 else t) for r, t in out]


def scalar(program):
    return [e for e in program if e[0] != 'MOVE']


def strip(e):
    return tuple(e[:2]) if e[0] in ('INIT', 'CLEAR') else tuple(e[:-1])


def trace_equivalent(old, new):
    """Match equal operations in order; the new order must keep every dependent pair (Cartier-Foata).
    Returns the matching (old index -> new index)."""
    need(Counter(map(strip, old)) == Counter(map(strip, new)), 'Same multiset of scalar and owned operations')
    slots = defaultdict(list)
    for j, e in enumerate(new):
        slots[strip(e)].append(j)
    for v in slots.values():
        v.reverse()
    match = [slots[strip(e)].pop() for e in old]
    groups = defaultdict(list)
    for i, e in enumerate(old):
        for r, t in kinds(e):
            g = groups[r]
            if g and g[-1][0] == t and t != 'X':
                g[-1][1].append(i)
            else:
                g.append([t, [i]])
    for r, g in groups.items():
        for (_, a), (_, b) in zip(g, g[1:]):
            need(max(match[i] for i in a) < min(match[i] for i in b), 'Dependent operations keep their order')
    return match


def inventory(base, word):
    for key in base:
        if key not in ('program', 'initial', 'final', 'frames'):
            need(word[key] == base[key], 'Unchanged word field: ' + key)
    need(word['frames'][:len(base['frames'])] == base['frames'], 'Existing charts unchanged')
    starts = {str(r): [a, b] for r, (a, b) in enumerate(zip(base['initial'], word['initial'])) if a != b}
    need(starts == EXPECTED['helper_starts'], 'Exact changed helper starts')
    finals = {str(r): [a, b] for r, (a, b) in enumerate(zip(base['final'], word['final'])) if a != b}
    need(finals == EXPECTED['helper_finals'], 'Exact changed helper finals')
    live = set(base['live']); main = live | {r+112 for r in live}
    need(all(int(r) not in main for r in list(starts) + list(finals)), 'Only free helper endpoints change')
    old, new = scalar(base['program']), scalar(word['program'])
    match = trace_equivalent(old, new)
    moved = sum(1 for i in range(len(old) - 1) if match[i] > match[i+1])
    charts = [[i, old[i], new[match[i]][-1] if new[match[i]][0] not in ('INIT', 'CLEAR') else new[match[i]][2]]
              for i in range(len(old)) if new[match[i]] != old[i]]
    need(charts == EXPECTED['changed_charts'], 'Exact changed scalar charts')
    def bill(w):
        return Counter(abs(len(w['frames'][e[2]]) - len(w['frames'][e[3]])) for e in w['program'] if e[0] == 'MOVE')
    before, after = bill(base), bill(word)
    delta = {str(r): after[r] - before[r] for r in sorted(before.keys() | after.keys()) if after[r] != before[r]}
    need(delta == EXPECTED['local_paid_delta'], 'Exact changed paid profile')
    return {'source_events': len(base['program']), 'events': len(word['program']),
            'ordered_scalar_events': len(old), 'order_descents': moved,
            'relocated_operations': EXPECTED['relocated_operations'],
            'changed_charts': charts, 'helper_starts': starts, 'helper_finals': finals, 'local_paid_delta': delta,
            'global_paid_delta': {r: 18*n for r, n in delta.items()},
            'trace_equivalence': 'every dependent pair keeps its order; T/T and S/S pairs commute exactly',
            'public_finals_ports_and_owned_lifetimes_fixed': True}


def dense_new_maps(base, word):
    """PR5548's dense all-column exact phase check on every native map absent from the base word."""
    for pin in read(HERE/'SOURCES.json')['dense_native_checker']['files']:
        raw = (REPO/pin['path']).read_bytes()
        need(sha256(raw).hexdigest() == pin['sha256'], 'PR5548 checker bytes: ' + pin['path'])
    K = load(DENSE/'check.py', 'r22_pr5548_dense')
    C = load(DENSE/'sources/clifford_exact.py', 'r22_pr5548_compiler')
    V = load(DENSE/'sources/native_verify.py', 'r22_pr5548_literals')
    def pairs(w):
        s = {(tuple(w['frames'][e[2]]), tuple(w['frames'][e[3]])) for e in w['program'] if e[0] == 'MOVE'}
        live = set(w['live']); main = live | {r+112 for r in live}
        return s | {(tuple(w['frames'][w['initial'][r]]), tuple(w['frames'][w['final'][r]]))
                    for r in range(735) if r not in main}
    out = []
    for a, b in sorted(pairs(word) - pairs(base)):
        recipe, _ = C.lower_child(C.canonical_frame(9, a).adjoint().then(C.canonical_frame(9, b)))
        need(recipe['rank'] == len(b) - len(a), 'New native map rank')
        actual, expected = V.recipe(recipe), V.adjoint(V.frame(list(a), 9)) + V.frame(list(b), 9)
        rec = K.compare_all(actual, expected, 'new map')
        fault = K.first_difference(tuple(actual) + (('phase', 1),), expected)
        out.append({'source': list(a), 'target': list(b), 'rank': recipe['rank'],
                    'matrix_sha256': rec['matrix_sha256'], 'global_phase_fault_rejected_at_column': fault})
    need(len(out) == EXPECTED['new_native_maps'], 'Exact new native map inventory')
    return {'maps': out, 'complex_entries_each': 512*512, 'checker': 'PR5548 compare_all, unmodified'}


def controls(L, base, word):
    variants = {}
    bad = deepcopy(word)                       # undo one reorder: the postponed 213 += 2*707 back before the O-chart read
    p = bad['program']
    k = p.index(['ADD', 213, 707, '2', 594])
    pair = p[k-1:k+1]
    need(pair[0] == ['MOVE', 213, 3, 594, False], 'Control anchor')
    del p[k-1:k+1]
    j = p.index(['ADD', 213, 473, '1/2', 3])
    p[j:j] = pair
    variants['undo_reorder'] = bad
    bad = deepcopy(word)
    e = next(e for e in bad['program'] if e == ['ADD', 113, 531, '1', 3]); e[-1] = 597
    variants['old_pivot_chart'] = bad
    bad = deepcopy(word)
    bad['initial'][531] = 597
    variants['helper_start_not_lowered'] = bad
    bad = deepcopy(word)
    e = next(e for e in bad['program'] if e == ['ADD', 197, 531, '-1', 3]); e[-2] = '1'
    variants['wrong_scalar_coefficient'] = bad
    rejected = {}
    for name, w in variants.items():
        try:
            L.replay(w)
        except ValueError as error:
            rejected[name] = str(error)
        else:
            raise ValueError('Accepted invalid word: ' + name)
    old, new = scalar(base['program']), scalar(word['program'])
    swapped = list(new)                        # a dependent pair out of order: read 531 after its next write
    a = swapped.index(['ADD', 113, 531, '1', 3]); b = next(i for i, e in enumerate(swapped) if e[:3] == ['ADD', 531, 351])
    swapped.insert(b, swapped.pop(a))
    try:
        trace_equivalent(old, swapped)
    except ValueError as error:
        rejected['dependent_pair_swapped'] = str(error)
    else:
        raise ValueError('Accepted a non-commuting reorder')
    try:
        inventory(base, base)
    except ValueError as error:
        rejected['unchanged_word'] = str(error)
    else:
        raise ValueError('Accepted unchanged word as a profile improvement')
    print('PASS controls', rejected, flush=True)
    return rejected


def ceiling(E, targets, paid):
    """Bound the moment derivative on the retained BIT band (as PR5580)."""
    cap = Q('0.0034')
    lower = upper = Q(0)
    for rank in targets.keys() | paid.keys():
        coefficient = paid.get(rank, 0) - targets.get(rank, 0)
        power = (E.power(rank, 1-cap)[0], Q(rank))
        term = E.scale(E.mul(power, E.log_bounds(rank)), coefficient)
        lower += term[0]
        upper += term[1]
    need(upper < 0, 'Strictly decreasing complete moment on the retained BIT band')
    return {'kappa_interval': [Q(0), cap], 'moment_derivative': [lower, upper],
            'scope': 'This fixed paid and target invoice; the inherited BIT cap is retained.'}


def main():
    sources = read(HERE/'SOURCES.json')
    for pin in sources['external_inputs']:
        raw = (HERE/pin['local_path']).read_bytes()
        need(sha256(raw).hexdigest() == pin['sha256'], 'Source bytes: ' + pin['local_path'])
        need(sha1(('blob ' + str(len(raw)) + '\0').encode() + raw).hexdigest() == pin['git_blob'],
             'Source Git object: ' + pin['local_path'])
    base = read(HERE/'inputs/pr5580-WORD.json.gz')
    word = read(HERE/'WORD.json.gz')
    need(construct(base) == word, 'Regenerated complete word payload')
    inv = inventory(base, word)
    source_price = (HERE/'inputs/pr5580-pricing.py').read_text()
    for before, after in json.loads((HERE/'tools/pricing-literals.json').read_text()):
        need(source_price.count(before) == 1, 'Unique pricing declaration: ' + before)
        source_price = source_price.replace(before, after)
    need(source_price == (HERE/'pricing.py').read_text(), 'Only declared pricing constants change')
    print('PASS source pins, exact reconstruction, trace equivalence and changed invoice', flush=True)
    dense = dense_new_maps(base, word)
    print('PASS dense all-column phase check of new native maps', len(dense['maps']), flush=True)
    with closure() as root:
        L = load(root/'research/p104-productive-controller/local.py', 'local')
        L.ROOT = root
        parent_local = L.replay(base)
        local = L.replay(word)
        need(parent_local['real_scalar_allowance'] == local['real_scalar_allowance'], 'Same scalar allowance')
        hd = {str(r): local['helpers'].get(r, 0) - parent_local['helpers'].get(r, 0)
              for r in sorted(local['helpers'].keys() | parent_local['helpers'].keys())
              if local['helpers'].get(r, 0) != parent_local['helpers'].get(r, 0)}
        need(hd == EXPECTED['helper_credit_delta'], 'Exact helper credit change')
        rejected = controls(L, base, word)
        print('PASS both exact arbitrary-input endpoints', flush=True)
        reverse = L.reverse_columns(word)
        print('PASS exact transpose', flush=True)
        native = L.native(word)
        print('PASS exact signed native maps', native['distinct_maps'], flush=True)
        C = load(root/'research/p104-productive-controller/caller.py', 'reframe_caller')
        caller = C.construct()
        need(caller == read(root/'research/p104-productive-controller/CONTROLLER.json'), 'Exact physical caller')
        physical = C.physical(caller, word)
        print('PASS full physical caller', flush=True)
        P = load(HERE/'pricing.py', 'reframe_pricing')
        result = P.run(local, native, caller, physical)
        print('PASS complete pricing', result['raw_root_interval'], flush=True)
        E = L.load(root/'research/higher-moment-strictification/verify.py', 'reframe_margin')
        targets = {int(r): n for r, n in result['targets'].items()}
        paid = {int(r): n for r, n in result['paid'].items()}
        parent_paid, parent_targets = dict(paid), dict(targets)
        for r, n in inv['global_paid_delta'].items():
            parent_paid[int(r)] -= n
        for r, n in hd.items():
            parent_targets[int(r)] -= 18*n
        parent_signs = []
        for k in PARENT_INTERVAL:
            t, p = E.moment(parent_targets, 1-k), E.moment(parent_paid, 1-k)
            parent_signs.append((t[0]-p[1], t[1]-p[0]))
        need(parent_signs[0][0] > 0 > parent_signs[1][1], 'Exact predecessor crossing')
        lo, hi = map(Q, result['raw_root_interval'])
        gain = [lo-PARENT_INTERVAL[1], hi-PARENT_INTERVAL[0]]
        need(gain[0] > 0, 'Strict gain over predecessor raw ceiling')
        fixed_ceiling = ceiling(E, targets, paid)
    receipt = P.encode({'status': EXPECTED['status'], 'inventory': inv, 'helper_credit_delta': hd,
                        'local': local, 'transpose': reverse, 'native': native, 'dense_new_maps': dense,
                        'physical': physical, 'controls': rejected,
                        'parent_raw_interval': PARENT_INTERVAL, 'raw_gain_interval': gain,
                        'fixed_invoice_ceiling': fixed_ceiling, 'result': result})
    if '--write' in sys.argv:
        (HERE/'RESULT.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    else:
        need(receipt == read(HERE/'RESULT.json'), 'Exact complete committed receipt')
    print(EXPECTED['status'], flush=True)


if __name__ == '__main__':
    main()

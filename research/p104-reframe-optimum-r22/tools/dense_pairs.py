"""PR5548 (Clear1nsight) dense all-column exact phase check for every NEW native map of a word:
MOVE frame pairs and helper (initial, final) boundaries absent from the base word.
Uses PR5548's capsule check.py (dense_column/compare_all) and its pinned clifford_exact/native_verify, unmodified."""
import sys, json, gzip, importlib.util
from pathlib import Path
A = Path(sys.argv[3] if len(sys.argv) > 3 else Path(__file__).resolve().parents[2]/'p104-contact-independent-audit/capsule/outputs/p104-native-contact-audit-20261025')
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m
K = load(A/'check.py', 'pr5548_check'); C = load(A/'sources/clifford_exact.py', 'p104_ce'); V = load(A/'sources/native_verify.py', 'p104_nv')
rd = lambda p: json.loads(gzip.decompress(Path(p).read_bytes()))
base, word = rd(sys.argv[1]), rd(sys.argv[2])
def pairs(w):
    s = {(tuple(w['frames'][e[2]]), tuple(w['frames'][e[3]])) for e in w['program'] if e[0] == 'MOVE'}
    live = set(w['live']); main = live | {r + 112 for r in live}
    s |= {(tuple(w['frames'][w['initial'][r]]), tuple(w['frames'][w['final'][r]])) for r in range(735) if r not in main}
    return s
new = sorted(pairs(word) - pairs(base))
out = []
for a, b in new:
    op = C.canonical_frame(9, a).adjoint().then(C.canonical_frame(9, b))
    recipe, _ = C.lower_child(op)
    rank = abs(len(b) - len(a))
    K.need(recipe['rank'] == rank, 'native rank')
    actual = V.recipe(recipe); expected = V.adjoint(V.frame(list(a), 9)) + V.frame(list(b), 9)
    rec = K.compare_all(actual, expected, str((a, b)))
    phased = tuple(actual) + (('phase', 1),)
    col = K.first_difference(phased, expected)
    out.append(dict(source=list(a), target=list(b), rank=rank, matrix_sha256=rec['matrix_sha256'], global_phase_fault_first_column=col))
    print('PASS dense', len(a), '->', len(b), 'rank', rank, rec['matrix_sha256'][:16], 'phase-fault rejected at column', col, flush=True)
print(json.dumps(dict(new_maps=len(out), maps=out, complex_entries_per_map=512*512)))

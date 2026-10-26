"""Emit EDITS.json turning a base P104 word into a candidate word: appended frames, changed
initial/final charts, and program hunks as (unique old run -> new run), widened with context until
each old run occurs exactly once.  usage: gen_edits.py BASE.json.gz CAND.json.gz OUT.json"""
import difflib, gzip, json, sys


def read(p):
    return json.loads(gzip.decompress(open(p, 'rb').read()))


def count(prog, run):
    k = len(run)
    return sum(1 for i in range(len(prog) - k + 1) if prog[i:i + k] == run)


def main(bp, cp, out):
    a, b = read(bp), read(cp)
    assert b['frames'][:len(a['frames'])] == a['frames']
    A = [json.dumps(e) for e in a['program']]; B = [json.dumps(e) for e in b['program']]
    ops = [o for o in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes() if o[0] != 'equal']
    # merge hunks closer than 3 events, then widen each with equal context until unique
    merged = []
    for t, i1, i2, j1, j2 in ops:
        if merged and i1 - merged[-1][1] < 3:
            merged[-1] = [merged[-1][0], i2, merged[-1][2], j2]
        else:
            merged.append([i1, i2, j1, j2])
    hunks = []
    for i1, i2, j1, j2 in merged:
        while not (i2 > i1 and count(a['program'], a['program'][i1:i2]) == 1):
            i1, j1 = i1 - 1, j1 - 1      # leading context (equal in both words)
            assert a['program'][i1] == b['program'][j1]
        hunks.append([a['program'][i1:i2], b['program'][j1:j2]])
    edits = {'frames': b['frames'][len(a['frames']):],
             'initial': {str(r): [x, y] for r, (x, y) in enumerate(zip(a['initial'], b['initial'])) if x != y},
             'final': {str(r): [x, y] for r, (x, y) in enumerate(zip(a['final'], b['final'])) if x != y},
             'program': hunks}
    json.dump(edits, open(out, 'w'), separators=(',', ':'))
    print('hunks', len(hunks), 'old events', sum(len(h[0]) for h in hunks), 'new events', sum(len(h[1]) for h in hunks),
          'frames', len(edits['frames']), 'initial', edits['initial'], 'final', edits['final'])


if __name__ == '__main__':
    main(*sys.argv[1:4])

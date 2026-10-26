"""Construct the R22 word from the source P104 word and EDITS.json.

Joel Pulikkan (GamingPuzzled) with Claude Opus 5.5 (Anthropic) via Claude Code. Apache-2.0.

EDITS.json lists appended charts, changed helper start/final charts, and program hunks.
Each hunk replaces one exact run of source events that occurs exactly once; hunks may not overlap.
"""
from copy import deepcopy
from pathlib import Path
import json

EDITS = json.loads((Path(__file__).resolve().parent/'EDITS.json').read_text())


def locate(program, run):
    hits = [i for i in range(len(program) - len(run) + 1) if program[i:i+len(run)] == run]
    assert len(hits) == 1, ('unique source run', run[:2], hits)
    return hits[0]


def construct(base, schema='p104-r22-reframe/1'):
    word = deepcopy(base)
    word['frames'] += deepcopy(EDITS['frames'])
    for key in ('initial', 'final'):
        for r, (old, new) in EDITS[key].items():
            assert word[key][int(r)] == old, ('source chart', key, r)
            word[key][int(r)] = new
    program = word['program']
    spots = sorted((locate(program, old), old, new) for old, new in EDITS['program'])
    for (i, old, _), (j, _, _) in zip(spots, spots[1:]):
        assert i + len(old) <= j, 'Disjoint hunks'
    for i, old, new in reversed(spots):
        program[i:i+len(old)] = deepcopy(new)
    word['schema'] = schema
    return word

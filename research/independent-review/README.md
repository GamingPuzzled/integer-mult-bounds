# Independent review of open κ claims, 11 October 2026

This review checks the open CrocSwap pull requests that claim a conditional
exponent above the reviewed gen4 result. It follows the verifier-first practice
of Georgiev, Gómez-Serrano, Tao and Wagner, *Mathematical exploration and
discovery at scale* (arXiv:2511.02864): assume a search may exploit its
verifier, replay every claim from a fresh extract, and recompute the score by
code that the claim does not ship. Negative results are recorded in
[NEGATIVE-RESULTS.md](NEGATIVE-RESULTS.md).

Scope: finite replay and exact arithmetic only. The original #109 framework, the
all-size compiler, chart, routing, restored-row, prime-supply, precision/recovery
and analytic interfaces, and every unmerged predecessor these PRs vendor, remain
assumptions. Nothing here is a formal proof or a human peer review. PR replays
for #355–#365 were performed by delegated Claude subagents in this session and
spot-checked as noted; the gen4 and #366 replays and the independent #366
score were run directly.

## Results

All runs used Python 3.13, a fresh `git archive` extract of the PR head, and a new
output directory. "Scorer" is [independent_bit_score.py](independent_bit_score.py):
it recomputes every MOVE/COPY rank from frame dimensions, rejects a word whose
rank fields disagree, and certifies the largest 10^-18 grid bit saving with its
own exact rational log/exp enclosures.

| PR | Head | Claimed κ | Replay | Scorer | Verdict |
| --- | --- | --- | --- | --- | --- |
| main (gen4) | `12a4934` | 90446448750933/1.25e17 ≈ 7.23572e-4 | PASS, 7m13s | — | reproduced |
| #366 | `d3d8420` | 160987957846297/2e17 ≈ 8.04940e-4 | PASS, 8m42s | exact agreement | reproduced, caveats |
| #364 | `f8c6a47` | 201219842699733/2.5e17 ≈ 8.04879e-4 | PASS, 6m21s | exact agreement | reproduced, caveats |
| #362 | `f46ddb5` | 804849251275843/1e18 | PASS, 6m22s | exact agreement | reproduced, caveats |
| #358 | `e76d7a9` | 80367971186626189473809/1e26 ≈ 8.03680e-4 | PASS, 744s | exact agreement | reproduced |
| #356 | `c3d16f4` | 401580942485227026650141/5e26 ≈ 8.03162e-4 | PASS, 481s | exact agreement | reproduced |
| #360 | `edef1a7` | 80351298055091/1e17 ≈ 8.03513e-4 | PASS after packaging fix | exact agreement | reproduced, packaging defect |
| #355 | `e59117a` | 801967436473393/1e18 ≈ 8.01967e-4 | PASS after packaging fix | exact agreement | reproduced, packaging defect |
| #365 | `a222705` | complex b = 876412559609473/1e18 | PASS, 2.7s | b reproduced | reproduced; κ unchanged |
| #363 | `9df55da` | complex b = 932783231884153/1e18 | PASS, 9.9s | b reproduced | reproduced, new unproved layout; κ unchanged |

Every bit-side claim is bound by the bit saving. The largest reproduced claim
is #366, 11.25% above the reviewed gen4 result.

## Findings

**#366.** The final word's records hash, `b99fa242…`, equals the PR's
`EXPECTED.json`. The scorer reproduces the bit saving 402794119831239/5e17, and
the bit→κ map recomputed separately gives the claimed κ with the bit side binding
(complex headroom ≈ 7.07e-5). Exact checks cover move/copy ranks against frames
(`stagelib.check`), frame validity and `I-J/9` nondegeneracy, and rational moment
enclosures with adjacent-grid rejection. Two scope points:

- `price.py` uses a hard-coded default complex saving `b`; `complex_b.py`
  recomputes b from the E8 certificate but only prints it. We confirmed the
  printed value equals the default exactly. An assertion would close this.
- `stagelib`'s column replay is over F2. Integer correctness of the signed lift
  rests on the columns checker's cancellation-free bound and inherited scalar
  evidence.

The 47 outer inequalities are asserted by the PR's own `outer.py`; they were not
recomputed independently.

**#364 / #362.** `verify.sh` asserts the recomputed complex b. In this lineage
`data/parity` is the PR's own regenerated base word, so "new frames" counts are
relative to it, not to #325, and the README's "1,064 frames new relative to
#325" is copied from #359. `stagelib.full_check` still checks every used frame
of the final word, and nondegeneracy rechecked against the true #325 frames
(8838 differing frames) found none degenerate. Several `cmd && echo` lines under
`set -e` would not stop on failure; all printed in this replay. The producer
regeneration scripts reference paths outside the package.

**#358 / #356.** `legality.cpp` rejects a MOVE/COPY rank that differs from its
frame dimension; the native 24-stage admission is actually executed. The audit's
`assembly.py` reads its root from `REFINEMENT.json`; an independent 1e-27 root
reproduced the claimed κ exactly. The exact integer operator check excludes
MOVEs, which the native geometry check covers.

**#360 / #355.** Both packages' `MANIFEST.json` pin a `.gitattributes` that is not
committed, so the documented `verify.py` fails on a fresh checkout with
"Package source missing, changed or unlisted". Replays used a copy with only
that manifest entry removed. Integer correctness is checked over Z against the
source word (int128 with overflow guards); the source words are compacted forms
of unmerged #351/#354 words whose conversion is not replayed.

**#365 / #363.** Both start from Sussman's identical `gcert1-e8-r783` certificate.
Neither changes κ: running #366's `outer.assembly` with b equal to the old value,
#365's or #363's gives the same κ, since the bit side binds. #363's seven-stage
bridged layout B₃ has no written or Lean proof (Sussman's bridge certificate covers
the five-stage layout) and inherits five-stage row constants. If admitted, it raises
the complex cap to ≈ 9.33e-4, so bit-side gains up to that cap would count.

## Reproduce

```sh
git fetch https://github.com/CrocSwap/integer-mult-bounds.git pull/366/head:pr366
git archive pr366 research/w3-design-t-mc-coupled-retiming | tar -x -C /tmp/pr366src
python3 -B /tmp/pr366src/research/w3-design-t-mc-coupled-retiming/verify.py /tmp/pr366out
python3 -I research/independent-review/independent_bit_score.py /tmp/pr366out/candidate \
    402794119831239/500000000000000000
```

Requires numpy, mpmath, a C++17 compiler and Boost headers. The receipt is
[receipts/pr366.json](receipts/pr366.json).

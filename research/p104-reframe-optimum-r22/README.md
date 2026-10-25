# Reorder + re-frame optimum on the P104 word: conditional kappa .00308598

Complete conditional kappa **.00308598** (certified claim line; tested at .0030859805). The exact raw crossing is in
(0.00308598907633, 0.00308598907634). That is **+4.0941077e-6** (+0.133%) over the raw crossing
(0.00308189496866, 0.00308189496867) of [PR5580](https://github.com/CrocSwap/integer-mult-bounds/pull/5580)
(aliromman, claim .00308189), the newest P104 head at the time of writing. The exact gain interval is
(204705383/50000000000000, 25588173/6250000000000).

**Conditional on** the same assumptions as PR5580:
(a) the five framework assumptions retained since PR5544/5545;
(b) the validity of the inherited P104 line (PR5551, PR5561, PR5569, PR5580);
(c) free helper endpoints (PR5561; audited against the PR5550 contract in PR5567). This word lowers two helper
start frames to dim 0 and one helper final frame (307) from dim 5 to dim 4.
The selected record is not changed. No independent human or proof-kernel acceptance is claimed.

## What changes

Not one contact at a time: this word is the **solver optimum of a whole-word model**. The model covers every
re-framing of every scalar operation together with every reordering inside the exact commutation poset. It was
solved on three nested domain families (below). The construction keeps every scalar instruction, coefficient,
owned lifetime, public main endpoint and literal port. It has three parts.

1. **Five commuting ADDs are postponed**:
   - `213 += 2*707`;
   - `113 += 2*710`;
   - `198 += 2*710`;
   - `572 += -2*710`;
   - `573 += 2*710`.

   Each one commutes exactly with the operations it passes, because only (T,T) and (S,S) pairs on a shared register
   are crossed. `verify.py` checks that the new scalar order is a linear extension of the dependence order: every
   dependent pair keeps its order (Cartier–Foata). Replay then confirms all 743 rows exactly.
2. **Thirteen ADDs change chart**:
   - Eight reads of helpers 473, 531, 648, 649, 650 and 652 leave the dim-1 pivot charts 594/597 for the empty
     chart O (frame 3).
   - `197 += 319` moves 617 -> 355 (dim 3 -> 2).
   - `473 += 100` moves 718 -> 716 (4 -> 3).
   - `319 += 85` and `507 += 319` move 728 -> a new dim-3 chart [44,30,487].
   - `307 += -85` moves 236 -> 235 (5 -> 4).
3. **Helper endpoints**:
   - Helpers 473 and 531 now start at O (dim 0) instead of dim 1. Their credit rises from H8 to H9.
   - Helper 307 now ends at 235 (dim 4). Its credit falls from H5 to H4.

Per local call:

| | change |
|---|---|
| paid MOVE jobs | H1 −10, H2 −2, H3 +2, H4 −4, H5 +5 (3,454 → 3,445 transports) |
| helper credits | H4 +1, H5 −1, H8 −2, H9 +2 |
| rank-mass surplus | unchanged, 760 |
| productive fields / paid calls (×18 + outer) | 12,814 / 66,690 |

These are the only changes. They remove stops on registers:
- X 85 and X 100;
- Y 197;
- helpers 307, 319, 507, 648, 649, 650 and 652.

The reorder is essential. Without it, the dim-1 pivot is forced: `213 += 2*707` (and the 710 reads) precede the
O-chart reads on the same target in program order. The `undo_reorder` control in `verify.py` shows that putting
`213 += 2*707` back makes the word illegal (`Scalar destination and coefficient`).

## Model and optimality evidence (tools/)

R13's dependency-respecting reorder model (PR4610 round-three word) is ported to the native P104 grammar of
PR5545 `local.py`:
- **Operations.** The operations are ADD, COPY, SCALE, INIT and CLEAR. MOVEs are synthesized from the frames.
- **Commutation.** Per register, each operation is a T (ADD target), an S (ADD/COPY source) or an X (anything
  else). T/T and S/S pairs commute exactly; all other pairs conflict.
- **Owned registers.** Owned registers (735..742) keep every operation exclusive, and their operations stay
  pinned to their charts. INIT and CLEAR also share a lifetime token.
- **Cost.** The cost per register is Σ f(jump) over its frame chain, minus f(final − initial) for helpers with free
  endpoints. Main X and Y endpoints are pinned. f(x) = x^(1−κ) is the exact linearization of the root.
- **MIP.** The exact subspace MIP (`tools/mip104.py`, HiGHS, one thread) uses:
  - per-register unit paths over candidate frames between forced frames (virtual source and sink for free helper
    endpoints);
  - op frame choices on the paths of all their registers;
  - dims-monotone consecutive conflict groups;
  - transitive-closure ordering inside commuting groups.
- **Realization.** The model is realized by a stable topological sort (`tools/realize104.py`).
- **Cycle cuts.** Owned chains decrease in dimension, which breaks R13's acyclicity lemma. A dimension-order cut is
  therefore added lazily for every realized cycle (`tools/loop104.py`): the frame edges of a cycle cannot all be
  active.

Positive control: realizing the current frames reproduces PR5580's word. The scalar order and all frames are
identical. The only MOVE-order difference is PR5580's own single source-first MOVE pair, which is reproduced by an
override. The invoice is identical.

| domain family (forward; the P104 caller is forward-only) | free ops | MIP vars | optimum (chain cost / local) | status |
|---|---:|---:|---:|---|
| current word (PR5580) | | | 1678.557119 | |
| no reorder (fixed order), medium domain | 1,208 | 22k | 1678.556906 (+1.7e-8 κ) | optimal |
| reorder, restricted (frames of the op's registers) | 1,269 | 13k | 1678.511536 (+3.353e-6 κ) | optimal, 1 cut round |
| reorder, medium (all 1,089 word frames) | 2,159 | 38k | 1678.511536 | optimal, same |
| reorder, wide (all subspaces in [low, up] when the gap is ≤ 3, else medium) | 3,955 | 180k | **1678.501486 (+4.094e-6 κ)** | optimal and acyclic, 2 cut rounds; **this word** |

PR5568's fixed-order event retime (`evlat.py`, K=2/4, maxm 0/3) finds 0 on PR5580's word, matching the
fixed-order row. Larger domains (gap ≤ 4: 682k vars; gap ≤ 5: 5.7M vars) and the gap-5 LP ceiling are reported
in the PR text when available. This package claims optimality only for the three solved families.

## Verification (`verify.py`, stdlib, Python 3.12, about 4 minutes)

- Source pins: PR5580's word and pricing (Git blob + SHA-256) and the byte-pinned PR5545 capsule (33 payloads).
  The PR5548 dense checker files are pinned too.
- Exact regeneration from PR5580's word through 25 literal hunks (`construct.py`).
- Inventory: trace equivalence; exactly 13 changed charts and 3 changed helper endpoints; the exact paid and
  credit deltas.
- **PR5548 (Clear1nsight) dense all-column exact phase check** of all 12 native maps that are new in this word.
  These are MOVE pairs and helper boundaries, with 512×512 complex entries each. A global-phase fault is rejected
  for each.
- The unmodified PR5545 `local.py` stack:
  - replay of both arbitrary-input endpoints;
  - dense transpose columns;
  - all 2,913 native maps;
  - the exact physical caller (18 forward calls).
- `pricing.py`: PR5580's pricing with only four literals changed (`LITERAL-CHANGES.diff`): the claim line, the
  previous line, the paid-call count and the label. It covers both moment engines, the compiler and all 54 strict
  + 4 functional outer checks.
- Exact predecessor crossing, strict gain and the fixed-invoice derivative ceiling.
- Six controls, all rejected:
  - undoing one reorder;
  - the old pivot chart;
  - the helper start not lowered;
  - a wrong coefficient;
  - a dependent pair out of order (trace check);
  - the unchanged word.

**Second check outside the package.** The PR5550 checker (Chris R / Clear1nsight), patched exactly as in PR5567
(Matarener: four literal input lines, temporary copy), was run with this package's invoice. It returns
`PASS_SCOPED_CALLER_AND_TARGET_BINDING`:
- 66,690 paid / 12,814 productive;
- 527 helper normalizers;
- 268 signed-Pauli and phase anchors;
- all 10 controls reject.

PR5580's invoice on this word is rejected, and so is this invoice on PR5580's word.

## Reproduce
```sh
python3.12 -B scripts/research_package.py --package research/p104-reframe-optimum-r22
python3.12 -B research/p104-reframe-optimum-r22/verify.py            # PASS_P104_REFRAME_OPTIMUM_KAPPA_00308598
# discovery (needs highspy and PR5568's infra/legal.py, price_exact.py via TK_INFRA):
python3.12 research/p104-reframe-optimum-r22/tools/loop104.py WORD restricted 600 3 OUT.json.gz
python3.12 research/p104-reframe-optimum-r22/tools/loop104.py WORD wide 2400 3 OUT.json.gz
```

## Credits
- aliromman: PR5580 (the base word), PR5579, PR5544/5545 (the P104 word line, `local.py`, the caller and pricing).
- DreamingOfClouds: PR5561 (free helper endpoints), PR5553 (hand-offs 473/531) and PR5568 (legality oracle,
  exact invoice and evlat).
- thu-nmrc: PR5551 (coupled P104 contacts).
- Matarener: PR5567 (endpoint-contract audit and checker patch) and PR5572.
- Clear1nsight: PR5550 (caller checker), PR5548 (dense native check) and PR5577.
- hexapode: PR5565 (commuting-read contact retiming).
- GamingPuzzled: PR5569 (priced hand-off of helper 706), PR5472, and R13's reorder model (PR4610 round-three
  word).
- Lineage: PR2305/2152/2219. The credits in `local.py` (David Arias, Cinna Davis, Gareth Davidson) are retained.
- zxv: productive-helper paradigm #4359.
- Cao Yifan: #4610 native semantics.
All predecessor credit is retained.

AI disclosure: Claude Opus 5.5 (Anthropic) via Claude Code, directed by Joel Pulikkan (GamingPuzzled). Apache-2.0.

## Open next questions
- Larger domain families (complete intervals with gap ≥ 4) and the full-interval LP gap.
- Owned-holder registers are pinned here. Freeing their charts needs the reversed-chain version of the cuts.
- Non-commuting rewrites with correction terms (R13 stage 3) on this word.

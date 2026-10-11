# Retimed E8 complex unit in the seven-stage bridged word

**Conditional κ = 233014627343551/250000000000000000 ≈ 9.32058509374204 × 10⁻⁴**,
**+0.01551%** over PR #373 (93191395651209/10¹⁷). The complex side binds.

**Status: superseded.** PR #375's unsplit B₃ layout and the complex retimings
in PRs #374 and #378 already exceed this value, and PR #380 (≈ 9.6726 × 10⁻⁴,
bit-bound) is higher again. The package is kept as a verified record.

This is a composition of three open, unmerged pull requests. It adds no new
circuit:

- **PR #365** (Ali Romman, `a222705`): four coupled frame changes to Jacob
  Sussman's E8 complex unit. The rational scalar operator is unchanged, and one
  child fewer is charged per invocation.
- **PR #363** (DaysSky, `9df55da`): the seven-stage bridged word B₃ and its
  complex guard.
- **PR #373** (DaysSky, `3ff87b5`): PR #370's E8 bit word in B₃, giving bit
  coarse saving c = 968197503705007/10¹⁸, and the outer assembly.

PR #365 priced its unit only in the five-stage word. PR #373 used the
unretimed unit. Running PR #365's certificate through PR #363's seven-stage
guard gives

| | b₃ (complex coarse saving) | κ |
| --- | --- | --- |
| PR #363 / #373 | 932783231884153/10¹⁸ | 93191395651209/10¹⁷ |
| this composition | 932928054566567/10¹⁸ | 233014627343551/2.5·10¹⁷ |

The seven-stage ledger changes exactly as PR #365's per-invocation histogram
change predicts, multiplied by seven stages: 29971 calls instead of 29978, with
rank mass 94473, deficit 216 and max child 31 unchanged. The guard also records
two more frames, two more phase-A gates and a slightly smaller local bill.

## Reproduce

```sh
python3 -B research/e8-retimed-seven-stage/verify.py /tmp/e8-retimed-out   # ~12 s
```

Requires Python 3.11+ standard library only. The verifier:

1. checks the hash of every vendored file (`MANIFEST.json`);
2. runs PR #365's own verifier, which checks equal scalar maps, legal frame
   paths and rejection of damaged inputs;
3. runs PR #363's unchanged guard on the original certificate, which must
   reproduce PR #363's pins;
4. runs the guard on the retimed certificate with every regression count pinned
   (`pins-e8-b3-retimed.json`), and requires a sign-flipped retimed certificate
   to be rejected (it fails Sussman's E5 scalar identity);
5. certifies b₃ with both vendored rational engines, the 10⁻¹⁶ fallback and
   adjacent-grid rejection, plus an independent exact enclosure written here;
6. computes κ with PR #373's `outer.py`: 47 strict constraints, rejection of
   the adjacent κ tick and of the complex leaf cap.

## Scope and open obligations

Every obligation of the three source PRs is inherited.

- **Seven-stage layout B₃ is unproved.** It has no Lean or written proof;
  Sussman's bridge certificate covers only the five-stage B₂. Its row constants
  are carried over from five stages.
- **The retimed unit has no Lean build.** PR #363's step regenerating
  Sussman's Lean data byte for byte applies only to the original certificate
  and is not run here.
- **PR #370's E8 bit word is checked over F₂.** That is the accepted standard,
  not a gap: the reviewed gen4 result deletes its even-coefficient payload ADDs
  as "identities over F₂" (`research/five-stage-gen4-banks/PROOF.md:100`). Even
  PR #366's p=10 word, whose helpers do restore over ℤ, has y outputs that over ℤ
  carry even multiples of helper registers. An earlier version of this note
  called F₂-only correctness an open requirement; that was wrong. κ here
  depends only on b₃, provided PR #370's word stays admissible above the
  complex cap.
- The bit coarse saving c is an input certified by PR #373's `verify.sh`; this
  package does not replay the bit word. An independent replay of PR #373 at
  `3ff87b5` reproduced c exactly.
- The original #109 framework and the all-size compiler, chart, routing,
  restored-row, precision and analytic interfaces remain assumptions.

## Attribution

Composition and verifier prepared with Claude (Anthropic). The vendored sources
keep their licenses and notices: `vendor/pr363-complex/` (DaysSky; Jacob
Sussman's E8 unit and Lean sources), `vendor/pr365/` (Ali Romman), and
`vendor/pr373-pricing/` (DaysSky; PR #315 engines).

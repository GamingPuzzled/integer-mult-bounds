# Negative results on the PR #62 stacked witness (historical construction)

These two bounded experiments were run on the PR #62 pair-assembly graph
compiled by PR #57's joint frame compiler (`research/pair-assembly/frame`),
before this branch was synchronized with the gen4 checkpoint. They do not
apply to the current five-stage p=10 words. They are recorded so the same
moves are not repeated on that construction.

At that witness the bit moment's log-weighted mass is about 0.459 per unit of
`m*W`. Internal frame-transition blocks carry 47% of it while holding 4% of the
rank mass, because most of them are rank-one children with weight `ln 575`.

## 1. Rank-2 transitions never form a contiguous child

`scripts/experiments/binary_frame_profiles.cpp` charges every transition of
rank at most 2 as singletons without computing its pivots
(`fixed-basis-two-stage.tex`: "rank1/2 may conservatively remain singletons").
There are 77,015 such rank-2 transitions at h=23 and 108,541 at h=25, 24% of
the internal rank mass. Charging every one as a single rank-2 child would raise
the bit saving by about 1.4%.

We ran the unchanged pivot and corner analysis on all of them, with the
three-prime CRT branch enabled for every rank-2 matrix: 79,796 matrices at
h=23 and 112,378 at h=25, with zero modular disagreements. The resulting block
histograms are **identical** to the conservative ones. No rank-2 transition
has consecutive row and column pivots, so the conservative charge is exact.

## 2. Global point relabeling does not help

Relabeling the points of a compiled word by a permutation σ preserves role
counts, envelopes and all correctness checks. The fixed basis `I+J` commutes
with permutations and the data corners do not depend on the producer. Only
the pivot runs change.

- The reversal of the point order leaves the internal log-mass exactly unchanged.
- Four random permutations were worse by 4.3%–4.8% of the internal log-mass.
- A first-improvement transposition hill climb found no improving swap among
  the first transpositions tested at either dimension before it was stopped
  when the branch moved to the gen4 checkpoint.
- Upper bound: even if every transition of rank r formed one block, the
  internal log-mass would fall by 17%, raising the bit saving by at most 8.8%.

Scope: these are bounded searches on one historical construction, not
impossibility proofs.

# R22 model domain (tools used for PR5666, PR5684, PR5739)

The R22 model is an exact MIP over scalar order and charts. `poset104.py` builds the poset and the domains,
`mip104.py` builds and solves the model, `realize104.py` emits a word, and `loop104.py` runs the cycle-cut loop
and the exact price. Run with `P104_NPUB` set to the number of public registers: 743 on PR5627 to PR5713, and 767
on PR5751.

## Order

The order is any linear extension of the commutation poset. Each register's operations are grouped into maximal
runs of one type: ADD target T, ADD/COPY source S, and everything else X. Runs of type (T,T) and (S,S) commute;
every other adjacent pair keeps its order. Owned registers are all-X, so their order is fixed, and INIT/CLEAR
share an `OWN` token. Charts imply further order between ops on the same public register. `realize104.py` turns
these into edges and takes a topological sort. A cycle among them gets a no-good cut in `loop104.py`, and the
model is solved again.

## Charts

Each scalar op picks one chart from its domain. A public register's charts then form a strictly increasing unit
path: one path per register, over the union of its ops' domains. Each arc costs `(dim jump)^(1-kappa)`. The bounds
`lows[i]` and `ups[i]` are the join and meet of the forced neighbours, as in `poset104.bounds`. The modes differ
in which charts each op may use:

- **restricted:** charts the op's registers already use in the source word.
- **medium:** every chart that occurs in the word.
- **wide `maxgap`:** every subspace X with `lows[i] <= X <= ups[i]` when `dim ups - dim lows <= maxgap`.
  Otherwise the medium pool is used, intersected with the bounds. New charts are allowed.

Every mode keeps only charts within the bounds and comparable with each register's forced charts. Every mode
also always includes the op's current chart.

Ops that touch an owned register are pinned to their current chart, unless `OWNED_FREE=1` is set. With
`OWNED_FREE=1`, each owned lifetime becomes a decreasing path with free INIT/CLEAR ends and no credit.

## Endpoints

- **Main X/Y registers:** start and final charts are pinned.
- **Helpers:** endpoints are free (PR5561, audited in PR5567).
  - The path leaves a virtual source `SRC` and enters a virtual sink `SNK`. Both arcs cost nothing.
  - The start is therefore just the chart of the helper's first op, and the final is the chart of its last op.
  - The start can be any chart in that first op's domain. It is not tied to the original start, so it can be
    raised as well as kept or lowered, as long as it stays within the bounds.
  - Credit `-(dim final - dim start)^(1-kappa)` is linked to the chosen start and final dims.
  - A rank-0 helper keeps its original final; see `realize104.py`.

## Large-neighbourhood restriction (PR5739)

`WIN=lo:hi` pins every op outside the op-index window [lo, hi). `WINREGS=r1,r2,...` pins every op that touches
none of the listed public registers. Pinned ops keep their current chart. The PR5739 block was found by a gap-4
run with a 1,000-op window, `wide 1200 4`.

## Packaging

`gen_edits.py BASE CAND EDITS.json` writes unique-run hunks, appended charts and endpoint changes.
`construct_edits.py` applies them.

The legality/pricing oracle (`legal`, `price_exact`) is not included here. It comes from the P104 designer
toolkit (`research/p104-designer-toolkit/infra`) and is located with `TK_INFRA`. Owned-field words need the
patched `legal.py`, which reads `owned_fields`.

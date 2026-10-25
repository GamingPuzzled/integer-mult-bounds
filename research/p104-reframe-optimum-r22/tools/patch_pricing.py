import sys
KAPPA, TESTED, PAID = sys.argv[1], sys.argv[2], sys.argv[3]
import os
P = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
src = open(P + 'inputs/pr5580-pricing.py').read()
REPL = [("KAPPA, TESTED = Q('.00308189'), Q('.0030818905')", "KAPPA, TESTED = Q('%s'), Q('%s')" % (KAPPA, TESTED)),
        ("PREVIOUS = Q('.00308181')", "PREVIOUS = Q('.00308189')"),
        ("sum(paid.values()) == 66852", "sum(paid.values()) == %s" % PAID),
        ("'kappa_decimal':'.00308189','previous_open_pr5569':PREVIOUS", "'kappa_decimal':'%s','previous_open_pr5580':PREVIOUS" % KAPPA)]
for a, b in REPL:
    assert src.count(a) == 1, a
    src = src.replace(a, b)
open(P + 'pricing.py', 'w').write(src)
import json; json.dump(REPL, open(P + 'tools/pricing-literals.json', 'w'), indent=1)

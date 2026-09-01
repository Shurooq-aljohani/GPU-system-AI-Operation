#!/usr/bin/env python3
# Green check for the extra W3D3 lab (load shedding under overload).
# Run next to shedding_report.json:  python verify.py
# Prints exactly one line last: GREEN CHECK: PASS  or  GREEN CHECK: FAIL (<reason>)
# stdlib only.
#
# The lab's numbers are live measurements, so there is no ground truth to
# recompute. Instead this holds the report to the invariants any honest run
# satisfies; the margins are deliberately loose so hardware never fails a
# student, only method does.
import json, os
from typing import NoReturn

SHED_FLOOR_N50 = 20        # cap 8, burst 50: most of the burst must be shed
P95_IMPROVEMENT = 0.8      # accepted p95 must be at most 0.8x the naive p95
SWEEP_FLATNESS = 2.5       # accepted p95 across the sweep: max <= 2.5x min


class _Stop(Exception):
    pass


def _fail(reason) -> NoReturn:
    print("GREEN CHECK: FAIL (%s)" % reason)
    raise _Stop()


def need(d, key, where):
    if not isinstance(d, dict) or key not in d:
        _fail("missing %s in %s" % (key, where))
    return d[key]


def main():
    if not os.path.isfile("shedding_report.json"):
        _fail("shedding_report.json not found; run Step 5 first")
    try:
        with open("shedding_report.json") as f:
            r = json.load(f)
    except json.JSONDecodeError as e:
        _fail("shedding_report.json is not valid JSON: %s" % e)

    naive = need(r, "naive_unbounded_n50", "report")
    shed = need(r, "shedded_cap8_n50", "report")
    sweep = need(r, "shedded_sweep", "report")

    if need(naive, "n_sent", "naive") != 50:
        _fail("naive burst must send 50")
    if need(naive, "n_ok", "naive") < 45:
        _fail("only %s/50 naive requests succeeded; fix the baseline before "
              "measuring shedding on top of it" % naive["n_ok"])
    naive_p95 = need(naive, "p95_s", "naive")
    if not isinstance(naive_p95, (int, float)) or naive_p95 <= 0:
        _fail("naive p95 missing or non-positive")

    if need(shed, "cap", "shedded") != 8 or need(shed, "n_sent", "shedded") != 50:
        _fail("the graded shedded burst is n=50 at cap=8")
    n_acc, n_shed = need(shed, "n_accepted", "shedded"), need(shed, "n_shed", "shedded")
    if n_acc + n_shed > 50:
        _fail("accepted (%s) + shed (%s) exceeds the 50 sent" % (n_acc, n_shed))
    if n_acc < 8:
        _fail("only %s accepted at cap 8; the first wave alone should fill the cap" % n_acc)
    if n_shed < SHED_FLOOR_N50:
        _fail("only %s shed out of 50 at cap 8; the shedder is queueing, not "
              "shedding" % n_shed)
    shed_p95 = need(shed, "accepted_p95_s", "shedded")
    if not isinstance(shed_p95, (int, float)) or shed_p95 <= 0:
        _fail("accepted p95 missing or non-positive")
    if shed_p95 >= naive_p95 * P95_IMPROVEMENT:
        _fail("accepted p95 %.2fs vs naive %.2fs: shedding is not protecting "
              "latency by a real margin" % (shed_p95, naive_p95))

    if not isinstance(sweep, list) or [lvl.get("n_sent") for lvl in sweep] != [8, 16, 32, 50]:
        _fail("shedded_sweep must hold the four levels n=8,16,32,50 in order")
    p95s, sheds = [], []
    for lvl in sweep:
        if lvl.get("cap") != 8:
            _fail("sweep level n=%s ran at cap=%s, the sweep fixes cap 8"
                  % (lvl.get("n_sent"), lvl.get("cap")))
        p = lvl.get("accepted_p95_s")
        if not isinstance(p, (int, float)) or p <= 0:
            _fail("sweep level n=%s has no accepted p95" % lvl.get("n_sent"))
        p95s.append(p)
        sheds.append(lvl.get("n_shed", 0))
    if sheds[0] > 1:
        _fail("n=8 at cap 8 shed %s requests; the cap is rejecting inside "
              "capacity" % sheds[0])
    if any(b < a for a, b in zip(sheds, sheds[1:])):
        _fail("shed counts fall as the burst grows (%s); that cannot happen "
              "with a fixed cap" % sheds)
    if sheds[-1] < 10:
        _fail("largest level shed only %s; the cap is not being enforced" % sheds[-1])
    if max(p95s) > min(p95s) * SWEEP_FLATNESS:
        _fail("accepted p95 varies %.2fs..%.2fs across the sweep; the cap is "
              "not holding latency flat" % (min(p95s), max(p95s)))

    print("invariants hold: shedding happened, accepted p95 protected, cap flat")
    print("GREEN CHECK: PASS")


if __name__ == "__main__":
    try:
        main()
    except _Stop:
        raise SystemExit(1)

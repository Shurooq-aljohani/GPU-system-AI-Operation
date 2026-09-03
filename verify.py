#!/usr/bin/env python3
# Green check for the extra W3D5 lab (cost per million tokens, scale-out).
# Run next to cost_report.json:  python verify.py
# Prints exactly one line last: GREEN CHECK: PASS  or  GREEN CHECK: FAIL (<reason>)
# stdlib only.
#
# The lab is pure arithmetic over the student's own bench levels, so this
# recomputes EVERYTHING from the levels in the report: per-level cost, knee
# selection, and the whole scale-out plan. It works identically for the sample
# bench and a student's real one.
import json, math, os
from typing import NoReturn


class _Stop(Exception):
    pass


def _fail(reason) -> NoReturn:
    print("GREEN CHECK: FAIL (%s)" % reason)
    raise _Stop()


def main():
    if not os.path.isfile("cost_report.json"):
        _fail("cost_report.json not found; run Step 5 first")
    try:
        with open("cost_report.json") as f:
            r = json.load(f)
    except json.JSONDecodeError as e:
        _fail("cost_report.json is not valid JSON: %s" % e)

    for key in ("gpu_hourly_usd", "target_p95_s", "levels", "knee", "scale_out_plan"):
        if key not in r:
            _fail("missing key '%s'" % key)
    rate, slo = r["gpu_hourly_usd"], r["target_p95_s"]
    if not isinstance(rate, (int, float)) or rate <= 0:
        _fail("gpu_hourly_usd must be a positive dollars-per-hour figure")
    if not isinstance(slo, (int, float)) or slo <= 0:
        _fail("target_p95_s must be a positive SLO in seconds")

    levels = r["levels"]
    if not isinstance(levels, list) or len(levels) < 3:
        _fail("levels must hold the bench sweep (at least 3 concurrency levels)")
    for L in levels:
        for f_ in ("concurrency", "tokens_per_s", "latency_p95_s",
                   "cost_per_million_tokens_usd"):
            if not isinstance(L.get(f_), (int, float)):
                _fail("level %r lacks numeric %s" % (L.get("concurrency"), f_))
        if not L["tokens_per_s"] or L["tokens_per_s"] <= 0:
            _fail("level %s reports tokens_per_s <= 0 (an all-error level); rerun the sweep" % L.get("concurrency"))
        want_cost = round(rate / (L["tokens_per_s"] * 3600 / 1_000_000), 4)
        if abs(L["cost_per_million_tokens_usd"] - want_cost) > max(0.0002, want_cost * 0.01):
            _fail("concurrency %s: cost %.4f, the formula gives %.4f "
                  "(tokens/s vs tokens/hour, or a non-hourly rate?)"
                  % (L["concurrency"], L["cost_per_million_tokens_usd"], want_cost))

    under = [L for L in levels if L["latency_p95_s"] <= slo]
    if not under:
        _fail("no level sits under the SLO, so no knee exists; the report "
              "should not have gotten this far (see failure modes)")
    want_knee = max(under, key=lambda L: L["concurrency"])
    knee = r["knee"]
    if not isinstance(knee, dict) or knee.get("concurrency") != want_knee["concurrency"]:
        _fail("knee is concurrency %s; the largest level under the %.1fs SLO "
              "is concurrency %s" % ((knee or {}).get("concurrency"), slo,
                                     want_knee["concurrency"]))

    plan = r["scale_out_plan"]
    want_targets = [round(want_knee["tokens_per_s"] * m, 6) for m in (1.0, 1.5, 2.0, 3.0)]
    if not isinstance(plan, list) or len(plan) != 4:
        _fail("scale_out_plan must hold the four multiples 1.0, 1.5, 2.0, 3.0")
    for row, want_req in zip(plan, want_targets):
        req = row.get("required_tokens_per_s")
        if not isinstance(req, (int, float)) or abs(req - want_req) > max(0.5, want_req * 0.01):
            _fail("plan targets must be the knee's throughput x (1, 1.5, 2, 3); "
                  "got %r, expected %.1f" % (req, want_req))
        want_n = math.ceil(want_req / want_knee["tokens_per_s"] - 1e-9)
        if row.get("replicas_needed") != want_n:
            _fail("required %.1f tok/s: replicas_needed=%r, ceil gives %d"
                  % (req, row.get("replicas_needed"), want_n))
        want_cost = round(want_n * rate, 2)
        if abs(row.get("total_hourly_cost_usd", 1e9) - want_cost) > 0.011:
            _fail("required %.1f tok/s: hourly cost %r, %d replicas at %.2f/h "
                  "gives %.2f" % (req, row.get("total_hourly_cost_usd"),
                                  want_n, rate, want_cost))
        if abs(row.get("effective_p95_s", 1e9) - want_knee["latency_p95_s"]) > 0.011:
            _fail("effective_p95_s must stay at the knee's p95: replicas run at "
                  "the safe concurrency, that is the whole model")

    print("recomputed costs, knee and scale-out plan all agree")
    print("GREEN CHECK: PASS")


if __name__ == "__main__":
    try:
        main()
    except _Stop:
        raise SystemExit(1)

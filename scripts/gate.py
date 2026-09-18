#!/usr/bin/env python3
"""jev-swap gate: mechanical checks over a swap packet.

    python scripts/gate.py swap/<component>     # reads responsibility-map.json + eval-card.json
    python scripts/gate.py --self-test          # fixtures in memory, no files

Enforces SKILL.md gates 1 (complete map), 2 (Jev only owns decisions), 5 (three arms,
wired), 7 (protected files unchanged) and 8 (evidence before status). Stdlib only.
"""
import json
import sys
from pathlib import Path

PRODUCERS = {"jev", "code", "original", "removed"}
KINDS = {"decision", "arithmetic", "date", "exact_string", "identifier", "generation", "rendering", "side_effect", "other"}
VERDICTS = {"KEEP", "REJECT", "NEEDS_EVIDENCE"}
STATUSES = {"IN_PROGRESS", "QUALIFIED_CANDIDATE", "PROMOTED", "BLOCKED"}
VERSION_KEYS = ("candidate_sha", "jev_model", "threshold_policy_version", "dataset_snapshot", "rubric_version")


def check_map(m):
    f = []
    for key in ("component", "claim", "commit_boundary", "fields"):
        if not m.get(key):
            f.append(f"map: missing {key}")
    if m.get("commit_boundary") and ":" not in str(m["commit_boundary"]):
        f.append("map: commit_boundary must be a path:line, not a sentence")
    for fld in m.get("fields") or []:
        n = fld.get("name", "?")
        if fld.get("producer_after") not in PRODUCERS:
            f.append(f"map: field {n}: producer_after must be one of {sorted(PRODUCERS)}")
        if fld.get("kind") not in KINDS:
            f.append(f"map: field {n}: kind must be one of {sorted(KINDS)}")
        elif fld.get("producer_after") == "jev" and fld["kind"] != "decision":
            f.append(f"map: field {n}: kind {fld['kind']} cannot be owned by jev (jaggedness)")
        if not fld.get("consumers") and not fld.get("consumers_verified_empty"):
            f.append(f"map: field {n}: no consumers listed and not verified empty")
        if not fld.get("invariant"):
            f.append(f"map: field {n}: missing invariant")
        if not fld.get("evidence") or str(fld["evidence"]).upper() == "NONE":
            f.append(f"map: field {n}: evidence is missing or NONE")
    controls = (m.get("case_set") or {}).get("planted_controls") or {}
    for c in ("confident_wrong", "out_of_set", "adversarial_state", "large_noisy_state", "provider_failure_injection"):
        if not controls.get(c):
            f.append(f"map: case_set missing planted control {c}")
    return f


def check_card(c):
    f = []
    arms = c.get("arms") or {}
    for a in ("A", "B", "C"):
        if a not in arms:
            f.append(f"card: arm {a} missing")
    if f:
        return f
    A, B, C = arms["A"], arms["B"], arms["C"]
    if A.get("jev_calls", 0) != 0:
        f.append("card: arm A made Jev calls (contaminated baseline)")
    for a, arm in (("B", B), ("C", C)):
        if not arm.get("jev_calls"):
            f.append(f"card: arm {a} made zero Jev calls (unwired mechanism)")
    min_cases = c.get("min_cases", 30)
    for a, arm in arms.items():
        n = arm.get("n", 0)
        if n < min_cases and not (c.get("n_available", 0) < min_cases and c.get("all_available_used")):
            f.append(f"card: arm {a} n={n} below min_cases={min_cases}")
    ceiling = c.get("critical_error_ceiling")
    if ceiling is None:
        f.append("card: critical_error_ceiling missing")
    else:
        rate = lambda arm: arm.get("critical_errors", 0) / max(arm.get("n", 0), 1)
        if rate(C) > ceiling:
            f.append(f"card: arm C critical-error rate {rate(C):.3f} above ceiling {ceiling}")
        if rate(C) > rate(A):
            f.append(f"card: arm C critical-error rate {rate(C):.3f} above baseline {rate(A):.3f}")
    fb = C.get("fallback_rate")
    if fb is None:
        f.append("card: arm C fallback_rate missing")
    elif fb >= c.get("fallback_rate_ceiling", 0.5):
        f.append(f"card: arm C fallback_rate {fb} at or above ceiling (hybrid hiding a weak candidate)")
    if C.get("downstream_field_integrity", 0) < 1.0:
        f.append("card: arm C downstream_field_integrity below 1.0")
    if c.get("graders_sha_at_plan") != c.get("graders_sha_at_eval"):
        f.append("card: protected graders changed between plan and eval (weakened check)")
    if not c.get("run_ids") or not c.get("evaluated_at"):
        f.append("card: run_ids or evaluated_at missing (stale or unobserved measurement)")
    if c.get("verdict") not in VERDICTS:
        f.append(f"card: verdict must be one of {sorted(VERDICTS)}")
    if c.get("status") not in STATUSES:
        f.append(f"card: status must be one of {sorted(STATUSES)}")
    if c.get("status") in ("QUALIFIED_CANDIDATE", "PROMOTED"):
        for k in VERSION_KEYS:
            if not c.get(k) or "REPLACE" in str(c[k]):
                f.append(f"card: status {c['status']} requires {k}")
    if c.get("status") == "PROMOTED":
        rb = c.get("readback") or {}
        if rb.get("deployed_sha") != c.get("candidate_sha") or not rb.get("observed_at"):
            f.append("card: PROMOTED requires readback.deployed_sha == candidate_sha and observed_at")
    return f


def run(m, c):
    failures = check_map(m) + check_card(c)
    # a cautious verdict (REJECT / NEEDS_EVIDENCE) over passing evidence is allowed; the reverse is not
    if failures and c.get("verdict") == "KEEP":
        failures.append("verdict KEEP contradicts the evidence above")
    return failures


def main(argv):
    if argv[:1] == ["--self-test"]:
        return self_test()
    if len(argv) != 1:
        print(__doc__)
        return 2
    d = Path(argv[0])
    m = json.loads((d / "responsibility-map.json").read_text(encoding="utf-8"))
    c = json.loads((d / "eval-card.json").read_text(encoding="utf-8"))
    failures = run(m, c)
    print("GATE " + ("PASS" if not failures else "FAIL"))
    for x in failures:
        print("  - " + x)
    return 0 if not failures else 1


def self_test():
    here = Path(__file__).resolve().parent.parent / "templates"
    m = json.loads((here / "responsibility-map.json").read_text(encoding="utf-8"))
    c = json.loads((here / "eval-card.json").read_text(encoding="utf-8"))
    c["graders_sha_at_plan"] = c["graders_sha_at_eval"] = "abc"
    assert run(m, c) == [], run(m, c)

    def mutated(fn):
        mm, cc = json.loads(json.dumps(m)), json.loads(json.dumps(c))
        fn(mm, cc)
        return run(mm, cc)

    def expect(fn, needle):
        out = mutated(fn)
        assert any(needle in x for x in out), (needle, out)

    expect(lambda mm, cc: mm["fields"][1].update(producer_after="jev"), "cannot be owned by jev")
    expect(lambda mm, cc: mm["fields"][0].update(evidence="NONE"), "evidence is missing or NONE")
    expect(lambda mm, cc: mm["fields"][0].pop("consumers"), "no consumers listed")
    expect(lambda mm, cc: mm["case_set"]["planted_controls"].pop("provider_failure_injection"), "missing planted control")
    expect(lambda mm, cc: mm.update(commit_boundary="somewhere in the pipeline"), "path:line")
    expect(lambda mm, cc: cc["arms"]["B"].update(jev_calls=0), "unwired mechanism")
    expect(lambda mm, cc: cc["arms"]["A"].update(jev_calls=3), "contaminated baseline")
    expect(lambda mm, cc: cc["arms"]["C"].update(critical_errors=9), "above ceiling")
    expect(lambda mm, cc: cc["arms"]["C"].update(fallback_rate=0.9), "hiding a weak candidate")
    expect(lambda mm, cc: cc["arms"]["C"].update(downstream_field_integrity=0.98), "integrity below 1.0")
    expect(lambda mm, cc: cc.update(graders_sha_at_eval="zzz"), "weakened check")
    expect(lambda mm, cc: cc.update(run_ids=[]), "stale or unobserved")
    expect(lambda mm, cc: cc.update(status="QUALIFIED_CANDIDATE"), "requires candidate_sha")
    expect(lambda mm, cc: cc.update(status="PROMOTED", candidate_sha="s1", dataset_snapshot="d", readback={"deployed_sha": "s2", "observed_at": "t"}), "PROMOTED requires readback")
    expect(lambda mm, cc: (cc["arms"]["B"].update(jev_calls=0), cc.update(verdict="KEEP")), "contradicts the evidence")
    small = mutated(lambda mm, cc: (cc.update(n_available=12, all_available_used=True), [a.update(n=12, critical_errors=0) for a in cc["arms"].values()]))
    assert small == [], small
    print("self-test OK: 1 good packet passes, 15 mutations fail for the stated reason, thin-but-complete set accepted")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

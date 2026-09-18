# WORK and JUDGE: three arms, live, re-run

Alignment cannot be judged by reading the diff. The swap is executed against the frozen
case set through the real entrypoint, and the numbers are written by the runner, not by
an agent. Then someone who did not build it runs it again.

## The three arms

| Arm | What runs | Why it exists |
| --- | --- | --- |
| A | Original only, `JEV_SWAP_MODE=original` | The supported baseline. Zero Jev calls, or the arm is contaminated. |
| B | Jev only, raw, `JEV_SWAP_MODE=jev`, no threshold, no fallback | The candidate's true quality and calibration |
| C | Jev with the threshold policy and the original as fallback, `JEV_SWAP_MODE=cascade` | What production would run |

Reporting C alone is how a weak candidate ships: a hybrid that falls back on 90% of cases
looks exactly like the original. Reporting B alone is how a good candidate gets rejected for
an unrepresentative slice. Report all three, every round.

## Two comparison modes, three levels

Modes, both required:

- **Isolated**: the same intermediate input into the old component and the Jev component.
  Answers "did this component improve".
- **End-to-end**: each pipeline runs on its own upstream outputs through the real entrypoint.
  Answers "did the customer-visible outcome improve".

Levels, all three checked in the end-to-end mode:

1. **Properties and boundaries**: actual provider calls observed, contracts valid, mapped
   fields propagate, data-release scope respected, fallback fired before the commit on the
   injected failure.
2. **Each logical component**: correct decision, abstention where expected, errors, against
   the approved component expectations.
3. **The whole case**: final output correctness, citation or evidence integrity, missing
   requirements, trajectory, end-to-end latency and total cost including fallback calls.

## Metrics

| Metric | Arms | Gate |
| --- | --- | --- |
| Agreement with labels (or with A where no labels exist) | B, C | at or above the plan's target |
| Critical-error rate (the harmful wrong decision the plan named) | A, B, C | C at or below the approved ceiling, and never above A |
| Coverage (share decided by Jev) against accepted-case error | C | plotted across thresholds; the policy threshold is read off the curve, not chosen by hand |
| Calibration (raw probability against outcome, by bucket) | B | reported; a flat curve means confidence cannot route |
| Fallback rate and reasons (`timeout`, `429`, `contract`, `abstain`, `breaker`) | C | below the ceiling; every reason counted |
| Latency p50 and p95, including fallback | A, C | C at or below A, or the plan justifies the difference |
| Cost per successful correct workflow, including failed attempts and fallback calls | A, C | C below A |
| Per-slice results | all | no slice regresses past the ceiling |
| Downstream field integrity: every mapped field equals its expectation or satisfies its invariant | C, end-to-end | 100%, or REJECT |

Retain raw probabilities and the policy version next to every decision. A rounded label in
the card with no probability behind it is a number nobody can re-derive.

## The eval card

`templates/eval-card.json`. Written by the runner from its own events: run ids, counts,
call counts per arm, timings, costs, per-case results, fallback reasons. An HTML or
Markdown rendering is generated from the same records. Mark every case as executed,
cached, failed, skipped, or unverified. Never fabricate a missing case.

## The judge protocol

Fresh context. Not the planner, not a worker. The report is a set of claims; the judge
re-runs the claimed verifications. Four hunts, in the order they bite:

1. **Unwired mechanism.** Count Jev calls per arm from the runner's events. B and C with zero
   calls means the swap never ran. A with any calls means contamination. Confirm the eval
   hit the real entrypoint, not a helper.
2. **Weakened check.** Hash graders, thresholds, answer keys, fixtures and the original path;
   compare to the plan. A changed threshold is a new policy version and a new eval, not a fix.
   A changed expected value is a defect unless it traces to a spec or a measurement, with the
   old value kept in a comment.
3. **Stale measurement.** Every number in the card has a run id, and the run is newer than the
   candidate sha. A number from before the last edit is not evidence for the edit.
4. **Reasoned-about versus observed.** Re-run the three arms, or a fixed random sample of them
   when the budget is bounded, and compare to the card. Re-run the previous round's attacks;
   do not read the diff and nod.

Verify the verifier before trusting it: a known-good case passes; the Jev path disconnected
fails; a hardcoded lookup of the answer key fails on unseen cases; an edit to a grader is
rejected. A deterministic solution that genuinely satisfies the contract is legitimate. Do
not require the candidate to look sophisticated.

Then run `python scripts/gate.py swap/<component>`. The gate failing and the verdict saying
KEEP is a defect in the verdict.

## Verdicts

Per round, exactly one, with one next action:

- **KEEP**: all gates pass on this round's evidence. The candidate advances.
- **REJECT**: a critical failure, a planted control passed, integrity under 100%, fallback over
  the ceiling, or a weakened check. Name the mechanism. The same mechanism twice escalates
  diagnosis instead of a third attempt.
- **NEEDS_EVIDENCE**: the claim may be true but was not observed. Say what run would show it.

Campaign status:

- **IN_PROGRESS**
- **QUALIFIED_CANDIDATE**: the declared qualification is met, with exact versions recorded:
  candidate sha, Jev model id, threshold policy version, dataset snapshot, rubric version.
  Ready for human review or authorized deploy. Not promoted.
- **PROMOTED**: after an authorized deploy and a readback that the deployed version is the
  candidate sha. The readback is fetched from the running system, not from local state.
- **BLOCKED**: mandatory evidence is missing. Never rendered as PASS.

Keep the best-supported candidate, not the newest.

## Human handoff

When the automated gates pass and domain truth is still open, publish through the existing
review surfaces rather than declaring a result:

- An annotation queue item per review-ready candidate, carrying baseline references, the
  judge's results and the eval card. Passing automated review means ready for review, not
  ready for production.
- Pairwise items: one per case and comparable logical component, plus one final-output pair
  per case. Randomize left and right. Hide the provider identity and the automated verdicts
  during the preference judgment. Offer left, right, tie, both wrong, insufficient information.
  Mark split, removed, or added components explicitly rather than pairing by position.
- One comparison identity across both systems: case and component, baseline and candidate
  code and model versions, spec and dataset snapshot, rubric version, run and observation ids.
- Read back the published item counts and ids. Deduplicate publishing retries. Capture one
  component pair, one final pair, and one queue item as proof.

Deterministic correctness and human preference are reported separately. New domain
uncertainty goes to triage, not to a green result.

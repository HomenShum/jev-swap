# PLAN: shape, questions, fallback, eval design

The Planner writes `swap-plan.md` (`templates/swap-plan.md`) from the responsibility map.
No worker starts until the plan names the falsifier and the budget.

## The five shapes

| Shape | Pick when | Jev owns | Code or the original owns |
| --- | --- | --- | --- |
| KEEP | The job is generation, arithmetic, dates, exact extraction, or multi-hop; or no case set can be built; or the baseline is already cheap and correct | nothing | everything |
| REPLACE | The whole contract is one bounded decision and every output field maps to a Jev answer or to deterministic code | the decision | validation, derived fields, side effects, the commit |
| SPLIT | The component decides and also explains or generates | the decision | the original model keeps the explanation or new text; code merges the two into the old contract |
| CASCADE | Decision quality is uneven across slices or confidence; the original stays for the rest | cases above the threshold policy | cases below it, abstentions, and every provider failure go to the original |
| VERIFY | The component generates, and Jev can screen the output (citation support, policy compliance, schema sanity) | the screen | the original stays the source of truth; a failed screen routes to fallback or a human |

Most real swaps are SPLIT or CASCADE. A plan that says REPLACE for a component with more than
one output field of kind `decision` should be re-read.

## Question design

Written against `JEV-CONTRACT.md`, section "Jaggedness".

- One decision, asked one way. Do not ask the same thing as a Noul and as a yes/no Choice and
  expect the numbers to agree. Do not add P(x) and P(not x) and expect 1.
- Criteria extend the instructions. Describe each option, including what it is *not* for,
  and add short examples when two options are confusable.
- Add an explicit abstain option (`none_of_these`, `escalate`, `insufficient_information`)
  to any Choice whose correct answer might be absent from the offered set.
- Filter the state in code first and name the relevant parts. Stay under 32k tokens of state.
- Fan out: put every question the workflow needs, including branch-specific ones, in one
  request; decide relevance in code afterwards.
- Score: 2 to 10 ordered levels. Threshold on the expectation; never read a magnitude off it.
- Anything numeric, dated, or exact is computed in code and passed in as a named bucket.
- Pin `jev-1.13.0` (or the current release id), never the `jev-latest` alias, and record the
  id with every answer.

## Fallback design

The fallback is not a `catch`. It is a policy with a version.

```
JEV_SWAP_MODE = original | shadow | cascade | jev        default: original, per component
```

- **original**: the unmodified path. Byte-for-byte the code that ran before the swap.
- **shadow**: call both, serve the original, log the pair with the raw answer. The first
  live arm, and it must have zero consumer impact.
- **cascade**: serve Jev when the threshold policy accepts; otherwise serve the original.
- **jev**: Jev-only. An evaluation arm, never a production default before PROMOTED.

The decision boundary returns one record and nothing else acts on Jev's answer:

```
{ decision, source: "jev" | "original", raw_answer, jev_model, policy_version, fallback_reason | null }
```

Rules the boundary enforces:

1. **Contract validation on every answer.** Type matches the question, `choice` is one of the
   offered options, probabilities sum to about 1, `score` is inside the legend range. Any
   violation is a fallback with reason `contract`.
2. **Threshold policy is versioned data**: `{ version, primitive, field, threshold,
   evaluated_on: <dataset snapshot> }`. Changing a threshold is a new version and a new eval.
3. **Deadline per call.** Start at half the original's p95 budget or a hard 2 s; a timeout is a
   fallback with reason `timeout`.
4. **Circuit breaker.** N failures (`429`, `529`, timeout, contract) inside a window flips the
   component to original-only for a cooldown. Reason `breaker`.
5. **Abstain routes.** The abstain option winning, or confidence under the policy, is reason
   `abstain` (CASCADE) or a human item (VERIFY).
6. **Fallback before the first irreversible write.** The commit stage runs after the boundary
   and reads `source`. After a commit, recovery is the existing idempotency or receipt path.
   Re-running the original after a write is how a submission gets sent twice.
7. **Drift trigger in production.** Fallback rate or disagreement rate above the plan's ceiling
   flips the mode to original and alerts. Confidence alone cannot find a confident mistake;
   sampled audits and the independent checks in `EVAL.md` can.

## Eval design, written before WORK

Copy this block into the plan and fill every line. If the experiment cannot distinguish
"Jev is better" from "the threshold hid the failures", redesign it before spending budget.

```
Failed requirement or decision-critical uncertainty:
Baseline identity:      code sha, model, prompt version, threshold (if any)
Candidate identity:     code sha, jev model id, threshold policy version
Dataset snapshot:       hash, n, slices, planted controls present (1-5)
Evaluator identity:     rubric version, judge model, grader file hashes
Evidence and suspected mechanism:
Smallest proposed change:
Expected benefit:       metric, direction, size
Falsifier:              the observation that would make us keep the original
Critical-error ceiling: <rate>, approved by <who>
Fallback-rate ceiling:  <rate>
Protected invariants:   the fields in the map that must not change
Protected files:        graders, thresholds, answer keys, fixtures, original path, with hashes
Authorized scope:       files workers may edit
Budget:                 calls, dollars, wall-clock, rounds
```

If Jev only replaces a judge or evaluator, this is a judge-calibration experiment: rescore
identical frozen outputs and compare to the existing judge. It is not evidence that the
pipeline improved, and the plan says so.

## Worked example: citation support

Existing component: an LLM reads a claim and a source section and returns
`{ label, quote, offsets, explanation }`, and downstream turns the citation green.

| Responsibility | Owner after the swap |
| --- | --- |
| Locate the quote in the source, offsets | Code, string match. A missing quote is `fabricated` without a model call |
| Supports / contradicts / says nothing | Jev, one Choice with three described options |
| The explanation shown to the reviewer | The original model (SPLIT) or dropped if no consumer reads it (the map says which) |
| Source id, version, deep link | Existing data |
| The green state and the write | Code, after the boundary, reading `source` |

Shape: SPLIT with CASCADE on confidence. Critical error: a false `supports`. The falsifier:
the false-support rate in arm C exceeds arm A's on the frozen set, or any planted control
passes. That is the swap; the label was never the hard part.

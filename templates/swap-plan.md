# Swap plan: <component>

Map: `swap/<component>/responsibility-map.json` (sha256: `<hash>`)

## Shape

`KEEP | REPLACE | SPLIT | CASCADE | VERIFY` — one line on why, citing the map fields that
forced it.

## Ownership after the swap

| Field | Producer after | Note |
| --- | --- | --- |
| label | jev | Choice, three options plus abstain |
| quote, offsets | code | string match; fabricated without a model call |
| explanation | original | SPLIT; consumer at `<path:line>` still reads it |
| confidence | jev | raw probabilities retained; policy v1 |

## Jev questions

```json
{
  "model": "jev-1.13.0",
  "state": { "claim": "<filtered>", "section": "<filtered>" },
  "questions": {
    "relation": {
      "type": "choice",
      "instructions": "How does the section relate to the claim?",
      "criteria": {
        "supports": "States the claim or directly implies it is true",
        "contradicts": "States the opposite or implies the claim is false",
        "says_nothing": "Does not address what the claim asserts, either way"
      }
    }
  }
}
```

Jaggedness check: one decision asked one way; criteria extend the instructions; state is
filtered to the two fields; nothing numeric, dated, exact, or generative is asked.

## Fallback policy

- Switch: `JEV_SWAP_MODE`, default `original`.
- Threshold policy: `{ version: "v1", primitive: "choice", field: "confidence", threshold: <from the coverage curve>, evaluated_on: "<snapshot>" }`
- Deadline: `<ms>`. Breaker: `<N>` failures in `<window>` flips to original for `<cooldown>`.
- Commit boundary: `<path:line>`; the boundary returns `{ decision, source, raw_answer, jev_model, policy_version, fallback_reason }` and the commit reads `source`.
- Drift trigger: fallback rate or disagreement rate above `<ceiling>` in production flips to original and alerts.

## Eval design

```
Failed requirement or decision-critical uncertainty:
Baseline identity:      sha <..>, model <..>, prompt v<..>
Candidate identity:     sha <..>, jev-1.13.0, policy v1
Dataset snapshot:       sha256:<..>, n=<..>, slices <..>, controls 1-5 present
Evaluator identity:     rubric v<..>, judge model <..>, grader hashes <..>
Evidence and suspected mechanism:
Smallest proposed change:
Expected benefit:       <metric>, <direction>, <size>
Falsifier:              <the observation that keeps the original>
Critical-error ceiling: <rate>, approved by <who>
Fallback-rate ceiling:  <rate>
Protected invariants:   <map fields>
Protected files:        <path> <sha256> ...
Authorized scope:       <files workers may edit>
Budget:                 <calls> / <usd> / <wall-clock> / <rounds>
```

## Worker packets

Links to the packets issued from `templates/worker-packet.md`, one per bounded task.

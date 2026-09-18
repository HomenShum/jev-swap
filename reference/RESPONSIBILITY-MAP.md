# GRASP and GATHER: the responsibility map

The investigation exists because the output schema lies by omission. This file says what
to trace, what the map must contain, and what the case set must contain before a plan is
allowed.

## GRASP (Planner, strong model, no code changes)

Write four lines and stop:

```
Claim:        <Component> turns <input> into <decision> so that <consumers> can <do what>.
Not its job:  <explanation text> / <exact values> / <ids and links> / <writes> / <...>
Class:        classifier | router | ranker | selector | verifier | judge | generator
Primitive:    Choice (one of a fixed set) | Noul (yes/no) | Score (position on levels) | none
```

Early KEEP, no further work, when the claim needs "and then explains", "and computes",
"and extracts the", or "and writes" to be true, and the decision cannot be separated on
paper. Record the KEEP in `verdict.md` with the sentence that killed it. A KEEP that took
ten minutes is a good outcome.

## GATHER (Workers fan out, Planner consolidates)

One worker packet per row. Each returns paths with line numbers and quoted code, never a
paraphrase. The Planner merges into `responsibility-map.json`.

| Trace target | What the worker returns |
| --- | --- |
| Callers | Every call site, `path:line`, and how each consumes the result |
| Context construction | What goes into the prompt or state today, what is filtered, what is implicit (system prompt, few-shot, retrieved docs, prior turns) |
| Parser and defaults | How the model output is parsed, what happens on parse failure, defaults, retries, the value consumers see when the call is skipped |
| Output contract | Every field, type, nullable, enum members, where each is derived |
| Derived values | Fields computed downstream from this output (`is_supported = label in {...}`, aggregated scores, sort keys) |
| Side effects | Cache writes and their keys, DB writes, queue publishes, emitted events, metrics, traces, UI state transitions |
| Commit boundary | The first irreversible write reachable from this output, with the path to it |
| Existing safeguards | Timeouts, retries, circuit breakers, feature flags, rate-limit handling already present |
| Tests and fixtures | Unit, integration, eval sets, golden files; which assert on this component's output and how |
| Live entrypoint and data scope | The real CLI, API, or job that exercises the component end to end; the authorized data path; whether sending this state to a new provider is approved |
| Baselines | From traces: accuracy or agreement if labels exist, p50 and p95 latency, cost per call, failure and fallback rate, volume |
| Ownership | Who approves changes here; where answer keys come from; which keys are unresolved |

Workers read. They do not propose the migration. A worker that returns "this looks like a
simple classifier, safe to swap" has left its packet.

## The map

`templates/responsibility-map.json` is the shape. The rules the gate enforces:

- Every output field has `producer_now`, `producer_after` in `jev | code | original | removed`,
  `consumers` (a list of `path:line`, or an explicit `consumers_verified_empty: true`),
  a non-empty `invariant`, and non-empty `evidence` that is not `NONE`.
- Every field has a `kind`: `decision | arithmetic | date | exact_string | identifier |
  generation | rendering | side_effect | other`. A field with `producer_after: jev` and any
  kind other than `decision` fails the gate. That is the jaggedness table applied per field.
- `commit_boundary` is a path, not a sentence.
- `data_release_scope` says whether the state may leave for a new provider, and who said so.

A field whose producer-after you cannot name is a field the swap will silently drop.
The map is done when a reader can answer, for every field: who makes it after the swap,
who reads it, what must stay true about it, and where that is checked.

## The case set

Frozen before PLAN, identified by a snapshot hash in the plan and the eval card.

- Size: 30 cases minimum for a pilot. If fewer exist, use all of them and say so in the
  card (`all_available_used: true`); the gate accepts that, a judge should still call it thin.
- Slices: whatever the baselines showed matters (tenant, language, length, source type).
  Report per slice.
- Labels: from existing answer keys only. Unresolved keys stay unresolved and route to human
  triage. Nothing is auto-gold, and nothing is labelled by Jev.
- Five planted controls, always present:
  1. A confidently wrong decision with a known label, to prove that type-valid is not correct.
  2. An out-of-set case whose right option is absent, to prove the abstain path.
  3. An adversarial state containing instructions, to prove contract validation holds.
  4. A large state full of irrelevant detail, to prove the filter step.
  5. A provider failure injection (`429`, timeout) to prove the fallback fires before the commit.

If a control cannot be built, the plan says which one and why, and the judge treats the
missing proof as BLOCKED for that gate.

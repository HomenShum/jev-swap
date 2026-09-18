---
name: jev-swap
description: Investigate, then swap a System 2 pipeline component (an LLM call or agent step that classifies, routes, ranks, selects, screens, or judges) for a System 1 TypeSafe Jev decision (Choice / Score / Noul) without breaking what depended on it. Traces the component's real responsibility and every downstream field first, picks a migration shape (KEEP / REPLACE / SPLIT / CASCADE / VERIFY), keeps the original pipeline as a live fallback, runs the swap through cheaper worker subagents, and promotes only on paired live evaluation re-run by an independent judge. Use for "swap this to Jev", "System 2 to System 1", "make this decision typed / faster / cheaper", TypeSafe AI adoption, or gating an agent harness's self-improvement loop.
---

# jev-swap

**A swap is a claim, not a result.** A component that returns `{label: "supported"}`
also owned things its schema never mentions: which source it cited, the exact quote and
offsets, the explanation shown to the user, the cache key, the row it wrote, the UI state
that turned green. Replace the LLM call with a typed decision that returns a valid label
and every one of those can break while every type check passes.

So this skill never starts at the swap. It starts at the responsibility, keeps the original
pipeline alive as the fallback, and only believes a result that was executed live and
re-run by someone who did not build it.

**Preserve the component's responsibility, not merely its response schema.**

## When to use, when to KEEP

Use it when the component's job is a **bounded decision over text or structured state**:
intent routing, taxonomy labels, passage relevance, claim-vs-evidence support, tool or
skill selection from a registry, UI panel selection, severity, trace-failure tagging,
review prioritization, browser operation/target selection.

Do not swap (verdict KEEP, decided in phase 1) when the job is **generation, arithmetic,
date or time comparison, exact extraction of novel strings, or multi-hop reasoning**.
Those are Jev's documented weak spots. See `reference/JEV-CONTRACT.md`, section
"Jaggedness". A generative model or plain code stays the owner; Jev may still *screen*
that output (shape VERIFY).

## The loop

```
GRASP ──> GATHER ──> PLAN ──> WORK ──> JUDGE ──> (repair, or hand off)
 name     trace      shape    swap +   re-run
 the      every      fall-    3 arms   never
 job      consumer   back     live     read
```

| Phase | Who | Model tier | Deliverable | Reference |
| --- | --- | --- | --- | --- |
| 1 GRASP | Planner | strong | One-sentence responsibility claim, component class, candidate primitive, or an early KEEP | `reference/RESPONSIBILITY-MAP.md` |
| 2 GATHER | Workers fan out, Planner consolidates | cheap workers, strong consolidation | `responsibility-map.json`: every output field with producer now / producer after / consumers / invariant / evidence; the case set with planted controls | `reference/RESPONSIBILITY-MAP.md` |
| 3 PLAN | Planner | strong | `swap-plan.md`: shape, Jev questions, fallback policy, protected files, eval design with falsifier and budget | `reference/MIGRATION-SHAPES.md` |
| 4 WORK | Workers | cheap | Adapter + fallback wired behind a switch, three arms executed live, `eval-card.json` generated from runner events | `reference/EVAL.md` |
| 5 JUDGE | Judge, fresh context | strong | KEEP / REJECT / NEEDS_EVIDENCE plus one next action; at campaign end QUALIFIED_CANDIDATE or BLOCKED | `reference/EVAL.md` |

Phase 1 is where most swaps should die. If the responsibility claim contains "and then
explains", "and computes", "and extracts the", or "and writes", the component is not one
decision. Split it on paper before anyone touches code.

### 1. GRASP

Write the claim: *Component X turns `<input>` into `<decision>` so that `<consumers>` can
`<do what>`. It is not responsible for `<list>`.* Classify it (classifier, router, ranker,
selector, verifier, judge, generator). Name the primitive: Choice for one of a fixed set,
Noul for a yes/no, Score for a position on described levels. A generator is KEEP.

### 2. GATHER

Fan out cheap workers with bounded packets (`templates/worker-packet.md`), one per trace
target: callers, context construction, parser and defaults, output contract, derived
values, side effects, commit boundary, existing safeguards, tests and fixtures, live
entrypoint and data-release scope, baselines from traces. The Planner consolidates into
the map. A field whose producer-after is unknown, or whose evidence is `NONE`, blocks
phase 3. So does a case set without the five planted controls.

### 3. PLAN

Pick the shape from the table in `reference/MIGRATION-SHAPES.md`. Write the questions
against the jaggedness rules. Design the fallback so it fires **before** the first
irreversible write. Write the eval design before any worker starts: what would falsify
the swap, what the critical-error ceiling is, what the budget is. Hash the protected
files (graders, thresholds, answer keys, fixtures, the original path) into the plan.

### 4. WORK

Workers implement behind `JEV_SWAP_MODE = original | shadow | cascade | jev`, default
`original`. Shadow first: call both, serve the original, log the pair. Then run the three
arms on the frozen case set through the **real entrypoint**. The eval card is written by
the runner from its own events. A reporting agent never types a number into it.

### 5. JUDGE

A fresh-context judge re-runs the claimed commands, counts Jev calls per arm, diffs the
protected hashes, checks every number has a run id newer than the candidate, and re-runs
the previous round's attacks. Then `python scripts/gate.py swap/<component>` must pass
before any verdict is written. Where `fable-judge` is installed, run it here.

## Roles and cost routing

- **Planner** (strong model). Owns the map, the plan, the protected list, consolidation,
  and difficult diagnosis. Never implements. Never grades its own plan.
- **Workers** (cheaper models: spawn with the Agent tool and `model: "sonnet"` or
  `"haiku"`, or the project's equivalent). Bounded tasks from a written packet: files
  allowed, files forbidden, expected output, budget. They may edit candidate code and the
  adapter. They may never edit graders, thresholds, answer keys, fixture expectations, the
  eval runner's scoring, or the original pipeline's code path. They report with paths and
  command output, not summaries.
- **Judge** (strong model, fresh context, not the planner and not a worker). Re-runs, never
  reads. Owns the verdict.
- Optional when stakes are high: an **HRE** reviewer that attacks the causal story
  ("Jev improved it" vs "the threshold hid the failures") and a **Steward** that audits
  conventions, permissions and data-release scope. All reviewers inspect the same
  candidate snapshot. No vote or average overrides a critical failure.

Never poll workers with premium turns. Never paste the whole conversation into a worker.
Never repeat an unchanged review. Measure total cost per qualified outcome, including
failed attempts and fallback calls.

## Hard gates

1. **No plan without a complete responsibility map.** Every output field has a producer
   after the swap and evidence for its invariant.
2. **Jev decides; code owns the rest.** Arithmetic, dates, identifiers, exact quotes and
   offsets, rendering, permissions and the commit stay in code. Generation stays with a
   generative model.
3. **The original stays callable and unmodified** behind the switch. Default is original
   until PROMOTED.
4. **Fallback before the first irreversible write.** After a commit, recovery is the
   existing idempotency or receipt path, never a blind re-run of the original.
5. **Three arms, always**: A original-only, B Jev-only (raw), C Jev-with-fallback. Both
   isolated (same intermediate input) and end-to-end (each pipeline's own upstream output).
   A hybrid alone can hide a weak candidate or a system that falls back on every case.
6. **Raw probabilities and a versioned threshold policy are retained.** Never silently
   round Jev output into an existing rubric. The independent judge's scores stay separate
   from Jev's own predictions.
7. **Workers cannot touch the proof.** The judge re-runs, never reads.
8. **Missing evidence is BLOCKED, never PASS.** QUALIFIED_CANDIDATE carries exact
   versions: candidate sha, Jev model id, threshold policy version, dataset snapshot,
   rubric version. PROMOTED only after an authorized deploy and a readback of the intended
   version.

## Stop rules

- Reproducible defect with a repair inside budget: continue.
- The same mechanism fails twice: escalate diagnosis, do not repeat.
- Candidate meets the declared qualification: stop the cycle and hand off.
- B and C are indistinguishable from A: keep A, the supported baseline, and say so.
- Fallback rate in C above the plan's ceiling: REJECT. The hybrid is hiding a weak candidate.
- Unknown domain truth: a human decision through the annotation queue, never a green.
- Budget or safety boundary: persist state, pause, report.

Keep the best-supported candidate, not the newest.

## Output packet

```
swap/<component>/
  responsibility-map.json   templates/responsibility-map.json
  swap-plan.md              templates/swap-plan.md
  eval-card.json            templates/eval-card.json, written by the runner
  verdict.md                judge's verdict, one next action, exact versions
```

`python scripts/gate.py swap/<component>` enforces mechanically what a script can: gate 1,
gate 2, the three-arms-wired half of gate 5 plus the presence of both comparison modes, the
protected-files half of gate 7, and gate 8. It also refuses a card that still carries the
template's illustrative numbers. Whether the judge re-ran instead of read is the judge's
own record, not the script's. A verdict written while the gate fails is a defect in the
verdict, not in the gate.

## Inside an agent harness

Jev can screen candidate patches, rank experiments, choose tools or skills from an
authorized registry with an explicit abstain option, and tag trace failures. That makes
the inner loop faster. It does not make it trustworthy on its own: Jev must never be the
sole evaluator of changes it helped select, and holdouts, labels, thresholds, permissions
and promotion criteria stay outside the optimizing loop. Same five phases, same gates.

## Reference

- `reference/JEV-CONTRACT.md` — the API as documented on 2026-09-18: endpoint, primitives, answer fields, limits, jaggedness table
- `reference/RESPONSIBILITY-MAP.md` — GRASP and GATHER: what to trace, the map schema, the case set
- `reference/MIGRATION-SHAPES.md` — PLAN: the five shapes, question design, fallback design, eval design
- `reference/EVAL.md` — WORK and JUDGE: three arms, metrics, judge protocol, verdicts, human handoff
- `templates/` — responsibility map, swap plan, eval card, worker packet
- `scripts/gate.py` — the mechanical gate, stdlib only, `--self-test` included

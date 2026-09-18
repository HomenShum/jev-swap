# Worker packet: <task id>

Issued by: Planner, round <n>. Model tier: cheap (sonnet / haiku or equivalent).
Budget: <turns> turns, <minutes> minutes. Stop and report when either runs out.

## Task

One bounded thing. Examples: "trace every caller of `checkSupport` and return path:line
plus the consuming expression", "implement the decision boundary in `src/citations/jev.ts`
against the plan's question JSON", "run arm B on snapshot `<hash>` through `<entrypoint>`
and return the runner's event log path".

## Files you may edit

- `<path>`
- `<path>`

## Files you may not touch

Graders, thresholds, answer keys, fixture expectations, the eval runner's scoring, the
original pipeline's code path, and anything not listed above. If the task cannot be done
without touching one of these, stop and report that. Do not work around it.

## Context you need

The plan section `<..>` and the map fields `<..>`. Nothing else is attached on purpose;
ask for a specific file if you need it.

## Return format

- Paths with line numbers and quoted code, never paraphrase.
- Commands you ran, verbatim, with their output.
- What you did not do, and why.
- No recommendation about whether the swap is a good idea. That is not this packet.

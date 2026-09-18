# The Jev contract, as documented on 2026-09-18

Everything here was read from docs.typesafe.ai on 2026-09-18, except where a different
source is named inline. Re-verify before quoting a number onward; the docs warn that limits
change. Pin the model id in every swap plan and record it with every answer.

## Endpoint

```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

Request: `{ "state": string | object | array, "model": string, "questions": { <id>: Question } }`.
Response: `{ "model": string, "answers": { <id>: Answer }, "usage": { "input_tokens", "output_tokens" } }`.

You choose the question ids. The model never sees them. Every question is evaluated
against the same `state`, in parallel, in one round trip.

## Models

| Model | Id | Notes |
| --- | --- | --- |
| Jev 1.13 | `jev-1.13.0` | Current release. `jev-latest` is an alias; do not pin an alias in a swap plan. |

- Price: $0.042 per million input tokens. Output tokens are free.
- Rate limits: 250,000 tokens per second, 1,200 requests per minute. Over either returns `429`.
- Context: 64k tokens per request; 32k for `state` plus the longest question.
- Input: text only. String, JSON object, or array of text values. No image, audio, or video.
  Browser and UI work therefore needs a DOM or accessibility snapshot, not a screenshot.

## Primitives and answer fields

| Primitive | Question | Answer | Read it as |
| --- | --- | --- | --- |
| Choice | `type: "choice"`, `instructions`, `criteria: { option: description }` | `choice`, `confidence`, `probabilities: { option: p }` | One of a fixed set. The distribution compares options; it does not invent a missing one. |
| Score | `type: "score"`, `instructions`, `criteria: [level, ...]` (2 to 10 ordered levels) | `score` (fractional expectation), `confidence`, `legend`, `probabilities: { "0": p, ... }` | A position on described levels. Use the expectation to test a threshold, never to reconstruct a magnitude. |
| Noul | `type: "noul"`, `instructions`, optional `criteria: { true, false }` | `noul` (probability of yes) | Whether a condition holds. No separate confidence. 0.5 means yes and no are equally likely, not "medium". A low value can be a strong no. |

`confidence` on Choice and Score summarizes how concentrated the distribution is. It is not
workflow correctness and not permission to act. Thresholds are chosen on your own cases
and consequences (see `EVAL.md`, the coverage-vs-error curve), never copied from a cookbook.

Errors: `401` bad key, `422` malformed question (body names the field), `429` rate limit,
`529` overloaded. Retry `429` and `529` with exponential backoff; the SDKs do this by default
and honor `retry-after`.

## SDKs

Python, `pip install typesafe-sdk`, env `TYPESAFE_API_KEY`:

```python
from typesafe_sdk import TypeSafeClient, Choice, Noul, Score

with TypeSafeClient() as client:
    r = client.system_one(
        model="jev-1.13.0",
        state={"claim": claim, "section": section},
        questions={
            "relation": Choice(
                instructions="How does the section relate to the claim?",
                criteria={
                    "supports": "States the claim or directly implies it is true",
                    "contradicts": "States the opposite or implies the claim is false",
                    "says_nothing": "Does not address what the claim asserts, either way",
                },
            ),
        },
    )
    a = r.answers["relation"]          # a.choice, a.confidence, a.probabilities
```

JavaScript / TypeScript, `npm install @typesafe-ai/sdk` (Node 20+):

```ts
import { choice, TypeSafeClient } from "@typesafe-ai/sdk";
const client = new TypeSafeClient();
const r = await client.systemOne({
  model: "jev-1.13.0",
  state: { document },
  questions: { category: choice("What is this ticket about?", { billing: null, technical: null, other: null }) },
});
r.answers.category.choice;
```

## Fan-out

Many questions cost no extra latency in one request. Ask every question the workflow might
need, including branch-specific ones, then let code decide which answers matter. Prefer one
speculative request over a chain of dependent ones. Not from the TypeSafe docs: the
browser-use `jev-ultrafast` agent (github.com/browser-use/jev-ultrafast, README as read
2026-09-18) does exactly this: operation plus one target head per operation type in a single
call, and a small LLM only writes text when the chosen operation is `TYPE_TEXT`.

## Jaggedness (jev-1.13, page reviewed 2026-09-17)

These are the documented failure modes. In PLAN, every responsibility in the map is checked
against this table; a match means code or the original model owns it, not Jev.

| # | Failure mode | Owner after the swap |
| --- | --- | --- |
| 1 | Literal reading: scoping words, negations, implied conditions are read at face value | Jev, but write the exact condition and criteria per option; split compound questions into literal ones and combine in code |
| 2 | Math and numbers: not a calculator; weak numeric calibration; hex and RGB worse than names | Code does the arithmetic and passes the computed number or a named bucket |
| 3 | Date and time comparison: dates are read as text, not ordered quantities | Code extracts components and compares; Jev may judge the semantics of a labelled result |
| 4 | Indirection: a property of a property, multi-hop reasoning | Reduce hops; point to the relevant part of state by name; else the original model |
| 5 | Large state full of irrelevant detail | Filter in code first; send only what the question needs |
| 6 | Adversarial content: instructions inside the state | Precise prompts, planted adversarial cases in the eval set, contract validation on every answer |
| 7 | Contradictory instructions and criteria | Criteria are an extension of the instructions; align them; a Noul where true means no performs worse |
| 8 | Structural invariants are not guaranteed: the same question as Noul and as yes/no Choice gives different numbers; P(x) + P(not x) need not be 1 | Ask each decision one way; enforce identities in code; never combine two phrasings as if they agreed |
| 9 | Generation | A generative model. Jev selects, screens, or rates; it does not write |

Two consequences the map must carry: an exact quote, an offset, an id, a date, a number, or
a sentence of explanation is never a Jev output field. And a Choice whose correct answer may
be absent from the options needs an explicit abstain option (`none_of_these`, `escalate`),
because Jev picks among what it is offered.

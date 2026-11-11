---
name: ui-eval
description: Run the blind, rubric-based UI eval across Alec's personal project. Use to score how the product looks and feels, find the weakest screens, or check whether a UI change made the experience better than its baseline.
---

# UI eval

[docs/development/ui-eval.md](../../../docs/development/ui-eval.md) describes the method, the
fairness rules and the commands. This skill runs a full loop: capture, prepare, a judge panel,
and score.

## 1. Choose the mode and surfaces

- **Score** one build to audit it: one arm, such as `--arm dev`.
- **Compare** a change: a baseline arm from a `dev` checkout and a candidate arm from the branch.
  Use `--only` with the surfaces the change reaches, plus one it does not reach as a control. The
  control should come out `same`.

Pick a run directory, `.worktree/ui-eval/<yyyy-mm-dd>-<topic>`. The CLI refuses a run outside
`.worktree/ui-eval/` and a `--checkout` that isn't a worktree of this repository.

## 2. Capture

Check each driver's preconditions first: `node e2e/drive.ts doctor` for app surfaces,
`vp run stack:doctor` for stack surfaces, and
`node .claude/skills/verify-desktop/doctor.ts` for desktop ones. Build what they need
(see the doc). For a compare run, capture the baseline from its own checkout, with its own builds
and its own stack:

```sh
vp run ui:eval capture .worktree/ui-eval/<run> --arm dev --checkout <dev-worktree> --only <ids>
vp run ui:eval capture .worktree/ui-eval/<run> --arm <branch> --only <ids>
```

A surface that fails to capture is a finding in its own right. Read its evidence, then fix the
environment and capture again in a fresh run directory, or report it as not judged.

## 3. Prepare

```sh
vp run ui:eval prepare .worktree/ui-eval/<run> --compare dev,<branch>
```

It prints the blind packet's path, `<packet>` below. From here on, judges see only the packet.
Never tell a judge the arm labels, the branch, the change or what you expect it to find.

## 4. Judge

The default panel is three judges from two model families: `opus-5.5`, `fable-5.1` and
`gpt-6-astra`. All three have taste of 8 or more. With a smaller budget, drop `fable-5.1`; two
judges is the minimum. Do not use gpt-6.1-sol as a judge: its taste is too low for this.

Read `<packet>/batches.json`. Each batch is a list of item ids, and each judge takes every batch,
each in a fresh session. Run the batches in parallel, and give every judge the same brief, word
for word. Replies go to `<run>/replies/<judge>/<item>.json`.

**Claude judges.** Use one `Agent` call per batch, with `model` set to `opus` or `fable` and
this prompt:

```text
You are a UI judge. Read <packet>/judge-brief.md and <packet>/rubric.md, then judge these items
from <packet>/items/: <ids>. Open every frame-NN.png with Read and its frame-NN.aria.yml. Read
nothing else outside <packet>. Write each item's reply as JSON to
<run>/replies/<judge>/<item>.json, then reply "done" with the ids you wrote.
```

**GPT judge.** Use one `codex exec` per item, attaching its frames in order: a scored item's
`items/<item>/frame-*.png`, or a compared item's `items/<item>/A/frame-*.png` followed by its
`items/<item>/B/frame-*.png`. `-o` writes the reply:

```sh
images=(); for f in <packet>/items/<item>/frame-*.png <packet>/items/<item>/A/frame-*.png \
  <packet>/items/<item>/B/frame-*.png; do [ -f "$f" ] && images+=(-i "$f"); done
codex exec --skip-git-repo-check -m gpt-6-astra -s read-only -C <packet> "${images[@]}" \
  -o <run>/replies/gpt-6-astra/<item>.json \
  "You are a UI judge. Read judge-brief.md and rubric.md, then judge item <item> in items/<item>/. The attached images are its frames in order (for a compared item: all of A, then all of B); read the aria.yml files beside them. Reply with the item's JSON only."
```

Codex runs can be slow. Run them in the background with each one's log under `<run>/logs/`,
and retry one that fails with a 503. If a reply comes back wrapped in a Markdown fence, delete
the fence and nothing else.
Never edit a judge's scores, verdicts or evidence, and never ask a judge again because you
disagree with its answer. Ask again only when the reply is malformed, and say so in the report.

## 5. Score and report

```sh
vp run ui:eval score .worktree/ui-eval/<run>
```

`score` lists every missing or malformed reply. Fix only the malformed ones, as in step 4.
Then read `report.md`:

- Open every frame listed under **Look at these by eye**, and say whether you side with the
  panel.
- Treat a judge with order agreement below 70%, or repeat drift above 1, as noisy, and say so.
- In compare mode, a `worse` surface blocks the change unless the PR explains the trade.

Give the user the table, the reliability notes, the top three fixes for the weakest surfaces and
the run directory. A PR that cites the eval links `report.md` from its `pr-assets` folder, along
with its key screenshots.

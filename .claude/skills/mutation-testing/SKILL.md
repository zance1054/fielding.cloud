---
name: mutation-testing
description: Kill surviving mutants in one source file and open one PR. Use when asked to mutation-test a file, or with no file to take the next one from the queue.
---

# Mutation testing

Mutate one source file with StrykerJS, resolve its survivors, open one PR and log the run. The
terms (mutant, killed, survivor, equivalent mutant, mutation score) are defined in
[mutation testing](../../../docs/development/mutation-testing.md).

`TEST_DATABASE_URL` must point at a reachable Postgres for `mutation:run` and every `vp test` here.
Without it the Postgres suites skip and their mutants show up as fake survivors.

## 1. Run

1. `git status --porcelain` must print nothing. Otherwise stop and report the dirty worktree.
2. `git fetch origin dev`, `git switch --detach origin/dev` and `vp install`.
3. Take the file you were given. Otherwise run `vp run mutation:pick`. Empty output means no work is
   left: stop.
4. `vp run mutation:run <file> --stage before`. A run that reaches 15 minutes
   retries once without static mutants and records that in the summary, so one call can take 30
   minutes. Run it in the background or with a timeout above 30 minutes; most agent shells stop a
   foreground command sooner.
   - It **stops** without a summary when interrupted: there is nothing to log. Run it again with a
     longer timeout. SIGINT or SIGTERM stops Stryker; on Windows a force-kill delivers no signal,
     but the summary is deleted at the start and written only at the end, so an interrupted run
     still writes nothing.
   - It **refuses** without a reachable `TEST_DATABASE_URL`: stop and report the message; there is
     nothing to log.
   - It **aborts** when Stryker fails or times out again, writes no readable report, or covered
     mutants ran zero tests (a stale runner patch): run
     `vp run mutation:log --pr none --stage before`, then stop and report
     the message. The picker skips the file until its content changes.
5. The summary holds `branch`, `commit` (the start commit), `outcome` (score and counts) and
   `survivors`, each with its mutator, location, replacement, the `tests` that ran it and their
   `testFiles`.
6. `gh pr list --head <branch> --state open --json url --jq '.[].url'` with the summary's `branch`.
   A URL means another run owns the file: stop and report it, with nothing to log. Otherwise
   `git switch -C <branch>`, which replaces any stale local branch of that name.

Done when `before.json` exists and you are on the branch.

## 2. Resolve survivors

Take survivors in order until about 20 are resolved; list the rest in the PR as left over the cap.
For each one:

1. **Confirm.** Apply the replacement at its location by hand and run `vp test <testFiles...>` with
   the survivor's `testFiles`. A `NoCoverage` survivor has none: run `vp test`. If a test fails, it
   is a **false survivor**: note the failing test and move on. Revert the mutation either way.
2. **Resolve** a confirmed survivor with the first of these that fits:
   1. **Delete** the code when no behavior depends on it.
   2. **Test** it through the module's public interface. Re-apply the mutation and watch the new
      test go red, then revert.
   3. **Suppress** it on the line above:
      `// Stryker disable next-line <mutator>: <equivalent|browser-only|electron-only>: <reason>`.
      Use `equivalent` only for code that has to stay. Lint rejects any other form.
   4. **Deepening candidate**: only a test of internals could kill it. Change nothing; name the
      survivor and the module seam that would expose it.

Tests follow the file's existing setup. A React test opts into the DOM per file with
`// @vitest-environment happy-dom` as its first line. If happy-dom can't run the component, add
jsdom in the same PR with `pnpm add -D -w --save-exact jsdom`, list it beside happy-dom
under `ignoreDependencies` in `knip.jsonc`, and use `// @vitest-environment jsdom` instead. Electron main-process tests run in Node with Electron mocked
at its seams.

Done when every survivor up to the cap is a false survivor, deleted, tested, suppressed or a
deepening candidate.

## 3. Open the PR

Skip to step 4 when you changed no code.

1. Apply the [PR convention](../../../docs/development/pull-requests.md) to the title and body.
   Use a title such as `<product-area>/<technical-surface>: kill mutants in <file>`.
   Run `vp run verify`, then `git add -A` and `git commit -m "<title>"`.
2. `vp run mutation:run <file> --stage after` for the score after.
   When it aborts, still open the PR; [pr-body.md](pr-body.md) says how to fill the After row.
3. Fill the body from [pr-body.md](pr-body.md) and write it to `reports/mutation/pr-body.md`.
4. Repeat the step 1.6 `gh pr list` check. A URL means another run opened a PR for the file while
   you worked: stop and report it, with nothing to log. Otherwise
   `git push --force -u origin <branch>`. The branch has no open PR, so a stale remote copy holds
   nothing to keep.
5. `gh pr create --base dev --head <branch> --title "<title>" --label mutation-testing --body-file reports/mutation/pr-body.md`.
   It prints the PR URL.

Done when the PR is open with every table filled from your notes and both summaries, and the
description ends with decisions, the current review record and the creation attribution.

## 4. Log

- With a PR: `vp run mutation:log --pr <PR url> --stage after`. It logs the after run,
  completed or aborted.
- Without one: `vp run mutation:log --pr none --stage before`.

The entry records the file's content at that point, and the picker skips the file while
`origin/dev` holds the same content, so a merged PR counts as done. Log every run that got a
summary, including runs that open no PR. Report the deepening candidates of a no-PR run in your
reply.

Done when the command prints the comment URL.

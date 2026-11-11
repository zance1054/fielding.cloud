# Mutation PR body

Fill every section; write "None" in an empty mutation-result section. Mutants are named `<id> <mutator> L<line>`.
Use the [PR convention](../../../docs/development/pull-requests.md) for the title, area fields,
decisions and agent review record, including its wording when no material alternatives were considered.

```markdown
## Area

- Product area: `<area>`
- Technical surface: `<surface>`
- Affected products: `<products>`
- Primary paths: `<file and test paths>`
- Change class: `<class>`
- Stack/base: `dev`

## Why

Mutation run on `<file>` from <start commit>.

## Score

|        | Score | Killed | Survived | No coverage | Ignored |
| ------ | ----- | ------ | -------- | ----------- | ------- |
| Before |       |        |          |             |         |
| After  |       |        |          |             |         |

Static mutants: <included | ignored in the before/after run, which reached 15 minutes>

## Tests added

| Mutant | Test name |
| ------ | --------- |

## Code deleted

| Mutant | Why no behavior depended on it |
| ------ | ------------------------------ |

## Suppressions

### equivalent

| Mutant | Reason |
| ------ | ------ |

### browser-only

| Mutant | Reason |
| ------ | ------ |

### electron-only

| Mutant | Reason |
| ------ | ------ |

## False survivors

| Mutant | `vp test` failure that shows it is killed |
| ------ | ----------------------------------------- |

## Deepening candidates

- <survivors>: <the module seam that would expose them>

## Survivors left over the cap

- <mutant>

## Decisions

- <material choice, why it won and strongest alternative considered>

## Agent review and attribution

Review pending. CodeRabbit reviews after the PR opens.

Created with <model> in <harness>.
```

Use the model and harness the tools report, including contributing agents. Refresh the review
record after pushes and reviews as the PR convention requires.

`<start commit>` is the `commit` in `reports/mutation/before.json`. Killed counts Stryker's `Killed`
and `Timeout`. When the after run aborted, its row reads `aborted: <reason>` in the Score column and
leaves the counts empty. Take each summary's `ignoreStatic` for the static mutants line.

---
name: pr-convention
description: Apply the repository's required title, body, decisions and agent attribution when creating, editing or reviewing PRs.
---

# Product-first pull requests

Use this skill when opening, editing or reviewing a pull request in this monorepo. Read
[`docs/development/pull-requests.md`](../../../docs/development/pull-requests.md) for the full
taxonomy and examples.

## Required convention

Use this title shape:

```text
<product-area>/<technical-surface>: <verb> <outcome>
```

Put an `Area` section first in the body with these fields:

```md
## Area

- Product area: `...`
- Technical surface: `...`
- Affected products: `...`
- Primary paths: `...`
- Change class: `...`
- Stack/base: `...`
```

Choose exactly one primary product area. The product area describes the behavior or ownership;
the technical surface describes the implementation concern. For example, a desktop-only release
script is `desktop/release`, while a release system shared by products is `delivery/release`.

Keep the existing `class:*` label as the change classification. It does not replace the product
area. Include validation and the required UI or runtime evidence in the body.

Solve one underlying problem per PR and describe the observed validation results and any gaps.
Keep `Decisions` and `Agent review and attribution` as the final two authored sections, following the
linked guide. The footer briefly names who reviewed and their actual verdicts; the final line
names creator models and harnesses, including contributing agents. Keep commit ids, links and
detailed review records out of the footer.
Record pending reviews honestly and refresh the description after each push and review.
Apply the same requirements to specialized PR templates.

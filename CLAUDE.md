# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git

Never run `git commit` or `git push` in this repository, and never run anything that creates or
rewrites commits or changes a remote: `git commit --amend`, `git merge`, `git rebase`,
`git cherry-pick`, `git revert`, `git tag`, `git stash`, `gh pr create`, `gh pr merge`.

Alec makes every commit and push himself, by hand. This holds even when a task, a skill or a
workflow says to commit, open a pull request or push a branch. Leave the changes in the working
tree, say what changed, and stop there.

Reading is fine: `git status`, `git diff`, `git log`, `git show`.

## Commands

```sh
pnpm install
pnpm dev                    # Vite dev server
pnpm build                  # tsc --noEmit, vite build, then the content check against dist/
pnpm preview --port 4317    # serve dist/; unknown addresses return a bare 404 here
pnpm intro:render           # re-render public/intro/ (needs Blender 5.2 and ffmpeg)
```

The content check is the only test suite. It reads `dist/`, so build first.

```sh
node --test checks/content.test.js                                   # all checks
node --test --test-name-pattern="Full toolbox" checks/content.test.js  # one check
```

Renders are slow, so render only what changed. `CUTS` picks the home intro cuts and `WORDS` the
page titles; an empty value skips that group. `BLENDER` overrides the Blender executable.

```sh
CUTS= WORDS="cooking" pnpm intro:render    # one page title, no home intro
CUTS="wide tall" WORDS= pnpm intro:render  # the home intro only
CUTS= TITLE_CUTS=tall WORDS="projects experience hobbies cooking gardening" pnpm intro:render # tall titles only
```

The container needs `docker login dhi.io` once, because both stages use Docker Hardened Images.

```sh
docker build -t fielding-cloud . && docker run --rm -p 8080:8080 fielding-cloud
```

## Architecture

A static multi-page site: seven HTML entry points listed in `vite.config.ts` (`appType: "mpa"`),
one stylesheet (`src/style.css`) and one script (`src/main.ts`). There is no templating and no
content data file. The copy lives in the HTML, and the head, nav and footer are repeated in every
page, so a change to any of them is a change to all seven files, `404.html` included. There is no
templating on purpose. The content check fails the build when the copies differ, apart from the
current-page mark and the About link in the nav, one extra sentence in the home page's footer, and
the word in a title block. It also fails when a page on disk is missing from `vite.config.ts`.

### Copy and the content check

The site states facts about Alec's work that come from a private record. `checks/content.test.js`
runs at the end of `pnpm build` and fails the build when the home, Projects or Experience page
drifts from it. It asserts on the text of the built pages, not on class names or exact sentences:

- required facts on those three pages (roles and dates, headline numbers, education, the Projects
  groups and Card titles);
- forbidden text on every page, the hobbies pages and `404.html` included, which covers
  ordinary-looking words such as "Manager", "customers", "RAG", "38" and any em dash. It reads the
  visible text and also `alt`, `aria-label` and `title` attributes and the link-preview tags;
- the Full toolbox on Experience, which must equal the `FULL_TOOLBOX` list in the check exactly,
  group by group and in order. That list and `experience/index.html` are the only two places the
  whole list appears. Edit both together.

The same check holds the facts that several files share: the repeated head, nav, footer and title
block, each page's link-preview tags, the wide and tall condition, the waffle and tomato chart
numbers, and every internal link and anchor.

Do not add a claim, a number or a tool that is not already on the site without asking. If `specs/`
and `GLOSSARY.md` exist locally (they are gitignored), read them before changing copy: they define
the terms and the limits on how each fact may be worded.

### Rendered art (`blender/` to `public/intro/`)

The home intro and the brick page titles are pre-rendered clips, generated headless from Python.

- `blender/intro.py` builds the home scene. It prints `finale_seconds`, which must match `FINALE`
  in `src/main.ts`: that is when the page takes over from the video. `blender/render.sh` stops
  before encoding if the two differ. The brick material and the brick object with its bevel are
  one helper each here, and `title.py` imports them.
- `blender/title.py` renders one title per `TITLE_WORD`. New letters need adding to `FONT`. The
  `OUTFIT` map picks the figure's costume and ending per word (chef for COOKING, gardener for
  GARDENING).
- `blender/figure.py` builds the figure. Its head and hair are cut from `public/profile.webp` by
  `blender/headart.py`, so changing that picture changes the figure.
- `blender/render.sh` renders and encodes everything; the word list is its `WORDS` default.

The home intro has two cuts, wide and tall, switched at `(max-aspect-ratio: 4/5)`. That one
condition appears in three places that must agree: the `<source media>` attributes and the preload
links in `index.html`, and the media query in `src/style.css`. The content check compares them. The `.art` class gives the intro
video and the hero image identical geometry so one fades into the other without a jump.

### Scripts

`src/main.ts` runs the home intro with Effect and marks the current section on the sticky jump
links. Each page also has small inline scripts that must run before the module loads: the home page
decides before first paint whether to play the intro and sets a failsafe; title pages play their
clip once per tab; `404.html` names the requested path. Every animated element falls back to a
still image under reduced motion, without scripts, or if the video fails.

A visitor has seen the intro once its video starts playing. `src/main.ts` records that, in one
place. Leaving the intro (Skip, Escape, the finale, the failsafe) is the inline script's job, in
one function, and it never records anything: blocked autoplay or leaving before the first frame
means the intro plays again next visit. The page titles work differently on purpose: a title is
marked for the tab before its clip starts. Don't align the two.

The container sends a Content Security Policy from `docker/security-headers.inc`. It allows inline
scripts and Google Fonts and nothing else external, so a new third-party resource needs that file
changed too. `docker/nginx.conf` sets caching and serves `404.html` with a 404 status.

### Figures

The charts on Projects, Experience and Gardening are CSS, drawn with studs. Most of their numbers
are in the markup: block sizes on `.waffle` (which sum to 661, 103 of them yellow), `--from` and
`--to` on the years chart (months counted from January 2018, out of 108, with "now" hard-coded),
`--n` on each tomato row. The build-time bar chart is the exception: its 14 and 3.4 minutes are in
`src/style.css` (`.bar`, `.bar-before`, `.bar-after`). Changing a number means changing those
values, the `aria-label` and the caption together. The content check adds up the waffle and the
tomato rows; nothing checks the years chart or the bar chart.

### Photos and print

Photos in `public/hobbies/` are resized to 1000 px with their metadata removed. Strip location data
from any photo before adding it.

The `@media print` block in `src/style.css` makes the pages print as dark text on white with the
contact details as plain text. It stands in for a résumé download, which the site deliberately does
not have yet.

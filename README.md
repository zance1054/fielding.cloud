# fielding.cloud

Personal site: static Vite + TypeScript, with Effect running the first-visit intro.

```sh
pnpm install
pnpm dev            # local dev server
pnpm build          # type-check, build to dist/, then run the content check
pnpm intro:render   # regenerate public/intro/ from blender/*.py (needs Blender 5.2 and ffmpeg)
```

## Container

`Dockerfile` builds the site (the build runs the content check) and serves `dist/` with nginx as a
non-root user on port 8080. Both stages use Docker Hardened Images, so run `docker login dhi.io`
before the first build. `docker/nginx.conf` sets the caching and serves `404.html` for unknown
addresses.

```sh
docker build -t fielding-cloud .
docker run --rm -p 8080:8080 fielding-cloud
```

## Content check

The copy lives in the HTML pages. `checks/content.test.js` reads every built page. On the home,
Projects and Experience pages it checks what a visitor reads: the roles and dates, the headline
numbers, the education, and the Projects groups and Cards. On every page it checks for claims that
must never appear, in the visible text, in image and label text, and in the link-preview tags. It
runs at the end of `pnpm build` on Node's test runner, so a failing check fails the build.

The same check holds what several files must share. The head, nav, footer and title block are
repeated in each page with no templating, and the check fails when the copies differ. It also
fails when a page on disk is not in `vite.config.ts`, when the wide and tall cuts switch at
different conditions, when a chart's studs don't add up to its label, and when an internal link
or anchor leads nowhere.

The check keeps its own list of the Full toolbox on the Experience page. To add or remove a
tool, edit that list and `experience/index.html` together.

## Intro

`blender/intro.py` builds the scene from nothing: bricks assemble a build, test, ship pipeline
and each stage goes green. Run it inside Blender (for example through the Blender MCP) to iterate
on the look; `INTRO_CUT=wide` (default) or `INTRO_CUT=tall` picks the framing.

`pnpm intro:render` renders both cuts headless and writes, per cut, `intro-<cut>.webm`,
`intro-<cut>.mp4`, `poster-<cut>.webp` (first frame) and `hero-<cut>.webp` (last frame, the hero
background). Portrait screens (aspect ratio up to 4:5) get the tall cut.

The page takes over when the last cap lands. If you change the timing in `intro.py`, copy the
`finale_seconds` it prints into `FINALE` in `src/main.ts`. `pnpm intro:render` stops before
encoding when the two differ.

The intro plays until a visitor has seen it (`localStorage["intro-seen"]`), which means until its
video has started playing once, and is skipped for `prefers-reduced-motion`. If the video can't
start within 2.5 seconds, or the script never loads, the page is shown instead and the intro
plays on the next visit. "Replay the build" in the hero plays it again.

## Pages and titles

Seven pages, listed in `vite.config.ts`: `index.html`, `projects/`, `experience/`, `hobbies/`,
`hobbies/cooking/`, `hobbies/gardening/` and `404.html`. The nav is repeated in each. The hobby photos
are in `public/hobbies/`, resized to 1000 px with their metadata removed.

`blender/title.py` renders the page titles: a brick figure (`blender/figure.py`) modelled on the
profile picture throws bricks that stack into the word. `TITLE_WORD` picks the word; a new word
may need letters added to `FONT` there. COOKING dresses the figure as a chef and drops a hat on
him at the end. GARDENING puts him in overalls and a straw hat, and he plants a tree. Add a
word to `WORDS` in `blender/render.sh` to render it. `pnpm intro:render` writes `title-<word>.webm`, `.mp4`
and `.webp` (the finished word). The page shows the still and plays the clip over it, so reduced
motion, no scripts, or a video that fails all leave the finished word. `CUTS= pnpm intro:render`
renders only the titles.

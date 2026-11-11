import { Effect } from "effect"
import posthog, { posthogEnabled, posthogLogger } from "./posthog"
import "./style.css"

declare global {
  interface Window {
    /** Set by the inline script in index.html: shows the page if the intro never gets going. */
    introFailsafe?: ReturnType<typeof setTimeout>
  }
}

/** Seconds into the video when the last cap lands: frame 70 at 30 fps in blender/intro.py. */
const FINALE = 2.3

const root = document.documentElement

const capture = (event: string, properties?: Record<string, string>) => {
  if (posthogEnabled) posthog.capture(event, properties)
}

const once = (target: EventTarget, event: string) =>
  Effect.callback<void>((resume) => {
    const handler = () => resume(Effect.void)
    target.addEventListener(event, handler, { once: true })
    return Effect.sync(() => target.removeEventListener(event, handler))
  })

/** Completes on the first animation frame at or past `time`. */
const reached = (video: HTMLVideoElement, time: number) =>
  Effect.callback<void>((resume) => {
    let id = 0
    const tick = () => {
      if (video.currentTime >= time || video.ended) resume(Effect.void)
      else id = requestAnimationFrame(tick)
    }
    id = requestAnimationFrame(tick)
    return Effect.sync(() => cancelAnimationFrame(id))
  })

/** Completes when every candidate `<source>` has failed. `play()` never settles in that case. */
const noSource = (video: HTMLVideoElement) =>
  Effect.callback<void>((resume) => {
    const sources = [...video.querySelectorAll("source")]
    const handler = () => {
      if (video.networkState === HTMLMediaElement.NETWORK_NO_SOURCE) resume(Effect.void)
    }
    for (const source of sources) source.addEventListener("error", handler)
    return Effect.sync(() => {
      for (const source of sources) source.removeEventListener("error", handler)
    })
  })

/** True once the video is playing; false if autoplay is blocked, it can't load, or it's too slow. */
const start = (video: HTMLVideoElement) =>
  Effect.raceAll([
    Effect.promise(() =>
      video.play().then(
        () => true,
        () => false,
      ),
    ),
    noSource(video).pipe(Effect.as(false)),
    Effect.sleep("2.5 seconds").pipe(Effect.as(false)),
  ])

const markSeen = () => {
  try {
    localStorage.setItem("intro-seen", "1")
  } catch {
    // Private mode: the intro just plays again next visit.
  }
}

/**
 * Plays the intro in its open dialog and hands over to the page as the last cap lands; the
 * video's remaining frames play out under the dialog's fade. Closing the dialog (Skip, Escape)
 * ends it early. A visitor who never saw it play is not marked as having seen it.
 */
const playIntro = (intro: HTMLDialogElement, video: HTMLVideoElement) =>
  Effect.gen(function* () {
    const started = yield* start(video)
    if (!started) return false
    clearTimeout(window.introFailsafe)
    // A stall mid-playback must not hold the page back for long.
    yield* Effect.raceFirst(reached(video, FINALE), Effect.sleep("6 seconds"))
    return true
  }).pipe(
    Effect.raceFirst(once(intro, "close").pipe(Effect.as(false))),
    Effect.andThen((played) =>
      Effect.sync(() => {
        if (played) {
          markSeen()
          capture("intro_completed")
          posthogLogger.info("intro playback completed", {
            component: "intro",
            outcome: "completed",
          })
        }
        root.dataset.intro = "done"
        if (intro.open) intro.close()
      }),
    ),
  )

const intro = document.querySelector<HTMLDialogElement>("#intro")
const video = intro?.querySelector("video")

if (intro && video) {
  if (root.dataset.intro === "play" && intro.open) Effect.runFork(playIntro(intro, video))

  intro.querySelector("button")?.addEventListener("click", () => intro.close())

  document.querySelector(".replay")?.addEventListener("click", () => {
    capture("intro_replayed")
    posthogLogger.info("intro replay requested", {
      component: "intro",
      action: "replayed",
    })
    root.dataset.intro = "play"
    video.currentTime = 0
    intro.showModal()
    Effect.runFork(playIntro(intro, video))
  })
}

const portfolioDestinations: Record<string, string> = {
  "/": "home",
  "/projects/": "projects",
  "/experience/": "experience",
  "/hobbies/": "hobbies",
}

document.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) return
  const link = event.target.closest<HTMLAnchorElement>("a[href]")
  if (!link) return

  const destination = new URL(link.href)
  if (destination.protocol === "mailto:") {
    capture("contact_link_clicked", { contact_method: "email" })
  } else if (destination.hostname === "www.linkedin.com") {
    capture("contact_link_clicked", { contact_method: "linkedin" })
  } else if (destination.hostname === "github.com") {
    capture("contact_link_clicked", { contact_method: "github" })
  } else if (destination.origin === location.origin && !destination.hash) {
    const portfolioDestination = portfolioDestinations[destination.pathname]
    if (portfolioDestination) capture("portfolio_navigation_clicked", { destination: portfolioDestination })
  }
})

// Jump links (Projects, Experience) show which part of the page is in view: the last one whose
// heading has passed under the two bars.
const jumps = [...document.querySelectorAll<HTMLAnchorElement>(".jump a")]
if (jumps.length > 0) {
  const mark = () => {
    let current = jumps[0]
    for (const link of jumps) {
      const target = document.getElementById(link.hash.slice(1))
      if (target && target.getBoundingClientRect().top <= 150) current = link
    }
    for (const link of jumps) {
      if (link === current) link.setAttribute("aria-current", "true")
      else link.removeAttribute("aria-current")
    }
  }
  addEventListener("scroll", mark, { passive: true })
  mark()
}

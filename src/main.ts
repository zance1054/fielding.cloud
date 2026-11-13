import { Effect } from "effect"
import posthog, { posthogEnabled, posthogLogger } from "./posthog"
import "./style.css"

declare global {
  interface Window {
    /** Set by the inline script in index.html: shows the page if the intro never gets going. */
    introFailsafe?: ReturnType<typeof setTimeout>
    leaveIntro?: () => void
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
 * Plays the intro in its open dialog and closes it as the last cap lands.
 * Closing the dialog (Skip, Escape) stops playback through the inline leave function.
 *
 * A visitor has seen the intro once the video starts playing, and this is the only place that
 * records it: blocked autoplay, a video that can't load and leaving before it starts don't count.
 * Leaving itself belongs to the inline script in index.html, which runs when the dialog closes.
 */
const playIntro = (intro: HTMLDialogElement, video: HTMLVideoElement) =>
  Effect.gen(function* () {
    if (!(yield* start(video))) return
    markSeen()
    clearTimeout(window.introFailsafe)
    // A stall mid-playback must not hold the page back for long.
    yield* Effect.raceFirst(reached(video, FINALE), Effect.sleep("6 seconds"))
    capture("intro_completed")
    posthogLogger.info("intro playback completed", { component: "intro", outcome: "completed" })
  }).pipe(
    Effect.raceFirst(once(intro, "close")),
    Effect.andThen(Effect.sync(() => window.leaveIntro?.())),
  )

const intro = document.querySelector<HTMLDialogElement>("#intro")
const video = intro?.querySelector("video")

if (intro && video) {
  const progress = intro.querySelector<HTMLProgressElement>(".intro-progress")
  const updateProgress = () => {
    if (progress) progress.value = Math.min(video.currentTime, FINALE)
  }
  let progressFrame = 0
  const tickProgress = () => {
    updateProgress()
    if (!video.paused && !video.ended && intro.open) progressFrame = requestAnimationFrame(tickProgress)
  }
  video.addEventListener("playing", () => {
    cancelAnimationFrame(progressFrame)
    tickProgress()
  })
  intro.addEventListener("close", () => cancelAnimationFrame(progressFrame))
  video.addEventListener("seeking", updateProgress)
  if (root.dataset.intro === "play" && intro.open) Effect.runFork(playIntro(intro, video))

  const replay = document.querySelector<HTMLButtonElement>(".replay")
  if (replay) replay.hidden = false
  replay?.addEventListener("click", () => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return
    capture("intro_replayed")
    posthogLogger.info("intro replay requested", { component: "intro", action: "replayed" })
    root.dataset.intro = "play"
    if (progress) progress.value = 0
    video.currentTime = 0
    intro.showModal()
    Effect.runFork(playIntro(intro, video))
  })
}

// Controls are enhancements: the email link and printable content work without scripts.
const copyEmail = document.querySelector<HTMLButtonElement>(".copy-email")
const copyStatus = document.querySelector<HTMLElement>(".copy-status")
if (copyEmail && copyStatus) {
  copyEmail.hidden = false
  let reset: ReturnType<typeof setTimeout>
  copyEmail.addEventListener("click", async () => {
    clearTimeout(reset)
    copyStatus.textContent = ""
    try {
      await navigator.clipboard.writeText("alec@fielding.cloud")
      const address = document.querySelector<HTMLElement>(".copy-address")
      if (address) address.hidden = true
      window.getSelection()?.removeAllRanges()
      copyEmail.textContent = "Copied!"
      // A fresh live-region update, including on consecutive copies.
      setTimeout(() => { copyStatus.textContent = "Email copied." }, 100)
    } catch {
      const address = document.querySelector<HTMLElement>(".copy-address")
      if (address) {
        address.hidden = false
        const range = document.createRange()
        range.selectNodeContents(address)
        const selection = window.getSelection()
        selection?.removeAllRanges()
        selection?.addRange(range)
      }
      copyEmail.textContent = "Select"
      setTimeout(() => { copyStatus.textContent = "Copy blocked. The address below is selected." }, 100)
    }
    reset = setTimeout(() => { copyEmail.textContent = "Copy"; copyStatus.textContent = "" }, 4000)
  })
}
const printPage = document.querySelector<HTMLButtonElement>(".print-page")
if (printPage) {
  printPage.hidden = false
  printPage.addEventListener("click", () => window.print())
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
      if (link === current) link.setAttribute("aria-current", "location")
      else link.removeAttribute("aria-current")
    }
  }
  addEventListener("scroll", mark, { passive: true, capture: true })
  mark()
}


// The document owns scrolling and history restoration. Only the footer link remains.
const backTop = document.querySelector<HTMLAnchorElement>(".back-top")
backTop?.addEventListener("click", event => {
  event.preventDefault()
  window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" })
  document.querySelector<HTMLAnchorElement>(".nav-brand")?.focus({ preventScroll: true })
})

// One control reveals every group's remaining tools. No scripts means every tool is visible.
const toolboxToggle = document.querySelector<HTMLButtonElement>(".toolbox-toggle")
const allTools = document.querySelector<HTMLElement>("#all-tools")
const toolboxCollapse = document.querySelector<HTMLButtonElement>(".toolbox-collapse")
if (toolboxToggle && allTools) {
  const count = allTools.querySelectorAll(".parts > li").length
  const setOpen = (open: boolean) => {
    allTools.classList.toggle("tools-collapsed", !open)
    if (toolboxCollapse) toolboxCollapse.hidden = !open
    toolboxToggle.setAttribute("aria-expanded", String(open))
    toolboxToggle.textContent = open ? "Show fewer tools" : `Show all ${count} tools`
  }
  toolboxCollapse?.addEventListener("click", () => {
    setOpen(false)
    toolboxToggle.focus()
    toolboxToggle.scrollIntoView({ block: "center" })
  })
  toolboxToggle.hidden = false
  setOpen(false)
  toolboxToggle.addEventListener("click", () => setOpen(toolboxToggle.getAttribute("aria-expanded") !== "true"))
}

// The CSS figures are the no-script fallback. Individual studs retain exactly the same data.
const motion = matchMedia("(prefers-reduced-motion: reduce)")
if (!motion.matches && "IntersectionObserver" in window) {
  const figures = [...document.querySelectorAll<HTMLElement>(".units, .waffle")]
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue
      const figure = entry.target as HTMLElement
      const blocks = figure.matches(".units") ? [figure] : [...figure.querySelectorAll<HTMLElement>("[style]")]
      let placed = 0
      const total = figure.matches(".waffle") ? 661 : 80
      for (const block of blocks) {
        const width = figure.matches(".units") ? 20 : Number(block.style.getPropertyValue("--w"))
        const height = figure.matches(".units") ? 4 : Number(block.style.getPropertyValue("--h"))
        for (let i = 0; i < width * height; i++) {
          const stud = document.createElement("span")
          stud.className = "assembly-stud"
          stud.setAttribute("aria-hidden", "true")
          const delay = placed++ / total * 280
          stud.style.setProperty("--delay", `${delay}ms`)
          block.append(stud)
        }
        block.classList.add("has-studs")
      }
      figure.classList.add("assembly-running")
      observer.unobserve(figure)
    }
  }, { threshold: 0.15 })
  figures.forEach(figure => observer.observe(figure))
}

// Reads every built page. Checks what a visitor reads on the home, Projects and Experience pages
// against the Record (Alec's verified work history), keeps forbidden claims off every page, and
// holds the facts that several files must share. `pnpm build` runs it, so a failure fails the build.
import assert from "node:assert/strict"
import { existsSync, readdirSync, readFileSync } from "node:fs"
import { test } from "node:test"

// The Full toolbox, in page order. This list and experience/index.html are the only two places
// the whole list appears: a tool gets recorded use in the Record first, then is added to both.
const FULL_TOOLBOX = {
  Languages: [
    "Python",
    "Go",
    "PowerShell",
    "TypeScript / Electron",
    "Groovy",
    "Bash",
    "HTML/CSS",
    "SQL",
    "JavaScript",
    "Java",
    "Socket / UDP messaging",
    "C++",
    "C#",
    "Microsoft Access / VBA",
  ],
  "Frameworks and web": [
    "MongoDB / Beanie",
    "FastAPI",
    "React",
    "Django",
    "Stripe",
    ".NET",
    "React Native",
    "MERN",
    "NumPy / Pandas",
  ],
  "Cloud and infrastructure": [
    "Kubernetes",
    "Unraid / self-hosted Docker",
    "Amazon ECS / ECR / CodeArtifact",
    "Nginx Proxy Manager / Let's Encrypt",
    "PostgreSQL",
    "Microsoft 365 platform (Graph, SharePoint, Teams, MSAL)",
    "Azure",
    "Tailscale",
    "Helm",
    "Docker EE",
    "Private corporate cloud",
    "AWS",
    "Azure Kubernetes Service (AKS)",
    "MySQL / MariaDB",
    "AWS ALB / ACM",
    "Vercel",
    "Cloudflare",
    "Linux virtual machines",
    "AWS API Gateway",
  ],
  "CI/CD and DevSecOps": [
    "Harness",
    "CodeRabbit",
    "GitHub Actions (composite actions, reusable workflows, self-hosted runners)",
    "Docker Hardened Images",
    "Doppler",
    "Keycloak / OIDC",
    "Flux CD",
    "SonarQube",
    "JFrog Artifactory",
    "Sysdig",
    "Wiz",
    "Checkmarx",
    "Jenkins",
    "HashiCorp Vault",
    "Code signing (Authenticode, SSL.com eSigner)",
    "Snyk",
    "gitleaks",
    "ArgoCD",
  ],
  "Infrastructure as code": [
    "OpenTofu",
    "Terraform",
    "GitHub organization as code (Terraform github provider)",
    "Bicep",
    "Ansible",
  ],
  Observability: ["Splunk", "PostHog", "OpenTelemetry", "Grafana Alloy", "Grafana"],
  Testing: ["Playwright", "Selenium"],
  "AI and agents": [
    "Multi-agent orchestration",
    "T3 Code (agent orchestration)",
    "OpenAI Codex",
    "Anthropic API",
    "MCP (Model Context Protocol)",
    "Claude Code",
    "LLM application design (structured output, grounding, tool guardrails)",
    "LLM tool calling",
    "LLM testing with a scripted model",
    "Prompt-injection defense",
    "Microsoft 365 Copilot APIs",
  ],
}

// The smart-home dashboard Card joins this list when its Record row is confirmed.
const CARDS = [
  "Docker EE to Kubernetes migration",
  "Three Jenkins instances to one Harness platform",
  "Pipeline factories",
  "Wagon Works AI",
  "Agent-driven delivery",
  "LLM features with guardrails",
  "A crash loop that led to a release gate",
  "Homelab",
  "This site",
]

const repo = new URL("../", import.meta.url)
const dist = new URL("../dist/", import.meta.url)

/** Every .html file under a directory, as paths like "hobbies/cooking/index.html". */
function pagesUnder(dir, skip = () => false, prefix = "") {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = prefix + entry.name
    if (entry.isDirectory()) return skip(path) ? [] : pagesUnder(new URL(entry.name + "/", dir), skip, path + "/")
    return entry.name.endsWith(".html") ? [path] : []
  })
}

const PAGES = pagesUnder(dist).sort()
const HOME = "index.html"
const html = Object.fromEntries(PAGES.map((page) => [page, readFileSync(new URL(page, dist), "utf8")]))
const css = readdirSync(new URL("assets/", dist))
  .filter((name) => name.endsWith(".css"))
  .map((name) => readFileSync(new URL("assets/" + name, dist), "utf8"))
  .join("\n")

/** What a visitor or a search result shows: the description, then the page's text, one line per block. */
function linesOf(source) {
  const description = source.match(/<meta\s+name="description"\s+content="([^"]*)"/)?.[1] ?? ""
  return (description + "\n" + source)
    .replace(/<(script|style)\b[\s\S]*?<\/\1>/g, "")
    .replace(/\s+/g, " ")
    .replace(/<\/?(title|p|li|ul|ol|h[1-6]|div|section|article|header|main|br)\b[^>]*>/g, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
}

/** Text a visitor never sees on the page: what a screen reader says and what a link preview shows. */
function unseenOf(source) {
  const markup = source.replace(/<(script|style)\b[\s\S]*?<\/\1>/g, "")
  return [
    ...markup.matchAll(/\s(?:alt|aria-label|title)="([^"]*)"/g),
    ...markup.matchAll(/<meta\s+property="og:(?:title|description)"\s+content="([^"]*)"/g),
  ].map((match) => match[1].replace(/&amp;/g, "&"))
}

/** A stretch of markup with its whitespace collapsed, so indentation is not a difference. */
const flat = (markup) => markup.replace(/\s+/g, " ").replace(/> </g, "><").trim()

const lines = Object.fromEntries(Object.entries(html).map(([page, source]) => [page, linesOf(source)]))
const text = Object.fromEntries(Object.entries(lines).map(([page, l]) => [page, l.join("\n")]))
const experience = lines["experience/index.html"]

test("Experience shows the current role at The Lobbi Corp", () => {
  const start = experience.findIndex((line) => line.startsWith("Co-Founder") && line.includes("The Lobbi Corp"))
  assert.notEqual(start, -1, "no Lobbi Corp entry")
  assert.match(experience.slice(start, start + 2).join(" "), /Aug 2025/)
})

test("TransUnion ended in Aug 2026 and is not shown as current", () => {
  const start = experience.findIndex((line) => line.startsWith("Software Architect") && line.includes("TransUnion"))
  const end = experience.findIndex((line) => line.startsWith("Oracle SQL Programmer"))
  assert.ok(start !== -1 && end > start, "no TransUnion entry above the Oracle SQL Programmer entry")
  const entry = experience.slice(start, end).join("\n")
  assert.match(entry, /Sep 2019/)
  assert.match(entry, /Aug 2026/)
  assert.doesNotMatch(entry, /present/i)
})

test("the headline numbers are on the home page and on Projects", () => {
  for (const page of [HOME, "projects/index.html"]) {
    for (const number of ["$1.8M", "408", "661"]) {
      assert.ok(text[page].includes(number), `${number} is missing from ${page}`)
    }
  }
})

test("Experience lists the degree, the certification and the publication", () => {
  const page = text["experience/index.html"]
  for (const fact of ["B.S., Computer Science", "AWS Certified Cloud Practitioner", "Journal of Double Star Observations"]) {
    assert.ok(page.includes(fact), `${fact} is missing`)
  }
})

test("Projects has its three groups and every Card", () => {
  const page = lines["projects/index.html"]
  for (const heading of ["Platform", "Product and AI", "Personal", ...CARDS]) {
    assert.ok(page.includes(heading), `"${heading}" is missing`)
  }
})

test("the Full toolbox on Experience is exactly the recorded tools, in order", () => {
  const section = html["experience/index.html"].match(/<section id="toolbox"[\s\S]*?<\/section>/)
  assert.ok(section, "no Full toolbox section")
  const listed = linesOf(section[0])
  assert.equal(listed[0], "Full toolbox")
  const expected = Object.entries(FULL_TOOLBOX).flatMap(([group, tools]) => [group, ...tools])
  // Everything from the first group name on: a line of introduction may sit above it.
  assert.deepEqual(listed.slice(listed.indexOf(expected[0])), expected)
})

test("no stale or forbidden claim appears on any page, seen or unseen", () => {
  const forbidden = [
    /\bGCP\b/,
    /Prometheus/i,
    /Mirantis/i,
    /release time/i,
    /customers/i,
    /\bRAG\b/,
    /Manager/, // the title; "the manager's extended leave" is the allowed wording
    /\b38\b/,
    new RegExp(String.fromCharCode(0x2014)), // em dash
  ]
  for (const page of PAGES) {
    // Nginx Proxy Manager is a product name, not the title.
    const checked = [text[page], ...unseenOf(html[page])].join("\n").replaceAll("Nginx Proxy Manager", "")
    for (const pattern of forbidden) {
      assert.doesNotMatch(checked, pattern, `${page} says ${pattern}`)
    }
  }
})

test("no page links to a coffee tip jar or a résumé PDF", () => {
  // The PDF assertion flips to required when the Public résumé is approved.
  for (const [page, source] of Object.entries(html)) {
    assert.doesNotMatch(source, /buymeacoffee/i, page)
    assert.doesNotMatch(source, /href="[^"]*\.pdf"/i, page)
  }
})

// From here on: facts that live in more than one file and must agree.

test("every page in the source tree is built", () => {
  // A page missing from the list in vite.config.ts works in `pnpm dev` and is absent from dist/.
  const skip = (path) => path.startsWith(".") || ["node_modules", "dist", "public"].includes(path)
  assert.deepEqual(PAGES, pagesUnder(repo, skip).sort())
})

test("each page's link preview matches its title and description", () => {
  for (const page of PAGES) {
    const source = html[page]
    const title = source.match(/<title>([^<]*)<\/title>/)?.[1]
    const description = source.match(/<meta\s+name="description"\s+content="([^"]*)"/)?.[1]
    assert.ok(title && description, `${page} has no title or description`)
    assert.equal(source.match(/<meta\s+property="og:title"\s+content="([^"]*)"/)?.[1], title, page)
    assert.equal(source.match(/<meta\s+property="og:description"\s+content="([^"]*)"/)?.[1], description, page)
  }
})

test("the shared head lines are the same on every page", () => {
  // What is left of the head once the lines a page owns are taken out.
  const shared = (source) =>
    flat(
      source
        .match(/<head>([\s\S]*?)<\/head>/)[1]
        .replace(/<title>[^<]*<\/title>/, "")
        .replace(/<meta\s+name="description"[^>]*>/, "")
        .replace(/<meta\s+property="og:(?:title|description)"[^>]*>/g, "")
        .replace(/<link\s+rel="preload"[^>]*>/g, "")
        .replace(/<script>[\s\S]*?<\/script>/g, ""),
    )
  for (const page of PAGES) assert.equal(shared(html[page]), shared(html[HOME]), page)
})

test("the nav is the same on every page and marks the right one", () => {
  const navOf = (page) => flat(html[page].match(/<header class="nav">[\s\S]*?<\/header>/)[0])
  // The two differences that are meant to be there: the current-page mark, and the About link,
  // which is in-page on the home page and leads back to it from everywhere else.
  const plain = (page) => {
    const nav = navOf(page).replace(/ aria-current="[^"]*"/g, "")
    return page === HOME ? nav.replace('href="#about"', 'href="/#about"') : nav
  }
  for (const page of PAGES) {
    assert.equal(plain(page), plain(HOME), page)

    // A section's own page is marked "page", a page beneath it "true", and the rest not at all.
    const section = page.includes("/") ? page.split("/")[0] : null
    const mark = page === `${section}/index.html` ? "page" : "true"
    const marks = [...navOf(page).matchAll(/href="([^"]*)" aria-current="([^"]*)"/g)].map((m) => `${m[1]} ${m[2]}`)
    assert.deepEqual(marks, section ? [`/${section}/ ${mark}`] : [], page)
  }
})

test("the footer is the same on every page", () => {
  const footerOf = (page) => flat(html[page].match(/<footer\b[\s\S]*?<\/footer>/)[0])
  // The home page's footer may add this one sentence.
  const home = footerOf(HOME).replace(" Brisket talk is welcome too.", "")
  for (const page of PAGES) {
    if (page !== HOME) assert.equal(footerOf(page), home, page)
  }
})

test("the Title block is the same on every page that has one, apart from its word", () => {
  const blocks = PAGES.flatMap((page) => {
    const block = html[page].match(/<div class="title-art"[\s\S]*?<\/script>/)
    return block ? [[page, flat(block[0])]] : []
  })
  assert.ok(blocks.length > 1, "no Title blocks found")
  const plain = (block) => block.replace(/title-[a-z]+\./g, "title-WORD.")
  for (const [page, block] of blocks) {
    const words = new Set([...block.matchAll(/title-([a-z]+)\./g)].map((m) => m[1]))
    assert.equal(words.size, 1, `${page} names more than one word: ${[...words]}`)
    assert.equal(plain(block), plain(blocks[0][1]), page)
  }
})

test("the wide and tall Cuts switch at one condition", () => {
  const home = html[HOME]
  const conditions = new Set([...home.matchAll(/<source\b[^>]*\smedia="([^"]*)"/g)].map((m) => m[1]))
  assert.equal(conditions.size, 1, `the video sources switch at ${[...conditions].join(" and ")}`)
  const [condition] = conditions
  const preloads = [...home.matchAll(/<link\s+rel="preload"[^>]*\smedia="([^"]*)"/g)].map((m) => m[1])
  assert.deepEqual(preloads.sort(), [condition, `not all and ${condition}`].sort())
  // The source stylesheet: the build rewrites the condition into another syntax.
  const styles = readFileSync(new URL("src/style.css", repo), "utf8")
  assert.ok(styles.includes(`@media ${condition} {`), `src/style.css has no @media ${condition}`)
})

test("the waffle chart's studs add up to the numbers beside it", () => {
  const figure = html["projects/index.html"].match(/<div class="waffle"[\s\S]*?<\/figure>/)
  assert.ok(figure, "no waffle chart")
  const blocks = [...figure[0].matchAll(/<div( class="mine")? style="--w: (\d+); --h: (\d+)"/g)]
  const studs = (list) => list.reduce((sum, [, , w, h]) => sum + w * h, 0)
  const total = studs(blocks)
  const mine = studs(blocks.filter(([, own]) => own))
  assert.ok(figure[0].includes(`aria-label="${total} studs, ${mine} of them yellow"`), "the label's numbers")
  const caption = linesOf(figure[0].match(/<figcaption>[\s\S]*?<\/figcaption>/)[0]).join(" ")
  assert.ok(caption.split(/\D+/).includes(String(total)), "the caption's total")
  assert.ok(caption.split(/\D+/).includes(String(mine)), "the caption's yellow count")
})

test("each tomato row shows the number its label says, and they add up to the heading", () => {
  const figure = html["hobbies/gardening/index.html"].match(/<figure class="tomatoes">[\s\S]*?<\/figure>/)
  assert.ok(figure, "no tomato chart")
  const rows = [...figure[0].matchAll(/style="--n: (\d+)" role="img" aria-label="(\d+) plants?"/g)]
  assert.equal(rows.length, [...figure[0].matchAll(/<li>/g)].length, "a row has no count or no label")
  for (const [row, dots, said] of rows) assert.equal(dots, said, row)
  const total = rows.reduce((sum, [, dots]) => sum + Number(dots), 0)
  const heading = figure[0].match(/<h3>([^<]*)<\/h3>/)?.[1] ?? ""
  assert.ok(heading.split(/\D+/).includes(String(total)), `the rows add up to ${total}, the heading says "${heading}"`)
})

test("every internal link, anchor and asset leads somewhere", () => {
  const fileFor = (path) => (path.endsWith("/") ? path + "index.html" : path).slice(1)
  for (const page of PAGES) {
    const source = html[page]
    const refs = [...source.matchAll(/\s(?:href|src)="([^"]*)"/g), ...source.matchAll(/url\('([^']*)'\)/g)]
    for (const [, ref] of refs) {
      if (!ref.startsWith("/") && !ref.startsWith("#")) continue // another site, or mailto:
      const [path, anchor] = ref.split("#")
      const target = path ? fileFor(path) : page
      assert.ok(existsSync(new URL(target, dist)), `${page} points to ${ref}, which is not in dist/`)
      if (anchor) assert.ok(html[target].includes(`id="${anchor}"`), `${page} points to ${ref}, and ${target} has no such id`)
    }
  }
  for (const [, , path] of css.matchAll(/url\((["']?)(\/[^)"']+)\1\)/g)) {
    assert.ok(existsSync(new URL(path.slice(1), dist)), `the stylesheet points to ${path}, which is not in dist/`)
  }
})

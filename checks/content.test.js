// Reads the three built pages and checks what a visitor reads against the Record
// (Alec's verified work history). `pnpm build` runs it, so stale or forbidden copy fails the build.
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

// The Full toolbox, in page order. This list and experience/index.html are the only two places
// the names appear: a tool gets recorded use in the Record first, then is added to both.
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

const html = Object.fromEntries(
  ["index.html", "projects/index.html", "experience/index.html"].map((page) => [
    page,
    readFileSync(new URL(`../dist/${page}`, import.meta.url), "utf8"),
  ]),
)

/** What a visitor or a search result shows: the description, then the page's text, one line per block. */
function linesOf(source) {
  const description = source.match(/<meta\s+name="description"\s+content="([^"]*)"/)?.[1] ?? ""
  return (description + "\n" + source)
    .replace(/<(script|style)\b[\s\S]*?<\/\1>/g, "")
    .replace(/\s+/g, " ")
    .replace(/<\/?(title|p|li|ul|ol|h[1-6]|div|section|article|header|main)\b[^>]*>/g, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
}

const lines = Object.fromEntries(Object.entries(html).map(([page, source]) => [page, linesOf(source)]))
const text = Object.fromEntries(Object.entries(lines).map(([page, l]) => [page, l.join("\n")]))
const site = Object.values(text).join("\n")
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

test("the headline numbers are on the site", () => {
  for (const number of ["$1.8M", "408", "661"]) {
    assert.ok(site.includes(number), `${number} is missing`)
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

test("no stale or forbidden claim appears on any page", () => {
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
  for (const [page, pageText] of Object.entries(text)) {
    // Nginx Proxy Manager is a product name, not the title.
    const checked = pageText.replaceAll("Nginx Proxy Manager", "")
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

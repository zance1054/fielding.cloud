import posthog from "posthog-js"

const key = import.meta.env.VITE_POSTHOG_KEY
const host = import.meta.env.VITE_POSTHOG_HOST

export const posthogEnabled = Boolean(key && host)

if (!posthogEnabled) {
  if (import.meta.env.DEV) {
    const variable = key ? "VITE_POSTHOG_HOST" : "VITE_POSTHOG_KEY"
    throw new Error(
      `${variable} variable required by PostHog is missing or un-configured, this causes events to be silently missed. This error stops appearing once ${variable} is configured`,
    )
  }
} else {
  posthog.init(key, {
    api_host: host,
    defaults: "2026-08-30",
    capture_exceptions: {
      capture_unhandled_errors: true,
      capture_unhandled_rejections: true,
      capture_console_errors: false,
    },
    logs: {
      serviceName: "fielding-cloud-web",
      environment: import.meta.env.MODE,
    },
  })
}

export const posthogLogger = {
  info: (message: string, attributes: Record<string, string>) => {
    if (posthogEnabled) posthog.logger.info(message, attributes)
  },
}

posthogLogger.info("browser analytics initialized", {
  component: "analytics",
  lifecycle: "initialized",
})

export default posthog

# Sent with every response. The pages use inline scripts and style attributes, and Google Fonts.
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Access-Control-Allow-Origin "*" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://*.posthog.com; connect-src 'self' https://*.posthog.com; worker-src 'self' blob: data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; media-src 'self'; base-uri 'self'; form-action 'none'; frame-ancestors 'none'" always;

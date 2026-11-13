# Builds the static site (the build runs the content check) and serves dist/ with nginx on port 8080.
# Both stages use Docker Hardened Images, which need `docker login dhi.io` to pull.
FROM dhi.io/node:24-dev AS build
WORKDIR /app
RUN npm install --global --ignore-scripts pnpm@12.18.0
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# Vite bakes these into the bundle; without them the build ships with analytics off.
ARG VITE_POSTHOG_KEY
ARG VITE_POSTHOG_HOST
RUN pnpm build

# Runs as a non-root user and listens on 8080. No shell or package manager in this image.
FROM dhi.io/nginx:1.31.8-alpine3.22
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/security-headers.inc /etc/nginx/security-headers.inc
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080

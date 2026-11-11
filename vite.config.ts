import { defineConfig } from "vite"

export default defineConfig({
  appType: "mpa", // an unknown address gets 404.html, not the home page
  build: {
    rollupOptions: {
      input: [
        "index.html",
        "projects/index.html",
        "experience/index.html",
        "hobbies/index.html",
        "hobbies/cooking/index.html",
        "hobbies/gardening/index.html",
        "404.html",
      ],
    },
  },
})

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In production the app is served by nginx and the API lives under /api on the
// same origin. In dev, proxy /api to the local backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
  build: { outDir: "dist", sourcemap: false },
});

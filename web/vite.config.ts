import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// In normal dev, /api is proxied to the FastAPI server. With VITE_USE_MOCK=1
// the client reads static JSON from public/mock-api instead (see src/api/client.ts).
export default defineConfig({
  plugins: [react()],
  // public/ only holds the exported mock API (paper text): never ship it in
  // a build that talks to a real server.
  publicDir: process.env.VITE_USE_MOCK === "1" ? "public" : false,
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});

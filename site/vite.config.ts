import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Served from the root of its own Vercel project. Routing is hash-based, so
// every page is index.html and a shared link or a refresh never needs a
// server-side rewrite.
export default defineConfig({
  base: "/",
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "dist",
    assetsInlineLimit: 0,
  },
});

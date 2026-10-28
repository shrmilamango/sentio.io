import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the dev server forwards API calls to the backend on :8000,
// so the browser only ever talks to one address (no CORS needed locally).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/v1": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 5500 matches the backend's default ALLOWED_ORIGINS
// (http://localhost:5500) so CORS works with zero backend changes.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5500,
    strictPort: true,
  },
});

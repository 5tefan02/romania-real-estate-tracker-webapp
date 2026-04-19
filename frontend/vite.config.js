// Vite config — tells Vite to use React.
// Vite is the dev server + bundler. `npm run dev` starts it.

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173, // must match FRONTEND_URL in backend/.env
  },
});

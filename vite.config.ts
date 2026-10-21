import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
const apiTarget = process.env.SHAPEOPS_DEV_API_URL || "http://127.0.0.1:8000";
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          three: ["three", "three/addons/controls/OrbitControls.js"],
          react: ["react", "react-dom"],
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": apiTarget,
      "/metrics": apiTarget,
      "/docs": apiTarget,
      "/openapi.json": apiTarget,
      "/redoc": apiTarget,
    },
  },
});

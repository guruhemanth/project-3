import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "app.subtrack.mobile",
  appName: "SubTrack",
  // Vite outputs to dist/; Capacitor copies it into the native projects.
  webDir: "dist",
  server: {
    // During dev you can live-reload from the running Vite server:
    //   npx cap run android --livereload --port 5173 (with VITE on 0.0.0.0)
    // In production the bundled assets are served from the app itself, no server needed.
    androidScheme: "https",
  },
  plugins: {
    StatusBar: {
      style: "DARK",
      backgroundColor: "#0b0b13",
    },
  },
};

export default config;

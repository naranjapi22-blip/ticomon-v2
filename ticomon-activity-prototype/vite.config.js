import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxy = env.ACTIVITY_BACKEND_ORIGIN
    ? { "/api": { target: env.ACTIVITY_BACKEND_ORIGIN, ws: true } }
    : undefined;

  return {
    server: {
      host: "0.0.0.0",
      allowedHosts: [".trycloudflare.com"],
      proxy,
    },
  };
});

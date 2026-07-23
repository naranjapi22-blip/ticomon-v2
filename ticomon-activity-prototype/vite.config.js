import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, loadEnv } from "vite";

const sharedBackgrounds = resolve(
  process.cwd(),
  "../rendering/assets/battle_bacgrounds",
);

function activityBackgroundsPlugin() {
  return {
    name: "ticomon-activity-shared-backgrounds",
    generateBundle() {
      for (const name of readdirSync(sharedBackgrounds).filter((file) =>
        /\.(?:jpg|png)$/i.test(file),
      )) {
        this.emitFile({
          type: "asset",
          fileName: `activity-backgrounds/${name}`,
          source: readFileSync(resolve(sharedBackgrounds, name)),
        });
      }
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxy = env.ACTIVITY_BACKEND_ORIGIN
    ? { "/api": { target: env.ACTIVITY_BACKEND_ORIGIN, ws: true } }
    : undefined;

  return {
    plugins: [activityBackgroundsPlugin()],
    server: {
      host: "0.0.0.0",
      allowedHosts: [".trycloudflare.com"],
      proxy,
    },
  };
});

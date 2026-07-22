import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";

const host = "0.0.0.0";
const port = Number(process.env.PORT || 4173);
const root = resolve(process.cwd(), "dist");
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
};

const send = (response, status, body, type) => {
  response.writeHead(status, { "Content-Type": type });
  response.end(body);
};

const server = createServer(async (request, response) => {
  const requestUrl = new URL(request.url || "/", "http://activity.local");
  const relativePath = decodeURIComponent(requestUrl.pathname);
  const candidate = resolve(root, `.${normalize(relativePath)}`);
  if (!candidate.startsWith(root)) {
    send(response, 400, "Invalid path", "text/plain; charset=utf-8");
    return;
  }

  try {
    const file = await stat(candidate);
    if (file.isFile()) {
      const body = await readFile(candidate);
      send(
        response,
        200,
        body,
        contentTypes[extname(candidate)] || "application/octet-stream",
      );
      return;
    }
  } catch {
    // Fall through to the SPA entry point for client-side routes.
  }

  try {
    const body = await readFile(join(root, "index.html"));
    send(response, 200, body, contentTypes[".html"]);
  } catch {
    send(response, 503, "Activity build is unavailable", "text/plain; charset=utf-8");
  }
});

server.listen(port, host, () => {
  console.log(`TicoMon Activity serving dist on ${host}:${port}`);
});

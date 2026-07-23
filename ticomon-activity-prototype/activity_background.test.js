import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  ACTIVITY_BACKGROUND_DIRECTORY,
  DEFAULT_ACTIVITY_BACKGROUND,
  activityBackgroundUrl,
  selectActivityBackground,
} from "./activity_background.js";

test("an existing shared battle background is selected through a relative URL", () => {
  const source = resolve(
    process.cwd(),
    "../rendering/assets/battle_bacgrounds",
    DEFAULT_ACTIVITY_BACKGROUND,
  );
  assert.equal(existsSync(source), true);
  assert.equal(
    selectActivityBackground([DEFAULT_ACTIVITY_BACKGROUND]),
    "/activity-backgrounds/bg-aquacordetown.jpg",
  );
  assert.equal(activityBackgroundUrl().startsWith("/"), true);
  assert.equal(activityBackgroundUrl().includes("C:"), false);
});

test("missing shared background falls back to a neutral Activity background", () => {
  assert.equal(selectActivityBackground([]), null);
  const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  assert.match(css, /background-color:\s*#334155/);
  assert.equal(ACTIVITY_BACKGROUND_DIRECTORY, "/activity-backgrounds");
});

test("Activity sprites cannot be enlarged beyond intrinsic dimensions", () => {
  const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  const spriteRule = css.match(/\.pokemon\s*\{([^}]+)\}/s)?.[1] || "";
  assert.match(spriteRule, /width:\s*auto/);
  assert.match(spriteRule, /height:\s*auto/);
  assert.match(spriteRule, /max-width:\s*42%/);
  assert.match(spriteRule, /max-height:\s*42%/);
  assert.doesNotMatch(spriteRule, /(?<!max-)width:\s*\d+%/);
  assert.doesNotMatch(spriteRule, /(?<!max-)height:\s*\d+%/);
});

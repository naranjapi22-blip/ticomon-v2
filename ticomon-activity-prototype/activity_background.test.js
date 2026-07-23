import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import {
  ACTIVITY_BACKGROUND_DIRECTORY,
  DEFAULT_ACTIVITY_BACKGROUND,
  applyActivityBackground,
  activityBackgroundUrl,
  selectActivityBackground,
} from "./activity_background.js";

const publicBackground = new URL(
  "./public/activity-backgrounds/bg-aquacordetown.jpg",
  import.meta.url,
);

test("an existing shared battle background is selected through a relative URL", () => {
  assert.equal(existsSync(publicBackground), true);
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

test("public background URL is not resolved as a Vite source import", () => {
  const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  assert.doesNotMatch(css, /activity-backgrounds/);
  assert.doesNotMatch(css, /url\(["']\.\//);
  const documentRef = {
    documentElement: { style: { setProperty: (_name, value) => { documentRef.value = value; } } },
  };
  applyActivityBackground(documentRef);
  assert.equal(documentRef.value, 'url("/activity-backgrounds/bg-aquacordetown.jpg")');
});

test("Activity sprites cannot be enlarged beyond intrinsic dimensions", () => {
  const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  const spriteRule = css.match(/\.pokemon\s*\{([^}]+)\}/s)?.[1] || "";
  assert.match(spriteRule, /width:\s*auto/);
  assert.match(spriteRule, /height:\s*auto/);
  assert.match(spriteRule, /max-width:\s*42%/);
  assert.match(spriteRule, /max-height:\s*clamp\(100px,\s*34%,\s*150px\)/);
  assert.doesNotMatch(spriteRule, /(?<!max-)width:\s*\d+%/);
  assert.doesNotMatch(spriteRule, /(?<!max-)height:\s*\d+%/);
});

test("battle stage and action panel are separate layout regions", () => {
  const html = readFileSync(new URL("./index.html", import.meta.url), "utf8");
  const battleShell = html.match(/id="battle-screen"[\s\S]*?<\/section>\s*<\/section>/)?.[0] || "";
  assert.match(html, /id="battle-screen" class="battle-shell"/);
  assert.ok(battleShell.indexOf('class="battle-stage"') < battleShell.indexOf('class="action-panel"'));
  const stage = battleShell.slice(
    battleShell.indexOf('<section class="battle-stage">'),
    battleShell.indexOf('<section class="action-panel">'),
  );
  assert.match(stage, /id="opponent" class="pokemon opponent"/);
  assert.match(stage, /id="player" class="pokemon player"/);

  const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  const actionRule = css.match(/\.action-panel\s*\{([^}]+)\}/s)?.[1] || "";
  assert.match(actionRule, /position:\s*relative/);
  assert.doesNotMatch(actionRule, /position:\s*absolute/);
  assert.match(css, /\.player\s*\{[^}]*bottom:\s*clamp\(85px,\s*18%,\s*150px\)/s);
  assert.match(css, /\.opponent\s*\{[^}]*top:\s*clamp\(90px,\s*26%,\s*150px\)/s);
  assert.match(css, /\.pokemon\s*\{[^}]*z-index:\s*2/);
  assert.match(css, /\.flash\s*\{[^}]*z-index:\s*3/);
  assert.match(css, /\.hud\s*\{[^}]*z-index:\s*4/);
});

test("the desktop shell gives the stage the flexible row and the panel its content row", () => {
  const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  assert.match(css, /\.battle-shell\s*\{[^}]*grid-template-rows:\s*minmax\(0,\s*1fr\)\s+auto/s);
  const desktopPanel = css.match(/\.action-panel\s*\{([^}]+)\}/s)?.[1] || "";
  assert.doesNotMatch(desktopPanel, /1fr/);
  assert.match(desktopPanel, /max-height:\s*min\(38vh,\s*240px\)/);
  assert.match(desktopPanel, /overflow-y:\s*auto/);
  assert.doesNotMatch(css, /\.battle-shell\s*\{[^}]*minmax\(120px/s);
});

test("mobile and short-landscape limits stay inside their responsive media queries", () => {
  const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  assert.match(css, /@media \(max-width: 520px\)[\s\S]*max-height:\s*min\(42vh,\s*230px\)/);
  const shortLandscape = css.match(
    /@media \(max-height: 460px\) and \(min-width: 521px\)\s*\{([\s\S]*?)\n\}/,
  )?.[1] || "";
  assert.match(shortLandscape, /\.action-panel\s*\{[\s\S]*max-height:\s*min\(34vh,\s*180px\)/);
  assert.doesNotMatch(shortLandscape, /\.battle-stage[\s\S]*max-height:\s*180px/);
  assert.doesNotMatch(shortLandscape, /\.battle-stage[\s\S]*height:/);
  assert.match(css, /\.action-panel\s*\{[^}]*overflow-y:\s*auto/s);
});

test("968x549 desktop keeps the stage flexible instead of applying the short limit", () => {
  const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  assert.match(css, /\.battle-shell\s*\{[^}]*grid-template-rows:\s*minmax\(0,\s*1fr\)\s+auto/s);
  assert.match(css, /@media \(max-height: 460px\) and \(min-width: 521px\)/);
  assert.match(css, /\.battle-stage\s*\{[^}]*min-height:\s*0/);
  assert.doesNotMatch(css, /\.battle-stage\s*\{[^}]*max-height:\s*180px/s);
});

test("short viewports keep separate sprite anchors while retaining a stage", () => {
  const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  assert.match(css, /\.opponent\s*\{[^}]*top:/s);
  assert.match(css, /\.player\s*\{[^}]*bottom:/s);
  assert.match(css, /\.action-panel\s*\{[^}]*overflow-y:\s*auto/s);
});

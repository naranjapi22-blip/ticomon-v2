import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  ActivityPresentationQueue,
  PRESENTATION_TIMINGS,
  presentationDelayFor,
  replaceSpriteAfterPreload,
  shouldExposeControls,
  shouldRestoreSnapshotImmediately,
} from "./activity_presentation.js";

test("startup markup has no fake Pokémon placeholders", () => {
  const html = readFileSync(new URL("./index.html", import.meta.url), "utf8");
  assert.doesNotMatch(html, /pikachu|charizard/i);
  assert.match(html, /id="opponent"[^>]*hidden/);
  assert.match(html, /id="player"[^>]*hidden/);
});

test("a real sprite replaces the neutral slot only after preload succeeds", async () => {
  const element = { src: "", hidden: true };
  class SuccessfulImage {
    set src(value) {
      this.value = value;
      this.onload();
    }
  }
  const pending = replaceSpriteAfterPreload(
    element,
    "/sprites/regular/25.gif",
    SuccessfulImage,
  );
  assert.equal(element.src, "");
  assert.equal(element.hidden, true);
  await pending;
  assert.equal(element.src, "/sprites/regular/25.gif");
  assert.equal(element.hidden, false);
});

test("a failed preload keeps the previous valid sprite", async () => {
  const element = { src: "/sprites/regular/25.gif", hidden: false };
  class FailedImage {
    set src(_value) {
      this.onerror();
    }
  }
  await assert.rejects(() => replaceSpriteAfterPreload(
    element,
    "/sprites/regular/6.gif",
    FailedImage,
  ));
  assert.equal(element.src, "/sprites/regular/25.gif");
  assert.equal(element.hidden, false);
});

test("submitting an action blocks controls immediately", () => {
  assert.equal(shouldExposeControls({ presentationBusy: false, pendingAction: true }), false);
  assert.equal(shouldExposeControls({ presentationBusy: true, pendingAction: false }), false);
});

test("next legal actions remain hidden until the presentation queue completes", async () => {
  let controlsVisible = false;
  let releasePause;
  const pause = new Promise((resolve) => { releasePause = resolve; });
  const queue = new ActivityPresentationQueue({
    present: async () => {},
    wait: () => pause,
    onStart: () => { controlsVisible = false; },
    onIdle: () => { controlsVisible = true; },
  });
  queue.enqueue({ type: "battle_snapshot", sequence: 2, phase: "waiting_for_actions" });
  await Promise.resolve();
  assert.equal(controlsVisible, false);
  releasePause();
  await queue.drainPromise;
  assert.equal(controlsVisible, true);
});

test("duplicate snapshots do not replay animations", async () => {
  let presentations = 0;
  const queue = new ActivityPresentationQueue({
    present: async () => { presentations += 1; },
    wait: async () => {},
  });
  queue.enqueue({ type: "battle_snapshot", sequence: 7, phase: "resolving" });
  assert.equal(queue.enqueue({ type: "battle_snapshot", sequence: 7, phase: "resolving" }), false);
  await queue.drainPromise;
  assert.equal(presentations, 1);
});

test("reconnect restores the current snapshot without replaying old turns", () => {
  assert.equal(
    shouldRestoreSnapshotImmediately({ reconnecting: true, hasSnapshot: true }),
    true,
  );
  assert.equal(
    shouldRestoreSnapshotImmediately({ reconnecting: false, hasSnapshot: true }),
    false,
  );
});

test("forced switches pause before controls return", () => {
  assert.equal(
    presentationDelayFor({ type: "battle_snapshot", phase: "forced_switch" }),
    PRESENTATION_TIMINGS.forcedSwitch,
  );
  assert.equal(PRESENTATION_TIMINGS.forcedSwitch, 800);
});

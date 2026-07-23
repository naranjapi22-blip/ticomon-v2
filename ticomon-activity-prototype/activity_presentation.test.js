import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  ActivityPresentationQueue,
  actionPromptFor,
  controlPhaseFor,
  controlOptionsFor,
  controlRenderKey,
  promptReadyTypeFor,
  preSnapshotMessage,
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

test("a snapshot received before its event is presented after that event", async () => {
  const order = [];
  const queue = new ActivityPresentationQueue({
    present: async (item) => order.push(item.type),
    wait: async () => {},
  });
  queue.enqueue({ type: "battle_snapshot", sequence: 12, phase: "resolving" });
  queue.enqueue({
    type: "battle_events",
    sequence: 11,
    index: 0,
    event: { kind: "move", move_name: "Tackle" },
  });
  await queue.drainPromise;
  assert.deepEqual(order, ["battle_events", "battle_snapshot"]);
});

test("terminal result is presented after the final snapshot", async () => {
  const order = [];
  const queue = new ActivityPresentationQueue({
    present: async (item) => { order.push(item.type); },
    wait: async () => {},
  });
  queue.enqueue({ type: "battle_snapshot", sequence: 10, phase: "finalizing" });
  queue.enqueue({
    type: "battle_finished",
    sequence: 11,
    reason: "normal",
    winner: { display_name: "Jorroco" },
  });
  await queue.drainPromise;
  assert.deepEqual(order, ["battle_snapshot", "battle_finished"]);
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
  assert.equal(PRESENTATION_TIMINGS.forcedSwitch, 0);
});

test("action reading and result timings meet the pacing floor", () => {
  assert.equal(PRESENTATION_TIMINGS.moveText, 800);
  assert.equal(PRESENTATION_TIMINGS.attack, 400);
  assert.equal(PRESENTATION_TIMINGS.impact, 400);
  assert.equal(PRESENTATION_TIMINGS.hp, 700);
  assert.equal(PRESENTATION_TIMINGS.notice, 800);
  assert.equal(PRESENTATION_TIMINGS.normalPause, 450);
  assert.equal(PRESENTATION_TIMINGS.finished, 2000);
});

test("effectiveness remains visible while HP is presented", () => {
  assert.equal(
    presentationDelayFor(
      { type: "battle_snapshot", phase: "resolving" },
      { type: "battle_events", event: { kind: "move", effectiveness: "super effective" } },
    ),
    PRESENTATION_TIMINGS.effectivenessPause,
  );
});

test("forced switch controls return immediately after the faint presentation", () => {
  assert.equal(
    presentationDelayFor(
      { type: "battle_snapshot", phase: "forced_switch" },
      { type: "battle_events", event: { kind: "move", fainted: true } },
    ),
    PRESENTATION_TIMINGS.faintPause,
  );
  assert.equal(PRESENTATION_TIMINGS.faintLead, 250);
});

test("reconnecting discards events waiting behind the current presentation", () => {
  const queue = new ActivityPresentationQueue({ present: async () => {} });
  queue.enqueue({ type: "battle_events", sequence: 12, index: 0, event: { kind: "move" } });
  queue.clearPending();
  assert.equal(queue.items.length, 0);
  assert.equal(queue.keys.size, 0);
});

test("forced-switch prompts distinguish local action, connected rival, and reconnect", () => {
  const legalSwitch = { moves: [], switches: [{ name: "Raichu" }], forced_switch: true };
  assert.equal(
    actionPromptFor({ legal: legalSwitch, phase: "forced_switch" }),
    "Choose a replacement Pokémon.",
  );
  assert.equal(
    actionPromptFor({
      legal: { forced_switch: true },
      phase: "forced_switch",
      requiredName: "Gin",
    }),
    "Gin is choosing a replacement.",
  );
  assert.equal(
    actionPromptFor({
      legal: { forced_switch: true },
      phase: "forced_switch",
      waitingForReconnect: true,
      requiredName: "Gin",
    }),
    "Waiting for Gin to reconnect.",
  );
});

test("pre-snapshot state waits instead of assigning an actor or exposing actions", () => {
  assert.equal(preSnapshotMessage(false), "Waiting for battle to start...");
  assert.equal(preSnapshotMessage(true), null);
});

test("control keys distinguish normal actions from forced switches", () => {
  const base = {
    sessionId: "session",
    turn: 1,
    requestId: "request-a",
    sequence: 4,
    actorId: "player-1",
  };
  assert.notEqual(
    controlRenderKey({ ...base, legal: { moves: [{ slot: 1 }] } }),
    controlRenderKey({ ...base, requestId: "request-b", legal: { forced_switch: true, switches: [{ slot: 1 }] } }),
  );
});

test("only local action phase exposes controls", () => {
  const common = { hasSnapshot: true, legal: { moves: [{ name: "Tackle" }] } };
  assert.equal(controlPhaseFor({ ...common, presentationBusy: true }), "presenting");
  assert.equal(controlPhaseFor({ ...common, presentationBusy: false, pendingAction: true }), "waiting_for_opponent");
  assert.equal(controlPhaseFor({ ...common, presentationBusy: false, pendingAction: false }), "waiting_for_local_action");
  assert.equal(controlPhaseFor({ hasSnapshot: true, presentationBusy: false, pendingAction: false, legal: {} }), "waiting_for_opponent");
});

test("forced switch controls contain only valid replacement options", () => {
  const options = controlOptionsFor({
    forced_switch: true,
    moves: [{ name: "should not appear" }],
    switches: [{ name: "Bench" }],
  });
  assert.deepEqual(options.moves, []);
  assert.deepEqual(options.switches, [{ name: "Bench" }]);
  assert.equal(promptReadyTypeFor(options), "forced_switch_prompt_ready");
  assert.equal(promptReadyTypeFor({ moves: [{ name: "Tackle" }] }), "action_prompt_ready");
});

test("a new legal action key is required before controls can be rebuilt", () => {
  const key = controlRenderKey({ sessionId: "session", turn: 1, requestId: "request", sequence: 4, actorId: "player-1", legal: { moves: [{ slot: 1 }] } });
  assert.equal(key, controlRenderKey({ sessionId: "session", turn: 1, requestId: "request", sequence: 4, actorId: "player-1", legal: { moves: [{ slot: 1 }] } }));
  assert.notEqual(key, controlRenderKey({ sessionId: "session", turn: 1, requestId: "request-2", sequence: 5, actorId: "player-1", legal: { moves: [{ slot: 1 }] } }));
});

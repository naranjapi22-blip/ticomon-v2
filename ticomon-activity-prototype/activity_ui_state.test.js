import test from "node:test";
import assert from "node:assert/strict";
import {
  isAuthorizedRole,
  resolveActivitySprite,
  shouldShowBlockingSetup,
} from "./activity_ui_state.js";

test("a snapshot stays visible during auth refresh or reconnect", () => {
  assert.equal(
    shouldShowBlockingSetup({ hasSnapshot: true }),
    false,
  );
  assert.equal(
    shouldShowBlockingSetup({ hasSnapshot: true }),
    false,
  );
});

test("initial setup remains blocking until initialization succeeds", () => {
  assert.equal(shouldShowBlockingSetup({ hasSnapshot: false }), true);
  assert.equal(
    shouldShowBlockingSetup({ hasSnapshot: true }),
    false,
  );
});

test("an auth refresh cannot restore the setup overlay after the first snapshot", () => {
  const ui = { hasSnapshot: false, setupVisible: true };

  ui.authenticating = true;
  assert.equal(shouldShowBlockingSetup(ui), true);
  ui.hasSnapshot = true;
  ui.authenticating = false;
  ui.setupVisible = shouldShowBlockingSetup(ui);
  assert.equal(ui.setupVisible, false);

  ui.refreshingAuthentication = true;
  ui.setupVisible = shouldShowBlockingSetup(ui);
  assert.equal(ui.setupVisible, false);

  ui.refreshingAuthentication = false;
  ui.authResponseReceived = true;
  ui.setupVisible = shouldShowBlockingSetup(ui);
  assert.equal(ui.setupVisible, false);
});

test("the backend-resolved Kadabra sprite URL is preserved", () => {
  const sprite = resolveActivitySprite({
    name: "Kadabra",
    sprite_url: "https://sprites.example/PVP/regular/kadabra.gif",
  });
  assert.equal(sprite.source, "https://sprites.example/PVP/regular/kadabra.gif");
  assert.equal(resolveActivitySprite({ name: "Kadabra" }).source, null);
});

test("one connected player does not make an authorized role unauthorized", () => {
  assert.equal(isAuthorizedRole("player1"), true);
  assert.equal(isAuthorizedRole("player2"), true);
  assert.equal(isAuthorizedRole("unauthorized"), false);
});

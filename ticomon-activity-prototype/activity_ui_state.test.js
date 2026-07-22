import test from "node:test";
import assert from "node:assert/strict";
import {
  isAuthorizedRole,
  resolveActivitySprite,
  shouldShowBlockingSetup,
} from "./activity_ui_state.js";

test("a snapshot stays visible during auth refresh or reconnect", () => {
  assert.equal(
    shouldShowBlockingSetup({ hasSnapshot: true, message: "Authenticating with Discord..." }),
    false,
  );
  assert.equal(
    shouldShowBlockingSetup({ hasSnapshot: true, message: "Reconnecting to the battle..." }),
    false,
  );
});

test("initial setup remains blocking until initialization succeeds", () => {
  assert.equal(
    shouldShowBlockingSetup({ hasSnapshot: false, message: "Authenticating with Discord..." }),
    true,
  );
  assert.equal(
    shouldShowBlockingSetup({ hasSnapshot: false, message: "Connected to the battle.", initialized: true }),
    false,
  );
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

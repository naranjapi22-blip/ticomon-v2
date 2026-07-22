import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  ACTIVITY_AUTH_STORAGE_KEY,
  clearCachedActivityAuth,
  isAuthorizedRole,
  resolveActivitySprite,
  setOverlayVisibility,
  shouldShowBlockingSetup,
} from "./activity_ui_state.js";
import { authenticateActivity } from "./activity_auth.js";

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

function fakeStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
    has: (key) => values.has(key),
  };
}

function fakeSdk(authorize) {
  return { commands: { authorize } };
}

test("a fresh launch calls Discord authorize when no backend session is verified", async () => {
  const storage = fakeStorage();
  let authorizeCalls = 0;
  const requests = [];
  const result = await authenticateActivity({
    sdk: fakeSdk(async () => {
      authorizeCalls += 1;
      return { code: "fresh-code" };
    }),
    clientId: "1234567890",
    channelId: "channel-1",
    storage,
    requestJson: async (path) => {
      requests.push(path);
      if (path.endsWith("challenge")) return { state: "state-1" };
      return { session_token: "fresh-token" };
    },
  });
  assert.equal(authorizeCalls, 1);
  assert.equal(result.auth.session_token, "fresh-token");
  assert.equal(requests.some((path) => path.includes("pvptest/session")), false);
});

test("stale cached auth is cleared and gets one fresh authorization", async () => {
  const storage = fakeStorage({
    [ACTIVITY_AUTH_STORAGE_KEY]: JSON.stringify({ session_token: "stale-token" }),
  });
  let authorizeCalls = 0;
  const result = await authenticateActivity({
    sdk: fakeSdk(async () => {
      authorizeCalls += 1;
      return { code: "fresh-code" };
    }),
    clientId: "1234567890",
    channelId: "channel-1",
    storage,
    requestJson: async (path) => {
      if (path.includes("pvptest/session")) throw new Error("401");
      if (path.endsWith("challenge")) return { state: "state-1" };
      return { session_token: "fresh-token" };
    },
  });
  assert.equal(authorizeCalls, 1);
  assert.equal(result.freshRetryUsed, true);
  assert.match(storage.getItem(ACTIVITY_AUTH_STORAGE_KEY), /fresh-token/);
});

test("a failed cached authorization cannot start an infinite fresh retry loop", async () => {
  const storage = fakeStorage({
    [ACTIVITY_AUTH_STORAGE_KEY]: JSON.stringify({ session_token: "stale-token" }),
  });
  let authorizeCalls = 0;
  await assert.rejects(() => authenticateActivity({
    sdk: fakeSdk(async () => {
      authorizeCalls += 1;
      return { code: "unexpected" };
    }),
    clientId: "1234567890",
    channelId: "channel-1",
    storage,
    freshRetryUsed: true,
    requestJson: async (path) => {
      if (path.includes("pvptest/session")) throw new Error("401");
      throw new Error("should not reach fresh authorization");
    },
  }));
  assert.equal(authorizeCalls, 0);
  clearCachedActivityAuth(storage);
  assert.equal(storage.has(ACTIVITY_AUTH_STORAGE_KEY), false);
});

test("successful authorization clears the setup overlay", () => {
  const element = {
    hidden: false,
    classList: { remove: (...names) => { element.removed = names; } },
    style: { removeProperty: (name) => { element.removedStyles ??= []; element.removedStyles.push(name); } },
    setAttribute: (name, value) => { element.attributes ??= {}; element.attributes[name] = value; },
  };
  setOverlayVisibility(element, false);
  assert.equal(element.hidden, true);
  assert.deepEqual(element.removed, ["visible", "active", "is-visible"]);
  assert.equal(element.attributes["aria-hidden"], "true");
  assert.deepEqual(element.removedStyles, ["display", "pointer-events"]);
});

test("hidden setup overlay is removed from layout and hit testing by CSS", () => {
  const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  assert.match(css, /\[hidden\]\s*\{[^}]*display:\s*none\s*!important;/s);
  assert.match(css, /\[hidden\]\s*\{[^}]*pointer-events:\s*none\s*!important;/s);
});

test("auth failure after a snapshot keeps the battle visible and interactive", () => {
  assert.equal(shouldShowBlockingSetup({ hasSnapshot: true }), false);
  const battle = { hidden: false };
  const setup = {
    hidden: false,
    classList: { remove: () => {} },
    style: { removeProperty: () => {} },
    setAttribute: () => {},
  };
  setOverlayVisibility(setup, false);
  assert.equal(battle.hidden, false);
  assert.equal(setup.hidden, true);
});

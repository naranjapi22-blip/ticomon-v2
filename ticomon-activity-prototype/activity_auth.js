import {
  cacheActivityAuth,
  clearCachedActivityAuth,
  readCachedActivityAuth,
} from "./activity_ui_state.js";

export async function authenticateActivity({
  sdk,
  clientId,
  channelId,
  requestJson,
  storage = globalThis.localStorage,
  freshRetryUsed = false,
  initialLaunch = false,
}) {
  const cached = readCachedActivityAuth(storage);
  if (cached) {
    try {
      await requestJson(
        `/api/activity/pvptest/session?channel_id=${encodeURIComponent(channelId)}`,
        { headers: { Authorization: `Bearer ${cached.session_token}` } },
      );
      return { auth: cached, freshRetryUsed };
    } catch (error) {
      clearCachedActivityAuth(storage);
      if (freshRetryUsed) {
        throw new Error("Cached Discord authorization is no longer valid.", { cause: error });
      }
      let auth;
      try {
        auth = await authorizeFresh({ sdk, clientId, requestJson });
      } catch (error) {
        error.freshRetryUsed = true;
        throw error;
      }
      cacheActivityAuth(storage, auth);
      return { auth, freshRetryUsed: true };
    }
  }

  if (freshRetryUsed) {
    throw new Error("Discord authorization retry limit reached.");
  }
  let auth;
  try {
    auth = await authorizeFresh({ sdk, clientId, requestJson });
  } catch (error) {
    if (!initialLaunch) {
      error.freshRetryUsed = true;
    }
    throw error;
  }
  cacheActivityAuth(storage, auth);
  return { auth, freshRetryUsed };
}

async function authorizeFresh({ sdk, clientId, requestJson }) {
  const challenge = await requestJson("/api/activity/auth/challenge");
  const { code } = await sdk.commands.authorize({
    client_id: clientId,
    response_type: "code",
    state: challenge.state,
    prompt: "consent",
    scope: ["identify"],
  });
  return requestJson("/api/activity/auth", {
    method: "POST",
    body: JSON.stringify({ code, state: challenge.state }),
  });
}

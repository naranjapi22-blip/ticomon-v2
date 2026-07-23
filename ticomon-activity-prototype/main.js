import { DiscordSDK } from "@discord/embedded-app-sdk";
import {
  clearCachedActivityAuth,
  isAuthorizedRole,
  resolveActivitySprite,
  setOverlayVisibility,
  shouldShowBlockingSetup,
} from "./activity_ui_state.js";
import { authenticateActivity } from "./activity_auth.js";
import {
  ActivityPresentationQueue,
  replaceSpriteAfterPreload,
  shouldRestoreSnapshotImmediately,
  shouldExposeControls,
} from "./activity_presentation.js";
import { applyActivityBackground } from "./activity_background.js";
import "./style.css";

applyActivityBackground();

const clientId = import.meta.env.VITE_DISCORD_CLIENT_ID?.trim();
const apiOrigin = import.meta.env.VITE_ACTIVITY_API_ORIGIN?.trim() || "";
const elements = {
  runtimeStatus: document.querySelector("#runtime-status"),
  connectionStatus: document.querySelector("#connection-status"),
  setupScreen: document.querySelector("#setup-screen"),
  setupMessage: document.querySelector("#setup-message"),
  setupDetail: document.querySelector("#setup-detail"),
  battleScreen: document.querySelector("#battle-screen"),
  playerName: document.querySelector("#player-name"),
  opponentName: document.querySelector("#opponent-name"),
  player: document.querySelector("#player"),
  opponent: document.querySelector("#opponent"),
  playerHp: document.querySelector("#player-hp"),
  opponentHp: document.querySelector("#opponent-hp"),
  playerHpText: document.querySelector("#player-hp-text"),
  opponentHpText: document.querySelector("#opponent-hp-text"),
  playerStatus: document.querySelector("#player-status"),
  opponentStatus: document.querySelector("#opponent-status"),
  playerTeam: document.querySelector("#player-team"),
  opponentTeam: document.querySelector("#opponent-team"),
  turnLabel: document.querySelector("#turn-label"),
  timerLabel: document.querySelector("#timer-label"),
  presenceLabel: document.querySelector("#presence-label"),
  message: document.querySelector("#message"),
  moves: document.querySelector("#moves"),
  switches: document.querySelector("#switches"),
  forfeit: document.querySelector("#forfeit"),
  flash: document.querySelector("#flash"),
  errorMessage: document.querySelector("#error-message"),
};

const state = {
  discordSdk: null,
  socket: null,
  sessionToken: null,
  role: "unauthorized",
  sequence: 0,
  pendingAction: false,
  deadline: null,
  phase: "initializing",
  snapshot: null,
  timer: null,
  reconnecting: false,
  reconnectAttempt: 0,
  authenticating: false,
  intentionalSocketClose: false,
  freshAuthRetryUsed: false,
  presentationBusy: false,
  restoringSnapshot: false,
  snapshotReceived: false,
};

const presentationQueue = new ActivityPresentationQueue({
  present: presentQueuedMessage,
  onStart: () => {
    state.presentationBusy = true;
    hideActionControls();
  },
  onIdle: () => {
    state.presentationBusy = false;
    renderControls(state.snapshot?.legal_actions);
  },
});

elements.forfeit.addEventListener("click", () => {
  if (state.pendingAction || !state.socket || state.socket.readyState !== WebSocket.OPEN) {
    return;
  }
  if (window.confirm("Forfeit this PvP battle?")) {
    send({ type: "forfeit" });
  }
});

async function initialize() {
  if (!isValidClientId(clientId) || !isLikelyActivity()) {
    setRuntime("Browser preview");
    showSetup(
      "Open this page from the TicoMon Activity in Discord.",
      "Browser preview does not create or simulate a real PvP battle.",
    );
    return;
  }

  try {
    setRuntime("Discord Activity");
    setSetup("Connecting to Discord...", "Waiting for the Embedded App SDK.");
    state.discordSdk = new DiscordSDK(clientId);
    await state.discordSdk.ready();
    await subscribeToActivityPresence();
    const authenticated = await authenticate(true);
    state.sessionToken = authenticated.auth.session_token;
    connectSocket();
  } catch (error) {
    console.error("Activity initialization failed.", error);
    setRuntime("Activity error");
    showConnectionFailure("Activity initialization failed.", error.message || "Try reopening the Activity.");
  }
}

async function subscribeToActivityPresence() {
  try {
    const participants = await state.discordSdk.commands.getInstanceConnectedParticipants();
    updateSdkPresence(participants);
    await state.discordSdk.subscribe(
      "ACTIVITY_INSTANCE_PARTICIPANTS_UPDATE",
      (event) => updateSdkPresence(event.participants),
    );
  } catch (error) {
    console.debug("Discord participant presence is unavailable.", error);
  }
}

function updateSdkPresence(participants) {
  if (Array.isArray(participants)) {
    elements.presenceLabel.textContent = `${participants.length}/2 players connected`;
  }
}

async function authenticate(initialLaunch = false) {
  state.authenticating = true;
  showConnectionState("Authenticating with Discord...");
  try {
    const authenticated = await authenticateActivity({
      sdk: state.discordSdk,
      clientId,
      channelId: state.discordSdk.channelId,
      requestJson,
      freshRetryUsed: state.freshAuthRetryUsed,
      initialLaunch,
    });
    state.freshAuthRetryUsed = authenticated.freshRetryUsed;
    state.sessionToken = authenticated.auth.session_token;
    clearActivityOverlay("Connecting to the battle...");
    return authenticated;
  } finally {
    state.authenticating = false;
  }
}

function connectSocket() {
  const wasReconnecting = state.reconnecting;
  state.reconnecting = false;
  state.restoringSnapshot = wasReconnecting && Boolean(state.snapshot);
  if (!wasReconnecting && !state.snapshot) {
    state.sequence = 0;
  }
  if (state.snapshot) {
    showConnectionState("Reconnecting to the battle...");
  }
  const wsUrl = new URL("/api/activity/pvptest/ws", apiOrigin || window.location.origin);
  wsUrl.protocol = wsUrl.protocol === "https:" ? "wss:" : "ws:";
  state.socket = new WebSocket(wsUrl);
  state.socket.addEventListener("open", () => {
    if (state.snapshot) {
      showConnectionState("Syncing the current battle...");
    }
    state.socket.send(JSON.stringify({
      type: "authenticate",
      session_token: state.sessionToken,
      instance_id: state.discordSdk.instanceId,
      channel_id: state.discordSdk.channelId,
      guild_id: state.discordSdk.guildId,
    }));
  });
  state.socket.addEventListener("message", (event) => {
    try {
      handleServerMessage(JSON.parse(event.data));
    } catch (error) {
      showError("The Activity received an invalid server update.");
      console.error("Invalid Activity server message.", error);
    }
  });
  state.socket.addEventListener("close", () => {
    if (state.intentionalSocketClose) {
      state.intentionalSocketClose = false;
      return;
    }
    if (state.phase === "finished" || state.phase === "unauthorized") {
      return;
    }
    state.reconnecting = true;
    setRuntime("Reconnecting");
    showConnectionState("Reconnecting to the battle...");
    window.setTimeout(connectSocket, Math.min(5000, 500 * 2 ** state.reconnectAttempt++));
  });
  state.socket.addEventListener("error", () => {
    setRuntime("Reconnecting");
  });
}

function handleServerMessage(message) {
  if (message.type === "no_active_session") {
    state.phase = "no_session";
    showSetup("No active !pvptest battle in this channel.", "Run !pvptest in the same Discord channel and complete team selection first.");
    return;
  }
  if (message.type === "error") {
    showError(message.message);
    if (message.message?.toLowerCase().includes("expired")) {
      refreshAuthentication();
      return;
    }
    if (message.message?.includes("not a player")) {
      state.phase = "unauthorized";
      showSetup("Unauthorized Activity user.", "Only the two selected !pvptest players can control this battle.");
    }
    return;
  }
  if (message.type === "connection_ready") {
    state.role = message.role;
    if (isAuthorizedRole(state.role)) {
      clearActivityOverlay("Connected to the battle.");
    } else {
      state.phase = "unauthorized";
      showSetup("Unauthorized Activity user.", "You can observe the Activity, but only the selected players can act.");
    }
    return;
  }
  if (message.type === "session_state") {
    state.role = message.role;
    state.phase = message.phase;
    elements.presenceLabel.textContent = `${message.players_connected}/${message.players_expected} players connected`;
    const players = Object.fromEntries(
      (message.players || []).map((player) => [player.role, player.name]),
    );
    if (state.role === "player1" || state.role === "player2") {
      const opponentRole = state.role === "player1" ? "player2" : "player1";
      elements.playerName.textContent = players[state.role] || "You";
      elements.opponentName.textContent = players[opponentRole] || "Opponent";
    }
    if (state.role === "unauthorized") {
      showSetup("Unauthorized Activity user.", "You can observe the Activity, but only the selected players can act.");
    } else {
      clearActivityOverlay("Connected to the battle.");
      elements.message.textContent = phaseMessage(message.phase);
    }
    return;
  }
  if (
    message.sequence !== undefined &&
    message.sequence <= state.sequence &&
    !(message.type === "battle_snapshot" && state.restoringSnapshot)
  ) {
    return;
  }
  if (message.sequence !== undefined) {
    state.sequence = message.sequence;
  }
  if (message.type === "battle_snapshot") {
    if (shouldRestoreSnapshotImmediately({
      reconnecting: state.restoringSnapshot,
      hasSnapshot: Boolean(state.snapshot),
    })) {
      state.restoringSnapshot = false;
      presentSnapshot(message, { restore: true });
    } else {
      presentationQueue.enqueue({ ...message, initial: !state.snapshotReceived });
      state.snapshotReceived = true;
    }
  } else if (message.type === "battle_events") {
    message.events?.forEach((event, index) => {
      presentationQueue.enqueue({
        type: "battle_events",
        sequence: message.sequence,
        index,
        event,
      });
    });
  } else if (message.type === "battle_finished") {
    presentationQueue.enqueue(message);
  }
}

async function presentQueuedMessage(item) {
  if (item.type === "battle_snapshot") {
    await presentSnapshot(item);
  } else if (item.type === "battle_events") {
    elements.message.textContent = item.event.message || item.event.kind;
    animateEvent(item.event);
  } else if (item.type === "battle_finished") {
    state.phase = "finished";
    state.pendingAction = true;
    elements.message.textContent = item.winner
      ? `${item.winner.display_name || "The winner"} won. Reason: ${item.reason}.`
      : `Battle finished. Reason: ${item.reason}.`;
    hideActionControls();
  }
}

async function presentSnapshot(snapshot, { restore = false } = {}) {
  state.snapshot = snapshot;
  state.phase = snapshot.phase;
  state.deadline = snapshot.deadline;
  state.pendingAction = false;
  clearActivityOverlay("");
  await renderSnapshot(snapshot);
  if (restore) {
    renderControls(snapshot.legal_actions);
  }
}

async function renderSnapshot(snapshot) {
  showBattle();
  elements.turnLabel.textContent = `Turn ${snapshot.turn}`;
  elements.message.textContent = snapshot.message?.message || phaseMessage(snapshot.phase);
  await Promise.all([
    renderPokemon(elements.player, snapshot.self),
    renderPokemon(elements.opponent, snapshot.opponent),
  ]);
  renderHp(elements.playerHp, elements.playerHpText, snapshot.self);
  renderHp(elements.opponentHp, elements.opponentHpText, snapshot.opponent);
  elements.playerStatus.textContent = snapshot.self?.status || "";
  elements.opponentStatus.textContent = snapshot.opponent?.status || "";
  renderTeam(elements.playerTeam, snapshot.self_team, snapshot.self_remaining);
  renderTeam(elements.opponentTeam, snapshot.opponent_team, snapshot.opponent_remaining);
}

async function renderPokemon(element, pokemon) {
  const sprite = resolveActivitySprite(pokemon);
  if (!sprite.source) {
    return;
  }
  try {
    await replaceSpriteAfterPreload(element, sprite.source);
    element.alt = sprite.alt;
    element.classList.remove("sprite-missing");
    element.removeAttribute("data-sprite-error");
  } catch (error) {
    if (!element.src) element.hidden = true;
    console.debug("Activity sprite preload failed.", error);
  }
}
function markSpriteMissing(element) {
  element.hidden = true;
  element.classList.add("sprite-missing");
  element.dataset.spriteError = "true";
  showError(`Could not load ${element.alt || "battle sprite"}.`);
}

function renderHp(fill, text, pokemon) {
  if (!pokemon) {
    fill.style.width = "0";
    fill.classList.remove("critical");
    text.textContent = "—";
    return;
  }
  const current = pokemon?.hp_current ?? 0;
  const maximum = pokemon?.hp_max || 1;
  const percent = Math.max(0, Math.min(100, (current / maximum) * 100));
  fill.style.width = `${percent}%`;
  fill.classList.toggle("critical", percent <= 25);
  text.textContent = `${current}/${maximum}`;
}

function renderTeam(element, team, remaining) {
  element.replaceChildren();
  if (!Array.isArray(team)) return;
  const count = team.length;
  for (let index = 0; index < count; index += 1) {
    const marker = document.createElement("span");
    marker.className = index < remaining ? "team-alive" : "team-fainted";
    marker.textContent = index < remaining ? "●" : "×";
    element.append(marker);
  }
}

function renderControls(legal = { moves: [], switches: [], forced_switch: false }) {
  if (!shouldExposeControls(state)) {
    hideActionControls();
    return;
  }
  elements.moves.hidden = false;
  elements.switches.hidden = false;
  elements.moves.replaceChildren();
  elements.switches.replaceChildren();
  const controlsDisabled = state.role === "unauthorized" || state.pendingAction || state.phase === "finished";
  legal.moves?.forEach((move) => elements.moves.append(actionButton(move, "choose_move", controlsDisabled)));
  legal.switches?.forEach((switchAction) => elements.switches.append(actionButton(switchAction, "choose_switch", controlsDisabled)));
  elements.forfeit.disabled = controlsDisabled;
}

function hideActionControls() {
  elements.moves.hidden = true;
  elements.switches.hidden = true;
  elements.forfeit.disabled = true;
}

function actionButton(action, type, disabled) {
  const button = document.createElement("button");
  button.type = "button";
  button.disabled = disabled;
  button.textContent = type === "choose_move" ? action.name : `Switch: ${action.name}`;
  button.title = action.detail || action.category || "Server-validated action";
  button.addEventListener("click", () => {
    if (state.pendingAction) {
      return;
    }
    state.pendingAction = true;
    hideActionControls();
    elements.message.textContent = "Waiting for opponent...";
    send({ type, slot: action.slot });
  });
  return button;
}

function send(message) {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    showError("The Activity is not connected to the battle server.");
    state.pendingAction = false;
    return;
  }
  state.socket.send(JSON.stringify(message));
}

function animateEvent(event) {
  restartAnimation(elements.flash, "screen-flash");
  if (["move", "damage", "faint"].includes(event.kind)) {
    restartAnimation(elements.player, "player-attacking");
    restartAnimation(elements.opponent, "opponent-hit");
  }
}

function restartAnimation(element, className) {
  element.classList.remove(className);
  void element.offsetWidth;
  element.classList.add(className);
  element.addEventListener("animationend", () => element.classList.remove(className), { once: true });
}

function setRuntime(label) {
  elements.runtimeStatus.textContent = label;
  elements.runtimeStatus.dataset.mode = label === "Discord Activity" ? "activity" : "preview";
}

function setSetup(message, detail) {
  elements.setupMessage.textContent = message;
  elements.setupDetail.textContent = detail;
}

function showConnectionState(message, isError = false) {
  if (!shouldShowBlockingSetup({ hasSnapshot: Boolean(state.snapshot) })) {
    showNonBlockingConnectionStatus(message, isError);
    return;
  }
  setSetup(message, "The backend remains authoritative for the current battle state.");
  setOverlayVisibility(elements.setupScreen, true);
  elements.battleScreen.hidden = true;
}

function clearActivityOverlay(status = "") {
  setOverlayVisibility(elements.setupScreen, false);
  elements.battleScreen.hidden = false;
  elements.connectionStatus.hidden = !status;
  elements.connectionStatus.textContent = status;
  elements.connectionStatus.dataset.state = "info";
}

function showNonBlockingConnectionStatus(message, isError = false) {
  elements.connectionStatus.hidden = !message;
  elements.connectionStatus.textContent = message;
  elements.connectionStatus.dataset.state = isError ? "error" : "info";
  showBattle();
}

function showConnectionFailure(message, detail) {
  if (state.snapshot) {
    showConnectionState(message, true);
    showError(detail);
    return;
  }
  showSetup(message, detail);
}

function showSetup(message, detail) {
  if (!shouldShowBlockingSetup({ hasSnapshot: Boolean(state.snapshot) })) {
    showNonBlockingConnectionStatus(message, true);
    return;
  }
  setSetup(message, detail);
  setOverlayVisibility(elements.setupScreen, true);
  elements.battleScreen.hidden = true;
}

function showBattle() {
  setOverlayVisibility(elements.setupScreen, false);
  elements.battleScreen.hidden = false;
}

function showError(message) {
  elements.errorMessage.hidden = false;
  elements.errorMessage.textContent = message;
}

async function refreshAuthentication() {
  if (state.authenticating) {
    return;
  }
  try {
    showConnectionState("Refreshing Discord authorization...");
    await authenticate();
    state.intentionalSocketClose = true;
    state.socket?.close();
    connectSocket();
  } catch (error) {
    if (error.freshRetryUsed) {
      state.freshAuthRetryUsed = true;
    }
    clearCachedActivityAuth(window.localStorage);
    console.error("Activity authorization refresh failed.", error);
    showConnectionFailure("Activity authorization failed.", error.message || "Try reopening the Activity.");
  }
}

function phaseMessage(phase) {
  return {
    starting: "Starting the Showdown battle...",
    waiting_for_actions: "Choose your next action.",
    forced_switch: "Choose a replacement Pokémon.",
    resolving: "Resolving turn...",
    finalizing: "Finishing battle...",
    finished: "Battle finished.",
  }[phase] || "Waiting for the battle server.";
}

function isValidClientId(value) {
  return Boolean(value && /^\d{10,}$/.test(value));
}

function isLikelyActivity() {
  try {
    return /Discord/i.test(navigator.userAgent) || window.self !== window.top;
  } catch {
    return false;
  }
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${apiOrigin}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || "Activity API request failed.");
  }
  return body;
}

function startTimer() {
  window.clearInterval(state.timer);
  state.timer = window.setInterval(() => {
    const remaining = state.deadline ? Math.max(0, Math.ceil((Date.parse(state.deadline) - Date.now()) / 1000)) : null;
    elements.timerLabel.textContent = remaining === null ? "Waiting" : `${remaining}s`;
  }, 250);
}

[elements.player, elements.opponent].forEach((element) => {
  element.addEventListener("error", () => markSpriteMissing(element));
});

startTimer();
initialize();

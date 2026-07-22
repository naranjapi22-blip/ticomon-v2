import { DiscordSDK } from "@discord/embedded-app-sdk";
import "./style.css";

const clientId = import.meta.env.VITE_DISCORD_CLIENT_ID?.trim();
const apiOrigin = import.meta.env.VITE_ACTIVITY_API_ORIGIN?.trim() || "";
const elements = {
  runtimeStatus: document.querySelector("#runtime-status"),
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
};

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
    await authenticate();
    connectSocket();
  } catch (error) {
    console.error("Activity initialization failed.", error);
    setRuntime("Activity error");
    showSetup("Activity initialization failed.", error.message || "Try reopening the Activity.");
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

async function authenticate() {
  setSetup("Authenticating with Discord...", "The server verifies the Discord identity before matching the battle.");
  const challenge = await requestJson("/api/activity/auth/challenge");
  const { code } = await state.discordSdk.commands.authorize({
    client_id: clientId,
    response_type: "code",
    state: challenge.state,
    prompt: "none",
    scope: ["identify"],
  });
  const auth = await requestJson("/api/activity/auth", {
    method: "POST",
    body: JSON.stringify({ code, state: challenge.state }),
  });
  state.sessionToken = auth.session_token;
}

function connectSocket() {
  state.reconnecting = false;
  state.sequence = 0;
  const wsUrl = new URL("/api/activity/pvptest/ws", apiOrigin || window.location.origin);
  wsUrl.protocol = wsUrl.protocol === "https:" ? "wss:" : "ws:";
  state.socket = new WebSocket(wsUrl);
  state.socket.addEventListener("open", () => {
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
    if (state.phase === "finished" || state.phase === "unauthorized") {
      return;
    }
    state.reconnecting = true;
    setRuntime("Reconnecting");
    setSetup("Reconnecting to the battle...", "Your next snapshot will restore the current server state.");
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
    if (message.message?.includes("not a player")) {
      state.phase = "unauthorized";
      showSetup("Unauthorized Activity user.", "Only the two selected !pvptest players can control this battle.");
    }
    return;
  }
  if (message.type === "connection_ready") {
    state.role = message.role;
    if (state.role === "unauthorized") {
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
      showBattle();
      elements.message.textContent = phaseMessage(message.phase);
    }
    return;
  }
  if (message.sequence !== undefined && message.sequence <= state.sequence) {
    return;
  }
  if (message.sequence !== undefined) {
    state.sequence = message.sequence;
  }
  if (message.type === "battle_snapshot") {
    state.snapshot = message;
    state.phase = message.phase;
    state.pendingAction = false;
    state.deadline = message.deadline;
    renderSnapshot(message);
  } else if (message.type === "battle_events") {
    state.pendingAction = false;
    const event = message.events?.at(-1);
    if (event) {
      elements.message.textContent = event.message || event.kind;
      animateEvent(event);
    }
  } else if (message.type === "battle_finished") {
    state.phase = "finished";
    state.pendingAction = true;
    elements.message.textContent = message.winner
      ? `${message.winner.display_name || "The winner"} won. Reason: ${message.reason}.`
      : `Battle finished. Reason: ${message.reason}.`;
    renderControls();
  }
}

function renderSnapshot(snapshot) {
  showBattle();
  elements.turnLabel.textContent = `Turn ${snapshot.turn}`;
  elements.message.textContent = snapshot.message?.message || phaseMessage(snapshot.phase);
  renderPokemon(elements.player, snapshot.self, true);
  renderPokemon(elements.opponent, snapshot.opponent, false);
  renderHp(elements.playerHp, elements.playerHpText, snapshot.self);
  renderHp(elements.opponentHp, elements.opponentHpText, snapshot.opponent);
  elements.playerStatus.textContent = snapshot.self?.status || "";
  elements.opponentStatus.textContent = snapshot.opponent?.status || "";
  renderTeam(elements.playerTeam, snapshot.self_team, snapshot.self_remaining);
  renderTeam(elements.opponentTeam, snapshot.opponent_team, snapshot.opponent_remaining);
  renderControls(snapshot.legal_actions);
}

function renderPokemon(element, pokemon, playerSide) {
  if (!pokemon?.sprite_url) {
    return;
  }
  element.src = pokemon.sprite_url;
  element.alt = pokemon.name || (playerSide ? "Your Pokémon" : "Opponent Pokémon");
}

function renderHp(fill, text, pokemon) {
  const current = pokemon?.hp_current ?? 0;
  const maximum = pokemon?.hp_max || 1;
  const percent = Math.max(0, Math.min(100, (current / maximum) * 100));
  fill.style.width = `${percent}%`;
  fill.classList.toggle("critical", percent <= 25);
  text.textContent = `${current}/${maximum}`;
}

function renderTeam(element, team, remaining) {
  element.replaceChildren();
  const count = Math.max(team?.length || 0, 3);
  for (let index = 0; index < count; index += 1) {
    const marker = document.createElement("span");
    marker.className = index < remaining ? "team-alive" : "team-fainted";
    marker.textContent = index < remaining ? "●" : "×";
    element.append(marker);
  }
}

function renderControls(legal = { moves: [], switches: [], forced_switch: false }) {
  elements.moves.replaceChildren();
  elements.switches.replaceChildren();
  const controlsDisabled = state.role === "unauthorized" || state.pendingAction || state.phase === "finished";
  legal.moves?.forEach((move) => elements.moves.append(actionButton(move, "choose_move", controlsDisabled)));
  legal.switches?.forEach((switchAction) => elements.switches.append(actionButton(switchAction, "choose_switch", controlsDisabled)));
  elements.forfeit.disabled = controlsDisabled;
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
    renderControls(state.snapshot?.legal_actions);
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

function showSetup(message, detail) {
  setSetup(message, detail);
  elements.setupScreen.hidden = false;
  elements.battleScreen.hidden = true;
}

function showBattle() {
  elements.setupScreen.hidden = true;
  elements.battleScreen.hidden = false;
}

function showError(message) {
  elements.errorMessage.hidden = false;
  elements.errorMessage.textContent = message;
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
  element.addEventListener("error", () => showError(`Could not load ${element.alt || "battle sprite"}.`));
});

startTimer();
initialize();

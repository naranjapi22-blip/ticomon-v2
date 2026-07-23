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
  actionPromptFor,
  preSnapshotMessage,
  replaceSpriteAfterPreload,
  shouldRestoreSnapshotImmediately,
  controlPhaseFor,
  controlOptionsFor,
  controlRenderKey,
  promptReadyTypeFor,
} from "./activity_presentation.js";
import { applyActivityBackground } from "./activity_background.js";
import {
  ANIMATION_TIMINGS,
  clearImpactFlash,
  eventAnimationPlan,
  reduceAnimationPlan,
} from "./activity_animation.js";
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
  actionPrompt: document.querySelector("#action-prompt"),
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
  playersConnected: 0,
  requiredUserId: null,
  waitingForReconnect: false,
  localUserId: null,
  playerNames: {},
  snapshot: null,
  authoritativeSnapshot: null,
  timer: null,
  reconnecting: false,
  reconnectAttempt: 0,
  authenticating: false,
  intentionalSocketClose: false,
  freshAuthRetryUsed: false,
  presentationBusy: false,
  restoringSnapshot: false,
  snapshotReceived: false,
  pendingSwitchSide: null,
  pendingFaintSide: null,
  preserveSnapshotMessage: false,
  promptAckKey: null,
  controlPhase: "waiting_for_start",
  controlsRenderKey: null,
  controlsSessionId: null,
  hpValues: { player: null, opponent: null },
};

const presentationQueue = new ActivityPresentationQueue({
  present: presentQueuedMessage,
  onStart: () => {
    state.presentationBusy = true;
    updateControlPresentation("presentation_start");
  },
  onIdle: () => {
    state.presentationBusy = false;
    renderControls(
      state.authoritativeSnapshot?.legal_actions || state.snapshot?.legal_actions,
      "presentation_idle",
    );
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
  if (wasReconnecting) {
    presentationQueue.clearPending();
    state.preserveSnapshotMessage = false;
    state.promptAckKey = null;
  }
  state.restoringSnapshot = wasReconnecting && Boolean(state.snapshot);
  if (!wasReconnecting && !state.snapshot) {
    state.sequence = 0;
  }
  if (state.snapshot) {
    showConnectionState("Reconnecting to the battle...");
  }
  const wsUrl = new URL("/api/activity/pvptest/ws", apiOrigin || window.location.origin);
  wsUrl.protocol = wsUrl.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(wsUrl);
  state.socket = socket;
  socket.addEventListener("open", () => {
    if (state.socket !== socket) return;
    if (state.snapshot) {
      showConnectionState("Syncing the current battle...");
    }
    socket.send(JSON.stringify({
      type: "authenticate",
      session_token: state.sessionToken,
      instance_id: state.discordSdk.instanceId,
      channel_id: state.discordSdk.channelId,
      guild_id: state.discordSdk.guildId,
    }));
  });
  socket.addEventListener("message", (event) => {
    if (state.socket !== socket) return;
    try {
      handleServerMessage(JSON.parse(event.data));
    } catch (error) {
      showError("The Activity received an invalid server update.");
      console.error("Invalid Activity server message.", error);
    }
  });
  socket.addEventListener("close", (event) => {
    if (state.socket !== socket) return;
    if (state.intentionalSocketClose) {
      state.intentionalSocketClose = false;
      return;
    }
    if (state.phase === "finished" || state.phase === "unauthorized") {
      return;
    }
    console.warn("PvP Activity WebSocket closed", {
      code: event.code,
      reason: event.reason || "",
      phase: state.phase,
    });
    state.reconnecting = true;
    setRuntime("Reconnecting");
    showConnectionState("Reconnecting to the battle...");
    window.setTimeout(connectSocket, Math.min(5000, 500 * 2 ** state.reconnectAttempt++));
  });
  socket.addEventListener("error", () => {
    if (state.socket !== socket) return;
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
  if (message.type === "startup_error") {
    state.phase = "startup_error";
    state.pendingAction = true;
    updateControlPresentation("startup_error");
    showConnectionFailure(
      "The battle could not start.",
      message.message || "The server timed out before the first battle snapshot.",
    );
    return;
  }
  if (message.type === "session_closed") {
    if (!state.snapshot) {
      state.phase = "closed";
      showConnectionFailure(
        "The battle session was closed.",
        "No first battle snapshot was received.",
      );
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
    state.playersConnected = message.players_connected || 0;
    state.requiredUserId = message.required_user_id ?? null;
    state.waitingForReconnect = Boolean(message.waiting_for_reconnect);
    elements.presenceLabel.textContent = `${message.players_connected}/${message.players_expected} players connected`;
    const players = Object.fromEntries(
      (message.players || []).map((player) => [player.role, player.name]),
    );
    state.playerNames = Object.fromEntries(
      (message.players || []).map((player) => [player.user_id, player.name]),
    );
    if (state.role === "player1" || state.role === "player2") {
      const opponentRole = state.role === "player1" ? "player2" : "player1";
      const localPlayer = (message.players || []).find((player) => player.role === state.role);
      state.localUserId = localPlayer?.user_id ?? null;
      elements.playerName.textContent = players[state.role] || "You";
      elements.opponentName.textContent = players[opponentRole] || "Opponent";
    }
    if (state.role === "unauthorized") {
      showSetup("Unauthorized Activity user.", "You can observe the Activity, but only the selected players can act.");
    } else {
      clearActivityOverlay("Connected to the battle.");
      if (!state.snapshotReceived && !state.snapshot) {
        const waitingMessage = preSnapshotMessage(false);
        elements.message.textContent = waitingMessage;
        elements.actionPrompt.textContent = waitingMessage;
        updateControlPresentation("session_state_before_snapshot");
      } else {
        elements.message.textContent = phaseMessage(message.phase);
        updateControlPresentation("session_state");
      }
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
  if (message.type === "battle_snapshot") {
    state.authoritativeSnapshot = message;
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
    await presentBattleEvent(item.event);
  } else if (item.type === "battle_finished") {
    state.phase = "finished";
    state.pendingAction = true;
    elements.message.textContent = item.winner
      ? `${item.winner.display_name || "The winner"} won. Reason: ${item.reason}.`
      : `Battle finished. Reason: ${item.reason}.`;
    updateControlPresentation("battle_finished");
  }
  if (item.sequence !== undefined) {
    state.sequence = Math.max(state.sequence, item.sequence);
  }
}

async function presentSnapshot(snapshot, { restore = false } = {}) {
  state.snapshot = snapshot;
  state.phase = snapshot.phase;
  state.deadline = snapshot.deadline;
  state.pendingAction = false;
  clearActivityOverlay("");
  await renderSnapshot(snapshot, { animate: !restore });
  if (snapshot.sequence !== undefined) {
    state.sequence = Math.max(state.sequence, snapshot.sequence);
  }
  if (restore) {
    renderControls(snapshot.legal_actions, "snapshot_restore");
  }
}

async function renderSnapshot(snapshot, { animate = true } = {}) {
  showBattle();
  elements.turnLabel.textContent = `Turn ${snapshot.turn}`;
  if (!state.preserveSnapshotMessage) {
    elements.message.textContent = snapshot.message?.message || phaseMessage(snapshot.phase);
  }
  await Promise.all([
    renderPokemon(elements.player, snapshot.self, "player", false),
    renderPokemon(elements.opponent, snapshot.opponent, "opponent", false),
  ]);
  await Promise.all([
    renderHp(elements.playerHp, elements.playerHpText, snapshot.self, "player", animate),
    renderHp(elements.opponentHp, elements.opponentHpText, snapshot.opponent, "opponent", animate),
  ]);
  if (state.pendingSwitchSide) {
    const switched = elementForSide(state.pendingSwitchSide);
    if (switched) {
      switched.hidden = false;
      await playAnimation(switched, "switching-in", ANIMATION_TIMINGS.switchIn);
    }
  }
  if (state.pendingFaintSide) {
    const fainted = elementForSide(state.pendingFaintSide);
    if (fainted) fainted.hidden = true;
  }
  state.pendingSwitchSide = null;
  state.pendingFaintSide = null;
  state.preserveSnapshotMessage = false;
  elements.playerStatus.textContent = snapshot.self?.status || "";
  elements.opponentStatus.textContent = snapshot.opponent?.status || "";
  renderTeam(elements.playerTeam, snapshot.self_team, snapshot.self_remaining);
  renderTeam(elements.opponentTeam, snapshot.opponent_team, snapshot.opponent_remaining);
}

async function renderPokemon(element, pokemon, side, animate) {
  const sprite = resolveActivitySprite(pokemon);
  if (!sprite.source) {
    return;
  }
  try {
    await replaceSpriteAfterPreload(element, sprite.source);
    element.classList.remove("fainting", "switching-out", "switching-in");
    if (
      state.pendingSwitchSide === side ||
      state.pendingFaintSide === side
    ) {
      element.hidden = true;
    }
    element.alt = sprite.alt;
    element.classList.remove("sprite-missing");
    element.removeAttribute("data-sprite-error");
    if (animate && state.pendingSwitchSide === side) {
      await playAnimation(element, "switching-in", ANIMATION_TIMINGS.switchIn);
    }
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

async function renderHp(fill, text, pokemon, side, animate) {
  if (!pokemon) {
    fill.style.width = "0";
    fill.classList.remove("critical");
    text.textContent = "—";
    state.hpValues[side] = null;
    return;
  }
  const current = pokemon?.hp_current ?? 0;
  const maximum = pokemon?.hp_max || 1;
  const percent = Math.max(0, Math.min(100, (current / maximum) * 100));
  const previous = state.hpValues[side];
  if (animate && previous !== null && previous !== percent) {
    fill.style.width = `${previous}%`;
    void fill.offsetWidth;
    fill.style.width = `${percent}%`;
    await wait(ANIMATION_TIMINGS.hp);
  } else {
    fill.style.width = `${percent}%`;
  }
  state.hpValues[side] = percent;
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

function renderControls(legal = { moves: [], switches: [], forced_switch: false }, reason = "unknown") {
  const hasSnapshot = Boolean(state.snapshotReceived || state.snapshot);
  const phase = controlPhaseFor({
    hasSnapshot,
    presentationBusy: state.presentationBusy,
    pendingAction: state.pendingAction,
    finished: state.phase === "finished",
    legal,
    waitingForReconnect: state.waitingForReconnect,
  });
  const key = controlRenderKey({
    sessionId: state.authoritativeSnapshot?.session_id || state.snapshot?.session_id,
    turn: state.authoritativeSnapshot?.turn || state.snapshot?.turn,
    requestId: state.authoritativeSnapshot?.request_id || state.snapshot?.request_id,
    sequence: state.authoritativeSnapshot?.sequence || state.snapshot?.sequence,
    actorId: state.requiredUserId,
    legal,
  });
  const shouldBuild = phase === "waiting_for_local_action" && key !== state.controlsRenderKey;
  const controlsLegal = controlOptionsFor(legal);
  if (shouldBuild) {
    elements.moves.replaceChildren();
    elements.switches.replaceChildren();
    controlsLegal.moves?.forEach((move) => elements.moves.append(actionButton(move, "choose_move", false)));
    controlsLegal.switches?.forEach((switchAction) => elements.switches.append(actionButton(switchAction, "choose_switch", false)));
    state.controlsRenderKey = key;
    state.controlsSessionId = state.authoritativeSnapshot?.session_id || state.snapshot?.session_id || null;
  }
  updateControlPresentation(reason, phase);
  if (
    phase === "waiting_for_local_action" &&
    (state.authoritativeSnapshot?.request_id || state.snapshot?.request_id) &&
    key !== state.promptAckKey
  ) {
    state.promptAckKey = key;
    send({
      type: promptReadyTypeFor(legal),
      request_id: state.authoritativeSnapshot?.request_id || state.snapshot?.request_id,
    });
  }
}

function updateControlPresentation(reason, phaseOverride = null) {
  const legal = state.authoritativeSnapshot?.legal_actions || state.snapshot?.legal_actions || { moves: [], switches: [], forced_switch: false };
  const calculatedPhase = controlPhaseFor({
    hasSnapshot: Boolean(state.snapshotReceived || state.snapshot),
    presentationBusy: state.presentationBusy,
    pendingAction: state.pendingAction,
    finished: state.phase === "finished",
    legal,
    waitingForReconnect: state.waitingForReconnect,
  });
  const currentKey = controlRenderKey({
    sessionId: state.authoritativeSnapshot?.session_id || state.snapshot?.session_id,
    turn: state.authoritativeSnapshot?.turn || state.snapshot?.turn,
    requestId: state.authoritativeSnapshot?.request_id || state.snapshot?.request_id,
    sequence: state.authoritativeSnapshot?.sequence || state.snapshot?.sequence,
    actorId: state.requiredUserId,
    legal,
  });
  const phase = phaseOverride || (
    calculatedPhase === "waiting_for_local_action" && currentKey !== state.controlsRenderKey
      ? "presenting"
      : calculatedPhase
  );
  const changed = state.controlPhase !== phase;
  state.controlPhase = phase;
  const controlsDisabled = phase !== "waiting_for_local_action" || state.role === "unauthorized";
  [elements.moves, elements.switches].forEach((element) => {
    element.classList.toggle("controls-disabled", controlsDisabled);
    element.querySelectorAll("button").forEach((button) => { button.disabled = controlsDisabled; });
  });
  elements.forfeit.disabled = controlsDisabled && phase !== "waiting_for_start";
  if (phase !== "waiting_for_local_action") {
    elements.moves.hidden = true;
    elements.switches.hidden = true;
  } else {
    elements.moves.hidden = false;
    elements.switches.hidden = false;
    renderActionPrompt(legal, false);
  }
  if (changed) {
    console.debug("pvp_activity_control_state", {
      control_state: phase,
      render_key: state.controlsRenderKey,
      actor_id: state.requiredUserId,
      local_user_id: state.localUserId,
      legal_moves_count: legal.moves?.length || 0,
      legal_switches_count: legal.switches?.length || 0,
      presentation_busy: state.presentationBusy,
      reason_for_render: phase === "waiting_for_local_action" ? reason : null,
      reason_for_hide_or_disable: phase === "waiting_for_local_action" ? null : reason,
    });
  }
}

function renderActionPrompt(legal, controlsDisabled) {
  legal ||= { moves: [], switches: [], forced_switch: false };
  if (controlsDisabled || state.phase === "finished") {
    elements.actionPrompt.textContent = "";
    return;
  }
  const requiredName = state.playerNames[state.requiredUserId]
    || elements.opponentName.textContent
    || "Opponent";
  elements.actionPrompt.textContent = actionPromptFor({
    legal,
    phase: state.phase,
    waitingForReconnect: state.waitingForReconnect,
    requiredName,
    localName: elements.playerName.textContent || "You",
    opponentName: elements.opponentName.textContent || "Opponent",
  });
  const isForcedSwitch = state.phase === "forced_switch" || legal.forced_switch;
  if (isForcedSwitch) {
    elements.message.textContent = elements.actionPrompt.textContent;
  }
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
    updateControlPresentation("action_selected", "waiting_for_opponent");
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

async function presentBattleEvent(event) {
  elements.message.textContent = event.move_name || event.message || event.kind;
  const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
  const plan = reduceAnimationPlan(eventAnimationPlan(event), reducedMotion);
  if (event.switch) {
    state.pendingSwitchSide = resolveSide(event.target_side || event.source_side || event.target);
  }
  if (event.fainted) {
    state.pendingFaintSide = resolveSide(event.target_side || event.target);
  }
  state.preserveSnapshotMessage = true;
  try {
    for (let index = 0; index < plan.length; index += 1) {
      const step = plan[index];
      if (step.target === "notice") {
        elements.message.textContent = step.text;
        await wait(step.duration);
        elements.message.textContent = event.message || event.kind;
        continue;
      }
      if (step.target === "timing") {
        await wait(step.duration);
        continue;
      }
      if (
        step.target === "defender" &&
        plan[index + 1]?.target === "flash"
      ) {
        const defender = animationElement(step.target, event);
        const flash = animationElement("flash", event);
        if (defender && flash) {
          await Promise.all([
            playAnimation(defender, step.className, step.duration),
            playAnimation(
              flash,
              plan[index + 1].className,
              plan[index + 1].duration,
            ),
          ]);
          index += 1;
          continue;
        }
      }
      const element = animationElement(step.target, event);
      if (element) {
        await playAnimation(element, step.className, step.duration);
        if (step.className.includes("fainting") || step.className.includes("switching-out")) {
          element.hidden = true;
        }
      }
    }
  } finally {
    clearImpactFlash(elements.flash);
  }
  if (event.fainted || event.switch) {
    const endingElement = animationElement("defender", event);
    if (endingElement) endingElement.hidden = true;
  }
}

function animationElement(target, event) {
  if (target === "flash") {
    return elements.flash;
  }
  if (target === "attacker") {
    return elementForSide(resolveSide(event.source_side || event.actor)) || elements.player;
  }
  if (target === "defender") {
    return elementForSide(resolveSide(event.target_side || event.target)) || elements.opponent;
  }
  return null;
}

function resolveSide(side) {
  if (!side) return null;
  return side === state.role ? "player" : "opponent";
}

function elementForSide(side) {
  return side === "player" ? elements.player : side === "opponent" ? elements.opponent : null;
}

function playAnimation(element, className, duration) {
  const classes = className.split(" ");
  element.classList.remove(...classes);
  void element.offsetWidth;
  element.classList.add(...classes);
  return new Promise((resolve) => {
    window.setTimeout(() => {
      element.classList.remove(...classes);
      resolve();
    }, duration);
  });
}

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
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

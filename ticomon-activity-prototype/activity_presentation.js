export const PRESENTATION_TIMINGS = Object.freeze({
  moveText: 950,
  attack: 400,
  impact: 400,
  hp: 750,
  notice: 900,
  impactToHp: 400,
  normalPause: 500,
  betweenActions: 400,
  faintLead: 250,
  faintPause: 0,
  switchPause: 0,
  forcedSwitch: 0,
  effectivenessPause: 700,
  snapshot: 500,
  finished: 2200,
  initialSnapshot: 0,
  defaultEvent: 600,
});

export function presentationDelayFor(item, previous = null) {
  if (item.type === "battle_finished") return PRESENTATION_TIMINGS.finished;
  if (item.type === "battle_snapshot") {
    if (previous?.type === "battle_events" && previous.event?.fainted) return PRESENTATION_TIMINGS.faintPause;
    if (previous?.type === "battle_events" && previous.event?.switch) return PRESENTATION_TIMINGS.switchPause;
    if (previous?.type === "battle_events" && (previous.event?.effectiveness || previous.event?.missed)) {
      return PRESENTATION_TIMINGS.effectivenessPause;
    }
    return item.initial
      ? PRESENTATION_TIMINGS.initialSnapshot
      : item.phase === "forced_switch"
        ? PRESENTATION_TIMINGS.forcedSwitch
        : PRESENTATION_TIMINGS.snapshot;
  }
  if (item.type === "battle_events") {
    if (item.event?.switch) return PRESENTATION_TIMINGS.switchPause;
    return previous?.type === "battle_snapshot"
      ? PRESENTATION_TIMINGS.betweenActions
      : PRESENTATION_TIMINGS.impactToHp;
  }
  return PRESENTATION_TIMINGS.defaultEvent;
}

export function presentationKey(item) {
  if (item.key) return item.key;
  if (item.type === "battle_snapshot") return `snapshot:${item.sequence}`;
  if (item.type === "battle_finished") return `finished:${item.sequence}`;
  return `event:${item.sequence}:${item.index ?? 0}`;
}

function presentationOrder(item) {
  return [item.sequence ?? Number.MAX_SAFE_INTEGER, item.index ?? -1];
}

function comesBefore(left, right) {
  const [leftSequence, leftIndex] = presentationOrder(left);
  const [rightSequence, rightIndex] = presentationOrder(right);
  return leftSequence < rightSequence || (
    leftSequence === rightSequence && leftIndex < rightIndex
  );
}

export function shouldRestoreSnapshotImmediately({ reconnecting, hasSnapshot }) {
  return reconnecting && hasSnapshot;
}

export function shouldExposeControls({ presentationBusy, pendingAction }) {
  return !presentationBusy && !pendingAction;
}

export function controlRenderKey({
  sessionId = "-",
  turn = "-",
  requestId = "-",
  sequence = "-",
  actorId = "-",
  legal = {},
}) {
  const moves = (legal.moves || []).map((action) => action.slot ?? action.id ?? action.name);
  const switches = (legal.switches || []).map((action) => action.slot ?? action.id ?? action.name);
  const actionType = legal.forced_switch ? "forced_switch" : "action";
  return [sessionId, turn, requestId, sequence, actorId, actionType, moves.join(","), switches.join(",")].join(":");
}

export function controlPhaseFor({
  hasSnapshot,
  presentationBusy,
  pendingAction,
  finished = false,
  legal = {},
  waitingForReconnect = false,
}) {
  if (!hasSnapshot) return "waiting_for_start";
  if (finished) return "finished";
  if (presentationBusy) return "presenting";
  if (pendingAction || waitingForReconnect) return waitingForReconnect ? "reconnecting" : "waiting_for_opponent";
  if (legal.moves?.length || legal.switches?.length) return "waiting_for_local_action";
  return "waiting_for_opponent";
}

export function controlOptionsFor(legal = {}) {
  return legal.forced_switch
    ? { moves: [], switches: legal.switches || [], forced_switch: true }
    : { moves: legal.moves || [], switches: legal.switches || [], forced_switch: false };
}

export function promptReadyTypeFor(legal = {}) {
  return legal.forced_switch
    ? "forced_switch_prompt_ready"
    : "action_prompt_ready";
}

export function actionPromptFor({
  legal = {},
  phase,
  waitingForReconnect = false,
  requiredName = "Opponent",
  localName = "You",
  opponentName = "Opponent",
}) {
  const forcedSwitch = Boolean(legal.forced_switch || phase === "forced_switch");
  const localCanAct = Boolean(legal.moves?.length || legal.switches?.length);
  if (forcedSwitch && localCanAct) return "Choose a replacement Pokémon.";
  if (forcedSwitch && waitingForReconnect) {
    return `Waiting for ${requiredName} to reconnect.`;
  }
  if (forcedSwitch) return `${requiredName} is choosing a replacement.`;
  if (localCanAct) return `${localName}, choose your action`;
  return `${opponentName} is choosing...`;
}

export function preSnapshotMessage(hasSnapshot) {
  return hasSnapshot ? null : "Waiting for battle to start...";
}

export function preloadSprite(source, ImageConstructor = globalThis.Image) {
  return new Promise((resolve, reject) => {
    if (!source || typeof ImageConstructor !== "function") {
      reject(new Error("A sprite source is required."));
      return;
    }
    const image = new ImageConstructor();
    image.onload = () => resolve(source);
    image.onerror = () => reject(new Error(`Unable to load sprite: ${source}`));
    image.src = source;
  });
}

export async function replaceSpriteAfterPreload(
  element,
  source,
  ImageConstructor = globalThis.Image,
) {
  await preloadSprite(source, ImageConstructor);
  element.src = source;
  element.hidden = false;
  return source;
}

export class ActivityPresentationQueue {
  constructor({
    present,
    wait = (milliseconds) => new Promise((resolve) => {
      setTimeout(resolve, milliseconds);
    }),
    onStart = () => {},
    onIdle = () => {},
  }) {
    this.present = present;
    this.wait = wait;
    this.onStart = onStart;
    this.onIdle = onIdle;
    this.items = [];
    this.keys = new Set();
    this.running = false;
    this.startPromise = null;
  }

  clearPending() {
    this.items = [];
    this.keys.clear();
  }

  enqueue(item) {
    const key = presentationKey(item);
    if (this.keys.has(key)) return false;
    this.keys.add(key);
    const queued = { ...item, key };
    const insertionIndex = this.items.findIndex((current) =>
      comesBefore(queued, current)
    );
    if (insertionIndex === -1) this.items.push(queued);
    else this.items.splice(insertionIndex, 0, queued);
    if (!this.running && this.startPromise === null) {
      this.startPromise = Promise.resolve().then(() => {
        this.startPromise = null;
        if (!this.running && this.items.length) return this.drain();
        return undefined;
      });
      this.drainPromise = this.startPromise;
    }
    return true;
  }

  async drain() {
    this.running = true;
    this.onStart();
    let previous = null;
    while (this.items.length) {
      const item = this.items.shift();
      await this.present(item);
      await this.wait(presentationDelayFor(item, previous));
      previous = item;
    }
    this.running = false;
    this.onIdle();
  }
}

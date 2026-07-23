export const PRESENTATION_TIMINGS = Object.freeze({
  moveText: 800,
  attack: 400,
  impact: 500,
  hp: 800,
  notice: 1000,
  normalPause: 600,
  faintPause: 900,
  switchPause: 900,
  forcedSwitch: 900,
  snapshot: 600,
  finished: 0,
  initialSnapshot: 0,
  defaultEvent: 600,
});

export function presentationDelayFor(item, previous = null) {
  if (item.type === "battle_finished") return PRESENTATION_TIMINGS.finished;
  if (item.type === "battle_snapshot") {
    if (previous?.type === "battle_events" && previous.event?.fainted) {
      return PRESENTATION_TIMINGS.faintPause;
    }
    if (previous?.type === "battle_events" && previous.event?.switch) {
      return PRESENTATION_TIMINGS.switchPause;
    }
    return item.initial
      ? PRESENTATION_TIMINGS.initialSnapshot
      : item.phase === "forced_switch"
        ? PRESENTATION_TIMINGS.forcedSwitch
        : PRESENTATION_TIMINGS.snapshot;
  }
  if (item.type === "battle_events") return 0;
  return PRESENTATION_TIMINGS.defaultEvent;
}

export function presentationKey(item) {
  if (item.key) return item.key;
  if (item.type === "battle_snapshot") return `snapshot:${item.sequence}`;
  if (item.type === "battle_finished") return `finished:${item.sequence}`;
  return `event:${item.sequence}:${item.index ?? 0}`;
}

export function shouldRestoreSnapshotImmediately({ reconnecting, hasSnapshot }) {
  return reconnecting && hasSnapshot;
}

export function shouldExposeControls({ presentationBusy, pendingAction }) {
  return !presentationBusy && !pendingAction;
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
  }

  clearPending() {
    this.items = [];
    this.keys.clear();
  }

  enqueue(item) {
    const key = presentationKey(item);
    if (this.keys.has(key)) return false;
    this.keys.add(key);
    this.items.push({ ...item, key });
    if (!this.running) this.drainPromise = this.drain();
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

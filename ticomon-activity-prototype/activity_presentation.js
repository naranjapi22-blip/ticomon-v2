export const PRESENTATION_TIMINGS = Object.freeze({
  move: 1800,
  damage: 750,
  faint: 900,
  switch: 900,
  forcedSwitch: 800,
  snapshot: 650,
  finished: 0,
  initialSnapshot: 0,
  defaultEvent: 650,
});

export function presentationDelayFor(item) {
  if (item.type === "battle_finished") return PRESENTATION_TIMINGS.finished;
  if (item.type === "battle_snapshot") {
    return item.initial
      ? PRESENTATION_TIMINGS.initialSnapshot
      : item.phase === "forced_switch"
        ? PRESENTATION_TIMINGS.forcedSwitch
        : PRESENTATION_TIMINGS.snapshot;
  }
  return PRESENTATION_TIMINGS[item.event?.kind] || PRESENTATION_TIMINGS.defaultEvent;
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
    while (this.items.length) {
      const item = this.items.shift();
      await this.present(item);
      await this.wait(presentationDelayFor(item));
    }
    this.running = false;
    this.onIdle();
  }
}

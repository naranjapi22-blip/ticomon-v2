import test from "node:test";
import assert from "node:assert/strict";
import {
  ANIMATION_TIMINGS,
  clearImpactFlash,
  eventAnimationPlan,
  reduceAnimationPlan,
} from "./activity_animation.js";
import { ActivityPresentationQueue } from "./activity_presentation.js";

test("physical events lunge before defender recoil", () => {
  const plan = eventAnimationPlan({
    kind: "move",
    actor: "player1",
    target: "player2",
    move_name: "Tackle",
  });
  assert.deepEqual(
    plan.slice(0, 2).map(({ target, className }) => [target, className]),
    [["attacker", "attack-physical"], ["defender", "hit-recoil"]],
  );
});

test("special events apply a glow and impact pulse", () => {
  const plan = eventAnimationPlan({
    kind: "move",
    category: "special",
    actor: "player1",
    target: "player2",
    move_name: "Flamethrower",
  });
  assert.equal(plan[0].className, "attack-special");
  assert.match(plan[1].className, /special-impact/);
});

test("physical and special categories produce different attacker presentations", () => {
  const physical = eventAnimationPlan({ kind: "move", category: "physical", move_name: "Tackle" });
  const special = eventAnimationPlan({ kind: "move", category: "special", move_name: "Surf" });
  assert.equal(physical[0].className, "attack-physical");
  assert.equal(special[0].className, "attack-special");
  assert.notEqual(physical[1].className, special[1].className);
});

test("misses animate only the attacker and show Missed", () => {
  const plan = eventAnimationPlan({
    kind: "move",
    missed: true,
    actor: "player1",
    target: "player2",
    move_name: "Hydro Pump missed!",
  });
  assert.equal(plan.some((step) => step.target === "defender"), false);
  assert.equal(plan.at(-1).text, "Missed!");
});

test("super effective events use heavy impact and readable text", () => {
  const plan = eventAnimationPlan({
    kind: "move",
    effectiveness: "super effective",
    move_name: "Thunderbolt",
  });
  assert.match(plan[1].className, /hit-heavy/);
  assert.equal(plan.at(-1).text, "Super effective!");
  assert.equal(plan.find((step) => step.target === "flash").className, "screen-flash flash-heavy");
});

test("hits flash, misses do not, and resisted hits use a lighter flash", () => {
  const hit = eventAnimationPlan({ kind: "move", move_name: "Tackle" });
  const miss = eventAnimationPlan({ kind: "move", move_name: "Tackle", missed: true });
  const resisted = eventAnimationPlan({ kind: "move", move_name: "Tackle", effectiveness: "resisted" });
  assert.equal(hit.find((step) => step.target === "flash").className, "screen-flash");
  assert.equal(miss.some((step) => step.target === "flash"), false);
  assert.equal(resisted.find((step) => step.target === "flash").className, "screen-flash flash-light");
});

test("impact flash cleanup removes all transient classes and inline opacity", () => {
  const removed = [];
  const element = {
    classList: { remove: (...names) => removed.push(...names) },
    style: { removeProperty: (name) => removed.push(name) },
  };
  clearImpactFlash(element);
  assert.deepEqual(removed, ["screen-flash", "flash-heavy", "flash-light", "opacity"]);
});

test("HP presentation completes before controls are exposed", async () => {
  const order = [];
  const queue = new ActivityPresentationQueue({
    present: async (item) => {
      if (item.type === "battle_snapshot") {
        order.push("hp-start");
        await new Promise((resolve) => setTimeout(resolve, ANIMATION_TIMINGS.hp));
        order.push("hp-end");
      }
    },
    wait: async () => {},
    onIdle: () => order.push("controls"),
  });
  queue.enqueue({ type: "battle_snapshot", sequence: 3, phase: "resolving" });
  await queue.drainPromise;
  assert.deepEqual(order, ["hp-start", "hp-end", "controls"]);
});

test("faint animation completes before a later switch-in presentation", async () => {
  const order = [];
  const queue = new ActivityPresentationQueue({
    present: async (item) => {
      order.push(item.name);
      if (item.name === "faint") {
        await new Promise((resolve) => setTimeout(resolve, ANIMATION_TIMINGS.faint));
      }
    },
    wait: async () => {},
  });
  queue.enqueue({ type: "battle_events", sequence: 4, index: 0, name: "faint" });
  queue.enqueue({ type: "battle_snapshot", sequence: 5, phase: "forced_switch", name: "switch-in" });
  await queue.drainPromise;
  assert.deepEqual(order, ["faint", "switch-in"]);
});

test("duplicate animation events are not replayed", async () => {
  let count = 0;
  const queue = new ActivityPresentationQueue({
    present: async () => { count += 1; },
    wait: async () => {},
  });
  const event = { type: "battle_events", sequence: 8, index: 0, event: { kind: "move" } };
  queue.enqueue(event);
  assert.equal(queue.enqueue(event), false);
  await queue.drainPromise;
  assert.equal(count, 1);
});

test("reduced motion removes movement but retains notices and a brief flash", () => {
  const plan = eventAnimationPlan({
    kind: "move",
    effectiveness: "super effective",
    move_name: "Thunderbolt",
  });
  const reduced = reduceAnimationPlan(plan, true);
  assert.equal(reduced.some((step) => step.className === "attack-physical"), false);
  assert.equal(reduced.some((step) => step.target === "flash"), true);
  assert.equal(reduced.at(-1).text, "Super effective!");
});

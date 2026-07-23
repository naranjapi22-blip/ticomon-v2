export const ANIMATION_TIMINGS = Object.freeze({
  attacker: 400,
  defender: 400,
  effectiveness: 800,
  hp: 700,
  faint: 700,
  switchOut: 600,
  switchIn: 600,
  impactFlash: 400,
});

export const IMPACT_FLASH_CLASSES = Object.freeze([
  "screen-flash",
  "flash-heavy",
  "flash-light",
]);

export function clearImpactFlash(element) {
  element.classList.remove(...IMPACT_FLASH_CLASSES);
  element.style.removeProperty("opacity");
}

const MOVEMENT_CLASSES = new Set([
  "attack-physical",
  "attack-special",
  "hit-recoil",
  "hit-heavy",
  "hit-light",
  "fainting",
  "switching-out",
  "switching-in",
]);

export function eventAnimationPlan(event) {
  const message = event.message || "";
  const miss = event.missed === true || /\bmiss(?:ed)?\b/i.test(message);
  const effectiveness = event.effectiveness || effectivenessFromMessage(message);
  const special = [event.category, event.move_category, event.attack_type]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase() === "special");
  const attackerClass = special ? "attack-special" : "attack-physical";
  const impactClass = effectivenessClass(effectiveness, special);
  const flashClass = effectivenessFlashClass(effectiveness);
  const plan = [];

  if (event.switch) {
    plan.push({ target: "defender", className: "switching-out", duration: ANIMATION_TIMINGS.switchOut });
    return plan;
  }

  const attackEvent =
    event.kind === "move" ||
    event.kind === "damage" ||
    event.move_name ||
    event.missed ||
    miss;
  if (event.fainted) {
    if (!miss) {
      plan.push({ target: "attacker", className: attackerClass, duration: ANIMATION_TIMINGS.attacker });
      plan.push({ target: "defender", className: impactClass || "hit-recoil", duration: ANIMATION_TIMINGS.defender });
      plan.push({ target: "flash", className: flashClass, duration: ANIMATION_TIMINGS.impactFlash });
    }
  } else if (attackEvent) {
    plan.push({ target: "attacker", className: attackerClass, duration: ANIMATION_TIMINGS.attacker });
    if (!miss) {
      plan.push({ target: "defender", className: impactClass || "hit-recoil", duration: ANIMATION_TIMINGS.defender });
      plan.push({ target: "flash", className: flashClass, duration: ANIMATION_TIMINGS.impactFlash });
    }
  }

  if (miss) {
    plan.push({
      target: "notice",
      text: "Missed!",
      duration: ANIMATION_TIMINGS.effectiveness,
    });
  } else if (effectiveness) {
    plan.push({
      target: "notice",
      text: effectivenessText(effectiveness),
      duration: ANIMATION_TIMINGS.effectiveness,
    });
  }
  return plan;
}

export function reduceAnimationPlan(plan, reducedMotion) {
  if (!reducedMotion) return plan;
  return plan.map((step) => {
    if (!step.className?.split(" ").some((name) => MOVEMENT_CLASSES.has(name))) {
      return step;
    }
    return { ...step, target: "timing", className: "" };
  });
}

export function effectivenessFromMessage(message) {
  if (/super effective/i.test(message)) return "super effective";
  if (/not very effective|resisted/i.test(message)) return "not very effective";
  return "";
}

function effectivenessClass(effectiveness, special) {
  if (/super effective/i.test(effectiveness)) return "hit-recoil hit-heavy";
  if (/not very effective|resisted/i.test(effectiveness)) return "hit-recoil hit-light";
  return special ? "hit-recoil special-impact" : "hit-recoil";
}

function effectivenessFlashClass(effectiveness) {
  if (/super effective/i.test(effectiveness)) return "screen-flash flash-heavy";
  if (/not very effective|resisted/i.test(effectiveness)) {
    return "screen-flash flash-light";
  }
  return "screen-flash";
}

function effectivenessText(effectiveness) {
  return /super effective/i.test(effectiveness)
    ? "Super effective!"
    : "Not very effective.";
}

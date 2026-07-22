const transientConnectionMessages = new Set([
  "Connecting to Discord...",
  "Authenticating with Discord...",
  "Refreshing Discord authorization...",
  "Reconnecting to the battle...",
  "Syncing the current battle...",
]);

export function isTransientConnectionMessage(message) {
  return transientConnectionMessages.has(message);
}

export function shouldShowBlockingSetup({ hasSnapshot, message, initialized = false }) {
  return !initialized && !(hasSnapshot && isTransientConnectionMessage(message));
}

export function isAuthorizedRole(role) {
  return role === "player1" || role === "player2";
}

export function resolveActivitySprite(pokemon) {
  const source = typeof pokemon?.sprite_url === "string" ? pokemon.sprite_url.trim() : "";
  return { source: source || null, alt: pokemon?.name || "Battle sprite" };
}

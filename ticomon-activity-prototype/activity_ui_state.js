export function shouldShowBlockingSetup({ hasSnapshot }) {
  return !hasSnapshot;
}

export function isAuthorizedRole(role) {
  return role === "player1" || role === "player2";
}

export function resolveActivitySprite(pokemon) {
  const source = typeof pokemon?.sprite_url === "string" ? pokemon.sprite_url.trim() : "";
  return { source: source || null, alt: pokemon?.name || "Battle sprite" };
}

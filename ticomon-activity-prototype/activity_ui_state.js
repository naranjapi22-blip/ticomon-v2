export function shouldShowBlockingSetup({ hasSnapshot }) {
  return !hasSnapshot;
}

export const ACTIVITY_AUTH_STORAGE_KEY = "ticomon.activity.auth";

export function readCachedActivityAuth(storage) {
  try {
    const value = JSON.parse(storage?.getItem(ACTIVITY_AUTH_STORAGE_KEY) || "null");
    return typeof value?.session_token === "string" && value.session_token
      ? value
      : null;
  } catch {
    return null;
  }
}

export function clearCachedActivityAuth(storage) {
  storage?.removeItem(ACTIVITY_AUTH_STORAGE_KEY);
}

export function cacheActivityAuth(storage, auth) {
  storage?.setItem(ACTIVITY_AUTH_STORAGE_KEY, JSON.stringify(auth));
}

export function setOverlayVisibility(element, visible) {
  element.hidden = !visible;
  element.classList.remove("visible", "active", "is-visible");
  element.style.removeProperty("display");
  element.style.removeProperty("pointer-events");
  element.setAttribute("aria-hidden", String(!visible));
}

export function isAuthorizedRole(role) {
  return role === "player1" || role === "player2";
}

export function resolveActivitySprite(pokemon) {
  const source = typeof pokemon?.sprite_url === "string" ? pokemon.sprite_url.trim() : "";
  return { source: source || null, alt: pokemon?.name || "Battle sprite" };
}

export const ACTIVITY_BACKGROUND_DIRECTORY = "/activity-backgrounds";
export const DEFAULT_ACTIVITY_BACKGROUND = "bg-aquacordetown.jpg";

export function activityBackgroundUrl(name = DEFAULT_ACTIVITY_BACKGROUND) {
  return `${ACTIVITY_BACKGROUND_DIRECTORY}/${name}`;
}

export function selectActivityBackground(available, preferred = DEFAULT_ACTIVITY_BACKGROUND) {
  if (available.includes(preferred)) return activityBackgroundUrl(preferred);
  const fallback = [...available].sort().find((name) => name.endsWith(".jpg"));
  return fallback ? activityBackgroundUrl(fallback) : null;
}

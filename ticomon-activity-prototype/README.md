# TicoMon Experimental PvP Activity

This is an experimental proof of concept. `!pvptest @opponent` reuses the
existing TicoMon PvP session, team selection, abilities, moves, Showdown
controller, timers, switching, forced switching, forfeit behavior, snapshots,
events, and final result. It does not replace or alter production `!pvp`.

The Activity client never decides damage, HP, legal actions, timers, winners,
or battle state. The existing PvP application service remains authoritative.

## Local environment

From this directory, install dependencies and create the frontend environment:

```powershell
npm ci
Copy-Item .env.example .env
```

Set `VITE_DISCORD_CLIENT_ID` to the Discord Application ID. Keep
`VITE_ACTIVITY_API_ORIGIN` empty when using relative `/api` paths. For local
Vite proxying, set `ACTIVITY_BACKEND_ORIGIN=http://127.0.0.1:8080` in `.env`.
Never put `DISCORD_CLIENT_SECRET`, `DISCORD_TOKEN`, database URLs, or session
secrets in a `VITE_` variable.

The bot reads the repository root `.env`:

```env
ACTIVITY_API_ENABLED=true
ACTIVITY_SESSION_SECRET=YOUR_LONG_RANDOM_ACTIVITY_SESSION_SECRET
ACTIVITY_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SHOWDOWN_WEBSOCKET_URL=ws://localhost:8000/showdown/websocket
```

The API binds to `0.0.0.0`. It uses Railway's `PORT` when present and falls
back to port `8080` locally. Activity sessions are in memory; no migration is
required.

## Local development

Run these in separate terminals:

1. Start the existing Pokémon Showdown server.
2. Start the TicoMon bot and experimental API from the repository root:

   ```powershell
   poetry run python main.py
   ```

   The API health endpoint is `http://localhost:8080/health`.
3. Start the Activity frontend:

   ```powershell
   cd C:\Users\Auditoria\Desktop\ticomon-v2\ticomon-activity-prototype
   npm run dev
   ```

   Vite serves `http://localhost:5173/` and proxies `/api` and WebSocket
   traffic to the configured local API.
4. Expose the frontend with an HTTPS tunnel:

   ```powershell
   cloudflared tunnel --url http://localhost:5173
   ```

   Do not store the temporary tunnel hostname in Git. Quick Tunnel hostnames
   can change after restart.

## Production Railway setup

The existing bot service keeps the repository root as its root directory and
starts its normal process. Enable the Activity API in that same process. The
new frontend service uses this directory as its Railway Root Directory:
`/ticomon-activity-prototype`.

Frontend build and start commands:

```text
npm ci
npm run build
npm run start
```

`npm run start` serves `dist/` with a production Node static server on
`0.0.0.0:$PORT`; it does not run Vite. The frontend uses relative `/api`
requests so Discord URL mappings can route API traffic to the bot service.

Bot/API variables (server-only; never expose their values):

```env
ACTIVITY_API_ENABLED=true
DISCORD_CLIENT_ID=YOUR_DISCORD_APPLICATION_ID
DISCORD_CLIENT_SECRET=YOUR_DISCORD_CLIENT_SECRET
ACTIVITY_SESSION_SECRET=YOUR_LONG_RANDOM_ACTIVITY_SESSION_SECRET
ACTIVITY_ALLOWED_ORIGINS=https://YOUR_ACTIVITY_DOMAIN
SHOWDOWN_WEBSOCKET_URL=ws://pokemon-showdown.railway.internal:8080/showdown/websocket
```

Preserve the existing bot variables such as `DISCORD_TOKEN`, `DATABASE_URL`,
R2 settings, and Showdown authentication settings. Railway supplies `PORT`.
The frontend service only needs:

```env
VITE_DISCORD_CLIENT_ID=YOUR_DISCORD_APPLICATION_ID
```

Do not put Railway internal URLs, bot secrets, or Discord client secrets in
frontend variables or built assets.

## Discord Developer Portal

After both Railway public domains are stable, configure **Activities → URL
Mappings** approximately as follows:

```text
/     → YOUR_ACTIVITY_DOMAIN.up.railway.app
/api  → YOUR_BOT_API_DOMAIN.up.railway.app
```

Enter each Target without `https://`. Keep Activities enabled and configure
the application's Activity Entry Point/App Launcher settings. The server-side
OAuth2 flow exchanges the Embedded App SDK authorization code with Discord;
configure the redirect URI in Discord OAuth2 settings. Discord's current
Activity guide documents `https://127.0.0.1` as the placeholder because the
Embedded App SDK handles the redirect internally. Add the production Activity
origin to `ACTIVITY_ALLOWED_ORIGINS`.

`!pvptest` is a prefix command. After both existing team-selection flows are
confirmed, its public message tells both players to launch TicoMon from the
App Launcher in the same channel and join the same Activity instance. The
backend still authenticates and authorizes both users independently.

## Manual smoke test

1. Start the existing Showdown server.
2. Start the TicoMon bot and experimental Activity API.
3. Start the production frontend locally with `npm run build` then
   `npm run start`, or use `npm run dev` for browser preview.
4. Start the HTTPS tunnel only for local testing.
5. Update the Discord URL mappings.
6. Run `!pvptest @opponent`.
7. Complete both existing team-selection flows.
8. Launch TicoMon from the same Discord channel.
9. Have both selected players join the same Activity instance.
10. Confirm both perspectives show the correct live Pokémon and HP.
11. Complete one real move turn through Showdown.
12. Test a switch and forced switch when applicable.
13. Close and reopen the Activity and verify the current snapshot returns.
14. Finish or forfeit the battle.
15. Confirm the result is published in Discord and production `!pvp` is unchanged.

## Commands

```powershell
npm run dev
npm run build
npm run start
npm run preview
```

The Activity API is started inside the normal bot process only when
`ACTIVITY_API_ENABLED=true`.

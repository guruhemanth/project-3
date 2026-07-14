# Google OAuth & Gmail Integration Setup (SubTrack)

SubTrack uses Google for two things:

1. **Sign in with Google** — `openid email profile` scope.
2. **Gmail auto-import** (Phase 2) — reads billing receipts and uses OpenRouter (GPT-OSS)
   to create subscriptions. Scope: `https://www.googleapis.com/auth/gmail.readonly`
   (read-only, minimum required; email bodies are processed in-memory and never persisted).

Both use the **same OAuth client**. Google Cloud usage here is **free** — there is no
charge for OAuth2 or Gmail API reads at this scale. You only need a billing account on
file later if you launch publicly and submit the (free) OAuth verification review.

## 1. Create the project (free)
1. Go to <https://console.cloud.google.com/> and create a new project (or pick an existing one).
2. **APIs & Services → Library** and enable:
   - **Google Gmail API** (required for auto-import)
   - *Identity/OAuth is available by default; no separate enable needed.*

## 2. Configure the OAuth consent screen
1. **APIs & Services → OAuth consent screen**.
2. User type: **External**.
3. App name: `SubTrack`, User support email + Developer contact: your email.
4. **Scopes**: add `.../auth/gmail.readonly` (sensitive scope).
5. **Test users**: add the Google account(s) you'll test with (required while publishing
   status is **Testing** — otherwise Google blocks consent).
6. Publishing status: leave as **Testing** for development. (Going to **Production** later
   triggers the free verification review.)

## 3. Create the OAuth client ID
1. **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Application type: **Web application**.
3. Name: `SubTrack Web`.
4. **Authorized redirect URIs** — add both (dev shown; replace host for prod):
   - `http://localhost:8000/api/auth/google/callback`   (Google sign-in)
   - `http://localhost:8000/api/gmail/oauth2callback`    (Gmail auto-import)
5. Click **Create** and copy the **Client ID** and **Client secret**.

## 4. Put the credentials in SubTrack
Edit `credentials.yaml` (this file is git-ignored — never commit it):

```yaml
google_oauth:
  client_id: "YOUR_CLIENT_ID.apps.googleusercontent.com"
  client_secret: "YOUR_CLIENT_SECRET"
  redirect_uri: "http://localhost:8000/api/auth/google/callback"
```

Also set the Gmail redirect URI (used by the auto-import flow) — it can be the same
value or set explicitly:

```yaml
  # gmail_integration must be true AND an OpenRouter key must be present:
feature_flags:
  gmail_integration: true
```

OpenRouter key (LLM that classifies the emails):

```yaml
openrouter:
  api_key: "sk-or-v1-..."
  model: "openai/gpt-oss-120b:free"
  base_url: "https://openrouter.ai/api/v1"
```

Restart the backend after editing (`pkill -f 'app.main:app'` then run `run/start.sh` or
`uvicorn app.main:app --port 8000`) so it reloads config.

## 5. Verify it works
```bash
# Login (or use the UI), then:
TOK=$(curl -s -X POST http://localhost:5173/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"play@subtrack.app","password":"subtrack123"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s -H "Authorization: Bearer $TOK" http://localhost:5173/api/gmail/status
# -> {"connected":false,"gmail_enabled":true,"openrouter_configured":true}

curl -s -H "Authorization: Bearer $TOK" http://localhost:5173/api/gmail/connect
# -> {"url":"https://accounts.google.com/o/oauth2/v2/auth?client_id=...&scope=...gmail.readonly..."}
```

Open that `url` in a browser, approve, and Google redirects to
`/api/gmail/oauth2callback?code=...&state=u<id>` which stores the encrypted token and
bounces you back to the app (`/?gmail=connected`). Then call:

```bash
curl -s -X POST -H "Authorization: Bearer $TOK" http://localhost:5173/api/gmail/ingest
# -> {"created": <n>}
```

## 6. Production notes
- Use **https** redirect URIs (e.g. `https://api.subtrack.app/api/gmail/oauth2callback`).
- Set the matching redirect in `credentials.yaml` (`gmail_redirect_uri` /
  `GOOGLE_REDIRECT_URI` / `GMAIL_REDIRECT_URI` env vars).
- For public launch, submit the OAuth app for **verification** (free) because
  `gmail.readonly` is a sensitive scope.
- Keep `credentials.yaml` out of git; in prod inject these via environment variables
  (see `.env.example` and `docker-compose.yml`).

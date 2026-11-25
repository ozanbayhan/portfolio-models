# Self-hosting

Portfolio Models runs anywhere Python 3.12 or Docker runs: your laptop, a home server, a VPS or a PaaS.
Your data never leaves your machine except for the price requests to Yahoo Finance, inflation requests (TCMB EVDS,
FRED/BLS, Deutsche Bundesbank, OECD — no personal data is sent) and, if configured, your SMTP server for emails.

| Mode | Who | Sign-in | Storage |
|---|---|---|---|
| **Local mode** (default) | just you | none | SQLite in `PM_DATA_DIR` |
| **Multi-user mode** | family, team, public | Google (OIDC) | SQLite or Postgres, rows isolated per user |

---

## Option A — one line with `uvx`

```bash
uvx --from git+https://github.com/ozanbayhan/portfolio-models portfolio-models serve
```

Useful flags:

```bash
portfolio-models serve --port 8080              # different port
portfolio-models serve --host 0.0.0.0           # reachable from your LAN
portfolio-models serve --data-dir ~/pm-data     # where portfolios.db lives (default ~/.portfolio-models)
portfolio-models serve --multi-user             # require sign-in (configure auth first, see below)
```

To install permanently: `uv tool install git+https://github.com/ozanbayhan/portfolio-models` and then simply
`portfolio-models serve`. Upgrade with `uv tool upgrade portfolio-models`.

## Option B — Docker

```bash
docker run -d --name portfolio-models --restart unless-stopped \
  -p 8501:8501 -v pm-data:/data \
  ghcr.io/ozanbayhan/portfolio-models:latest
```

The image runs as a non-root user, stores everything in the `/data` volume and has a health check
(`/_stcore/health`). Configure it with environment variables (`-e NAME=value` or `--env-file .env`).

Image commands:

| Command | What it does |
|---|---|
| `serve` (default) | web interface on port 8501 |
| `report` | send the weekly email summaries once |
| `weekly` | scheduler: runs `report` every Monday 06:00 UTC |

## Option C — Docker Compose (recommended for servers)

```bash
git clone https://github.com/ozanbayhan/portfolio-models && cd portfolio-models
cp .env.example .env
docker compose up -d                                  # app only, SQLite
docker compose --profile postgres up -d               # + Postgres
docker compose --profile postgres --profile email up -d   # + weekly email scheduler
```

Upgrade: `docker compose pull && docker compose up -d`.

---

## Configuration reference

All settings are optional. Put them in `.env` (Compose), pass them with `-e` (Docker) or export them (uvx).

| Variable | Default | Purpose |
|---|---|---|
| `PM_PORT` | `8501` | Host port (Compose) |
| `PM_DATA_DIR` | `/data` (Docker), `~/.portfolio-models` (uvx) | Folder for `portfolios.db` |
| `PM_LOCAL_MODE` | on unless OAuth is set | Single-user mode without sign-in |
| `PM_DATABASE_URL` | SQLite in `PM_DATA_DIR` | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@host:5432/db` |
| `PM_PUBLIC_URL` | — | Public base URL, required for Google sign-in, e.g. `https://pm.example.com` |
| `PM_OAUTH_CLIENT_ID` / `PM_OAUTH_CLIENT_SECRET` | — | Google OAuth client; enables multi-user mode |
| `PM_COOKIE_SECRET` | random per start | Long random string; set it or users are signed out on every restart |
| `PM_OAUTH_METADATA_URL` | Google | Any OIDC provider's discovery URL (Auth0, Keycloak, Microsoft Entra …) |
| `PM_EVDS_API_KEY` | — | TCMB EVDS key for up-to-date Turkish CPI; OECD is used otherwise |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | `smtp.gmail.com` / `465` | Weekly email delivery (SSL) |
| `MAIL_FROM` | `SMTP_USER` | Sender shown in emails |
| `APP_URL` | public demo | Link in emails — set it to your `PM_PUBLIC_URL` |

Without Docker you can also use a `.streamlit/secrets.toml` file in the working directory
(see [Streamlit secrets](https://docs.streamlit.io/develop/concepts/connections/secrets-management)):

```toml
evds_api_key = "..."

[auth]
redirect_uri = "https://pm.example.com/oauth2callback"
cookie_secret = "..."
client_id = "..."
client_secret = "..."
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[connections.portfolios]
url = "postgresql+psycopg://..."
```

---

## Google login

Multi-user mode uses Streamlit's built-in OIDC login. Each user sees only their own saved settings, positions,
transactions and fund prices; isolation is enforced on the server by e-mail address.

1. Open the [Google Cloud console](https://console.cloud.google.com/) and create a project.
2. **Google Auth Platform → Branding**: app name, support e-mail, and your **home page**, **privacy policy**
   (`https://your-host/?page=privacy`) and **terms** (`https://your-host/?page=terms`) links. Add your domain under
   *Authorized domains*.
3. **Audience**: choose *External*, then **Publish app** (otherwise only listed test users can sign in). The app only
   requests `openid`, `email` and `profile`, so no verification is required.
4. **Clients → Create client → Web application**. Authorised redirect URI: `https://your-host/oauth2callback`.
5. Put the client ID and secret into `.env`:

   ```bash
   PM_PUBLIC_URL=https://pm.example.com
   PM_OAUTH_CLIENT_ID=1234-abc.apps.googleusercontent.com
   PM_OAUTH_CLIENT_SECRET=GOCSPX-...
   PM_COOKIE_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
   ```

6. `docker compose up -d` — the sidebar now shows **Sign in with Google**.

Other OIDC providers work the same way; set `PM_OAUTH_METADATA_URL` to their discovery document.

## Database

- **SQLite** (default) is perfect for one person or a small group. The file is `PM_DATA_DIR/portfolios.db`.
- **Postgres** for many users: `docker compose --profile postgres up -d` and
  `PM_DATABASE_URL=postgresql+psycopg://portfolio_models:${POSTGRES_PASSWORD}@db:5432/portfolio_models`.
- **Supabase** (free tier) works too. Use the **Session pooler** connection string (IPv4), prefix it with
  `postgresql+psycopg://`, and percent-encode special characters in the password.

Tables are created automatically on first start. No migrations are needed for upgrades within 0.x so far;
check the [changelog](https://github.com/ozanbayhan/portfolio-models/blob/main/CHANGELOG.md) before upgrading.

## HTTPS with a reverse proxy

Streamlit uses WebSockets, so the proxy must forward upgrade headers.

**Caddy** (automatic certificates):

```caddy
pm.example.com {
    reverse_proxy localhost:8501
}
```

**Nginx**:

```nginx
server {
    server_name pm.example.com;
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

## Weekly email

Users opt in with the **📧 Weekly email summary** switch on *My portfolio*. Every Monday they receive the value,
weekly change and stale fund prices of their most recently saved portfolio, in the language they had selected.

- **Docker Compose**: `docker compose --profile email up -d` with `SMTP_*`, `MAIL_FROM` and `APP_URL` set.
- **Cron**: `0 6 * * 1  DB_URL=... SMTP_USER=... SMTP_PASSWORD=... portfolio-models report`
- **GitHub Actions**: the repository ships [`weekly-report.yml`](https://github.com/ozanbayhan/portfolio-models/blob/main/.github/workflows/weekly-report.yml);
  add `DB_URL`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` as repository secrets (`scripts/setup_weekly_email.sh` helps).

For Gmail, create an [app password](https://myaccount.google.com/apppasswords) (2-step verification required).

## Streamlit Community Cloud (free hosting)

1. Fork the repository.
2. On [share.streamlit.io](https://share.streamlit.io) create an app from your fork, branch `main`, main file `app.py`,
   Python 3.12.
3. Paste your secrets (the TOML above) into **Settings → Secrets**.

## Backups

- SQLite: copy `PM_DATA_DIR/portfolios.db` (e.g. `docker cp portfolio-models:/data/portfolios.db .`).
- Postgres: `docker compose exec db pg_dump -U portfolio_models portfolio_models > backup.sql`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Sign-in is not set up on this server" | OAuth variables are missing; or use local mode |
| Google says `redirect_uri_mismatch` | The redirect URI in Google must be exactly `PM_PUBLIC_URL` + `/oauth2callback` |
| Users signed out after restart | Set a fixed `PM_COOKIE_SECRET` |
| Blank page behind a proxy | Forward WebSocket `Upgrade`/`Connection` headers |
| No prices for a symbol | Check the Yahoo Finance symbol (BIST stocks end in `.IS`; the app adds it for you) |
| CPI stops in an old month | Set `PM_EVDS_API_KEY`; OECD publishes Turkish CPI with a delay |

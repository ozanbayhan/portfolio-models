#!/bin/sh
# Ortam değişkenlerinden Streamlit secrets dosyasını üretir ve istenen komutu çalıştırır.
#   serve   — web arayüzü (varsayılan)
#   report  — haftalık e-posta özetlerini bir kez gönder
#   weekly  — her pazartesi 06:00 UTC'de report çalıştıran zamanlayıcı
#   mcp     — yapay zekâ asistanları için MCP sunucusu (stdio; --http ile HTTP)
#   api     — model portföy arşivi için salt okunur JSON API (port 8770)
set -eu

SECRETS=/app/.streamlit/secrets.toml
: > "$SECRETS"

esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

MULTI=""
if [ -n "${PM_OAUTH_CLIENT_ID:-}" ]; then
  : "${PM_PUBLIC_URL:?PM_PUBLIC_URL gerekli (ör. https://portfoy.example.com) — Google girişi için}"
  if [ -z "${PM_COOKIE_SECRET:-}" ]; then
    echo "UYARI: PM_COOKIE_SECRET tanımlı değil; rastgele üretildi. Konteyner yeniden başlarsa oturumlar kapanır." >&2
    PM_COOKIE_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
  fi
  cat >> "$SECRETS" <<TOML
[auth]
redirect_uri = "$(esc "${PM_PUBLIC_URL%/}")/oauth2callback"
cookie_secret = "$(esc "$PM_COOKIE_SECRET")"
client_id = "$(esc "$PM_OAUTH_CLIENT_ID")"
client_secret = "$(esc "${PM_OAUTH_CLIENT_SECRET:?PM_OAUTH_CLIENT_SECRET gerekli}")"
server_metadata_url = "$(esc "${PM_OAUTH_METADATA_URL:-https://accounts.google.com/.well-known/openid-configuration}")"

TOML
  MULTI="--multi-user"
fi

if [ -n "${PM_DATABASE_URL:-}" ]; then
  cat >> "$SECRETS" <<TOML
[connections.portfolios]
url = "$(esc "$PM_DATABASE_URL")"
TOML
fi

cmd="${1:-serve}"
[ $# -gt 0 ] && shift
case "$cmd" in
  serve)
    exec portfolio-models serve --host 0.0.0.0 --port "${PM_PORT:-8501}" --data-dir "${PM_DATA_DIR:-/data}" $MULTI "$@"
    ;;
  report)
    export DB_URL="${PM_DATABASE_URL:-sqlite:///${PM_DATA_DIR:-/data}/portfolios.db}"
    exec portfolio-models report "$@"
    ;;
  api)
    exec portfolio-models api --host 0.0.0.0 --port "${PM_API_PORT:-8770}" --data-dir "${PM_DATA_DIR:-/data}" "$@"
    ;;
  mcp)
    exec portfolio-models mcp --data-dir "${PM_DATA_DIR:-/data}" "$@"
    ;;
  weekly)
    export DB_URL="${PM_DATABASE_URL:-sqlite:///${PM_DATA_DIR:-/data}/portfolios.db}"
    echo "Haftalık e-posta zamanlayıcısı başladı (her pazartesi 06:00 UTC)."
    while true; do
      secs=$(python - <<'PY'
from datetime import datetime, timedelta, timezone
now = datetime.now(timezone.utc)
nxt = (now + timedelta(days=(7 - now.weekday()) % 7)).replace(hour=6, minute=0, second=0, microsecond=0)
if nxt <= now:
    nxt += timedelta(days=7)
print(int((nxt - now).total_seconds()))
PY
)
      echo "Sonraki gönderim: ${secs} sn sonra."
      sleep "$secs"
      portfolio-models report || echo "Gönderim başarısız; bir sonraki hafta tekrar denenecek." >&2
    done
    ;;
  *)
    exec "$cmd" "$@"
    ;;
esac

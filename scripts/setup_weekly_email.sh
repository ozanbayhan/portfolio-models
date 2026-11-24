#!/usr/bin/env bash
# Haftalık e-posta özeti için GitHub secret'larını ayarlar.
# Çalıştırma: bash scripts/setup_weekly_email.sh
# Şifreler ekrana yazılmaz; doğrudan GitHub'a (şifreli secret olarak) gönderilir.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v gh >/dev/null || { echo "gh (GitHub CLI) gerekli: brew install gh"; exit 1; }

echo "1/3  Veritabanı adresi .streamlit/secrets.cloud.toml dosyasından okunuyor…"
.venv/bin/python - <<'PY' | gh secret set DB_URL
import tomllib
print(tomllib.load(open(".streamlit/secrets.cloud.toml", "rb"))["connections"]["portfolios"]["url"], end="")
PY
echo "     DB_URL ayarlandı."

read -r -p "2/3  Gönderen Gmail adresi: " SMTP_USER
gh secret set SMTP_USER --body "$SMTP_USER"
gh secret set MAIL_FROM --body "Portföy Modelleri <$SMTP_USER>"

echo "3/3  Gmail uygulama şifresi (https://myaccount.google.com/apppasswords — 16 harf, boşluksuz)."
echo "     Yazdığınız görünmez; bitince Enter'a basın:"
gh secret set SMTP_PASSWORD
echo
echo "Tamam. Denemek için: gh workflow run weekly-report.yml -f dry_run=false"

# Portfolio Models — self-hosted image
#   docker build -t portfolio-models .
#   docker run -p 8501:8501 -v pm-data:/data portfolio-models

# ── 1) Derleme: bağımlılıkları sanal ortama kur ─────────────────────────────────
FROM python:3.12-slim AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_NO_CACHE=1
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable \
    && find /app/.venv -name "tests" -type d -prune -exec rm -rf {} + \
    && find /app/.venv -name "*.pyi" -delete

# ── 2) Çalışma: yalnızca sanal ortam + giriş betiği ─────────────────────────────
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" PM_DATA_DIR=/data
WORKDIR /app
RUN useradd --create-home --uid 1000 app && mkdir -p /data /app/.streamlit && chown -R app:app /data /app
COPY --from=build --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app .streamlit/config.toml /app/.streamlit/config.toml
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/entrypoint.sh

USER app
VOLUME ["/data"]
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).read()==b'ok' else 1)"

ENTRYPOINT ["entrypoint.sh"]
CMD ["serve"]

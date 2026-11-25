# Contributing

Thanks for considering a contribution! Every size helps: a typo fix, a translation, a broker import format, a new model.

## Development setup

```bash
git clone https://github.com/ozanbayhan/portfolio-models && cd portfolio-models
uv sync                                   # installs Python 3.12 and all dependencies
uv run pytest -q                          # ~500 tests, about a minute
uv run portfolio-models serve             # the UI on http://localhost:8501 (local mode)
```

The UI reloads automatically when you edit files under `src/portfolio_models/`.

## Ground rules

- Open an issue first for larger changes so we can agree on the approach.
- Keep the maths in library modules (`src/portfolio_models/*.py`) and the UI thin (`web/`).
- Add or update tests for behaviour changes. `uv run pytest -q` must pass.
- User-facing text goes through `t()` and needs English and German translations (see below).
- One topic per pull request; describe what and why.

## Adding a model

1. Register it in `MODELS` in `src/portfolio_models/models.py`: a factory returning a skfolio-style estimator
   (`fit(returns)` → `weights_`) and a short Turkish description (the translation key).
2. If it comes from another library, wrap it in `adapters.py`.
3. Add a guide entry in `model_guide.py` (`year`, `origin`, `idea`, `read`, `strengths`, `caution` in `tr`/`en`/`de`).
4. Add the description's translations to `locales.py`.
5. Run `uv run pytest -q` — `tests/test_models.py` fits every registered model on sample data.
6. Regenerate the docs page: `uv run python scripts/gen_docs.py`.

## Translations

Turkish source strings are the keys; `src/portfolio_models/locales.py` maps each to `en` and `de`.

```bash
uv run python scripts/i18n_keys.py        # lists keys without English/German translations
```

**Adding a language:** add it to `LANGS` in `i18n.py`, add the language code to every catalogue entry and to the
`model_guide.py` texts. Partial translations are fine — missing strings fall back to Turkish — but please open a
draft PR early so others can help.

## Broker import formats

`trades_io.py` recognises column names and values through alias tables. To support a new broker, add its column
names/values there and a small sample file to `tests/test_trades_io.py`. Never commit real account data.

## Docs

The documentation site lives in `docs/` (MkDocs Material). Preview it with:

```bash
uvx --with mkdocs-material mkdocs serve
```

`docs/models.md` and `docs/metrics.md` are generated — edit `model_guide.py` instead.

## Releasing (maintainers)

Update `CHANGELOG.md` and the version in `pyproject.toml`, then tag `vX.Y.Z`; the Docker workflow publishes the image.

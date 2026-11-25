# FAQ

**Is it free?**
Yes — MIT licensed. The public demo runs on Streamlit Community Cloud; self-hosting costs only your server.

**Is my data safe on the demo?**
Only signed-in users can save, and every user sees only their own rows. For full control, run it yourself — local
mode never leaves your computer except for price requests.

**Which markets are supported?**
Anything on Yahoo Finance (stocks, ETFs, indices, FX, crypto, futures), BIST with automatic `.IS`, gram gold, cash in
any currency, and Turkish TEFAS funds via uploaded prices. Values are shown in TRY.

**Why do I have to upload TEFAS prices?**
TEFAS has no public API and blocks automated access. Exporting a CSV/Excel takes a few seconds and the app remembers
the history.

**Which model should I use?**
None of them is "the best". Use equal weight as the benchmark, look at the backtest on unseen data, and prefer models
where several approaches agree (the *consensus* comment). Read the [model guide](models.md) for each model's
weaknesses. This is not investment advice.

**Why are the weights different every run?**
They depend on the data window. A model whose weights swing wildly with small window changes is fragile — the
commentary warns about this.

**Can I add my own model?**
Yes — see [CONTRIBUTING](https://github.com/ozanbayhan/portfolio-models/blob/main/CONTRIBUTING.md#adding-a-model).

**Can I use another login than Google?**
Any OpenID Connect provider works; set `PM_OAUTH_METADATA_URL`. See [Self-hosting](self-hosting.md#google-login).

**Can I add a language?**
Yes, translations live in `src/portfolio_models/locales.py`. See CONTRIBUTING.

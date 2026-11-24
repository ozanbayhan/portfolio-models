# portfolio-models

Portföy optimizasyon modelleri tek bir komut satırı aracında toplandı. Aynı veri ve aynı backtest kurallarıyla yan yana karşılaştırılabilirler.

Modellerin kendisi aktif olarak geliştirilen açık kaynak kütüphanelerden geliyor. Bu repo onları bir arada kullanmanızı sağlıyor ve **her hafta güncellemeleri otomatik çekiyor**:

| Kütüphane | Ne katıyor |
|---|---|
| [skfolio](https://github.com/skfolio/skfolio) | Ana motor: Markowitz ailesi, risk paritesi, HRP/HERC/NCO, DRO, stacking, Black-Litterman, walk-forward backtest |
| [Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) | Geniş risk ölçüsü seti (CVaR, CDaR, EVaR…) |
| [PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) | Klasik etkin sınır ve Critical Line Algorithm |

## Kurulum

[uv](https://docs.astral.sh/uv/) gerekir (`brew install uv`).

```bash
git clone https://github.com/ozanbayhan/portfolio-models.git
cd portfolio-models
uv sync
```

## Web arayüzü

```bash
uv run streamlit run app.py
```

Tarayıcıda açılır. Sembolleri ve modelleri seçin; ağırlıkları, backtest sonuçlarını, Black-Litterman görüşlerini ve korelasyonları sekmelerde görün.

## Komut satırı

```bash
# Tüm modelleri listele
uv run portfolio-models list

# Güncel ağırlıklar: BIST hisseleri + altın
uv run portfolio-models weights --bist THYAO ASELS EREGL GARAN BIMAS --tickers GC=F

# Walk-forward backtest: 1 yıl eğit, ayda bir yeniden dengele, tüm modelleri karşılaştır
uv run portfolio-models backtest --bist THYAO ASELS EREGL GARAN BIMAS --tickers GC=F --start 2020-01-01

# Sadece seçili modeller, kendi CSV dosyanızla
uv run portfolio-models backtest --csv fiyatlar.csv --models hrp risk_parity max_sharpe
```

Çıktılar `results/` klasörüne yazılır:
- `weights.csv`
- `backtest_summary.csv`
- `cumulative_returns.html`: etkileşimli grafik

Veri kaynakları:
- `--tickers`: Yahoo Finance sembolleri (`AAPL`, `GC=F`, `USDTRY=X`, `BTC-USD`…)
- `--bist`: BIST sembolleri; `.IS` eki otomatik eklenir
- `--csv`: ilk sütunu tarih, diğer sütunları fiyat olan kendi dosyanız

Python içinden kullanım için [examples/quickstart.py](examples/quickstart.py) dosyasına bakın. Kendi görüşlerinizi modele katmak için [examples/black_litterman.py](examples/black_litterman.py) örneğini kullanın.

## Modeller

| Ad | Açıklama |
|---|---|
| `equal_weighted` | Eşit ağırlık (1/N) |
| `inverse_volatility` | Volatilitenin tersiyle ağırlık |
| `min_variance` | Minimum varyans (Markowitz) |
| `max_sharpe` | Maksimum Sharpe oranı |
| `max_sharpe_shrunk` | Maks. Sharpe; büzülmüş beklenti ve Ledoit-Wolf kovaryans |
| `max_sortino` | Maksimum Sortino oranı |
| `min_cvar` | Minimum CVaR (%95) |
| `min_cdar` | Minimum CDaR (drawdown riski) |
| `min_max_drawdown` | Minimum maksimum düşüş |
| `max_diversification` | Maksimum çeşitlendirme oranı |
| `dro_cvar` | Dağılımsal olarak dayanıklı CVaR (Wasserstein) |
| `risk_parity` | Risk paritesi (varyans) |
| `risk_parity_cvar` | Risk paritesi (CVaR) |
| `hrp` | Hiyerarşik risk paritesi |
| `hrp_cdar` | HRP, CDaR ile |
| `herc` | Hiyerarşik eşit risk katkısı |
| `nco` | İç içe kümeler optimizasyonu |
| `schur` | Schur tamamlayıcı tahsis |
| `stacking` | Birden çok modeli birleştiren topluluk |
| `riskfolio_hrp` | Riskfolio-Lib HRP |
| `riskfolio_max_sharpe_cvar` | Riskfolio-Lib maks. getiri/CVaR |
| `riskfolio_min_cdar` | Riskfolio-Lib minimum CDaR |
| `pypfopt_max_sharpe` | PyPortfolioOpt maks. Sharpe |
| `pypfopt_cla_min_vol` | PyPortfolioOpt CLA min. volatilite |

**Yeni model eklemek:** [src/portfolio_models/models.py](src/portfolio_models/models.py) içindeki `MODELS` sözlüğüne bir satır ekleyin. skfolio'daki her tahminci doğrudan çalışır. Başka bir kütüphanenin modelini eklemek için [adapters.py](src/portfolio_models/adapters.py) dosyasına `getiriler -> ağırlıklar` döndüren bir fonksiyon yazmanız yeterli.

## Güncellemeler nasıl geliyor?

- **Dependabot** her pazartesi kütüphanelerin yeni sürümlerini kontrol eder ve tek bir Pull Request açar.
- **CI** her PR'da tüm modelleri sentetik veriyle test eder. Testler yeşilse PR'ı birleştirin.
- **Haftalık "en yeni sürümler" testi**, kütüphanelerin en son halleriyle çalışıp çalışmadığını kontrol eder. Bir güncelleme bir modeli bozarsa Actions sekmesinde görürsünüz.
- Kendi bilgisayarınızda güncellemek için `git pull && uv sync` yeterli. Kütüphaneleri hemen en yeni sürüme çekmek için `uv lock --upgrade && uv sync` çalıştırın.

## Bilinen sorunlar

- `pypfopt_hrp` kapalı: PyPortfolioOpt 1.6.0 güncel scipy ile uyumsuz. Upstream düzeltilince [models.py](src/portfolio_models/models.py) dosyasındaki satırı açın. HRP için `hrp` veya `riskfolio_hrp` kullanın.

## Uyarı

Bu araç eğitim ve araştırma amaçlıdır, yatırım tavsiyesi değildir. Geçmiş performans gelecekteki sonuçları garanti etmez.

## Lisans

MIT

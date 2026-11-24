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

**Canlı:** https://portfolio-models.streamlit.app — her `main` güncellemesinde otomatik yenilenir.

Yerelde:

```bash
uv run streamlit run app.py
```

Tarayıcıda açılır. Sembolleri ve modelleri seçin; ağırlıkları, backtest sonuçlarını, Black-Litterman görüşlerini ve korelasyonları sekmelerde görün.

### 💼 Portföyüm: gerçek portföy takibi

Uygulamanın **Portföyüm** sayfasında varlıklarınızı miktarlarıyla girip takip edebilirsiniz:

- **Desteklenen varlıklar:** BIST hisseleri, TEFAS fonları, Yahoo Finance'teki her sembol (ABD hisseleri, ETF'ler, kripto…), gram altın ve nakit (TRY, USD, EUR…).
- **TL değerleme:** Döviz cinsinden varlıklar güncel kurla TL'ye çevrilir. Günlük değişim ve dağılım gösterilir. Ortalama maliyet girilen varlıklar için kâr/zarar hesaplanır.
- **Geçmiş:** Bugünkü miktarlarla son 1 yılın portföy değeri grafiği.
- **Yeniden dengeleme:** Seçtiğiniz modele (HRP, risk paritesi, maks. Sharpe…) göre hangi varlıktan kaç adet alıp satmanız gerektiği listelenir. BIST hisseleri tam adete yuvarlanır.
- **Kayıt:** Giriş yaptıysanız pozisyonlarınız adlandırılarak kaydedilir; yalnızca siz görürsünüz.

**TEFAS fonları:** TEFAS otomatik veri erişimini engellediği için fonun güncel birim fiyatını siz girersiniz ([tefas.gov.tr → Fon Verileri](https://www.tefas.gov.tr/tr/fon-verileri)). Fonlar toplam değer, dağılım ve kâr/zarara dahil edilir. Fiyat geçmişi olmadığı için yeniden dengelemede oldukları gibi bırakılır.

### Giriş ve portföy kaydetme

Kullanıcılar Google hesaplarıyla giriş yapıp ayarlarını adlandırarak kaydedebilir. Kaydedilenler semboller, tarihler, modeller, backtest ayarları ve Black-Litterman görüşleri. Her kullanıcı **yalnızca kendi kayıtlarını** görür, yükler ve siler; bu kontrol sunucu tarafında, e-postaya göre yapılır. Uygulama girişsiz de kullanılabilir, ama kayıt için giriş gerekir.

Sunucuda bu özelliği açmak için Streamlit Cloud → **Manage app → Settings → Secrets** alanına şunları girin:

```toml
[auth]
redirect_uri = "https://portfolio-models.streamlit.app/oauth2callback"
cookie_secret = "<rastgele uzun bir metin: python -c 'import secrets; print(secrets.token_hex(32))'>"
client_id = "<Google OAuth istemci kimliği>"
client_secret = "<Google OAuth istemci gizli anahtarı>"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[connections.portfolios]
url = "postgresql+psycopg://<Supabase session pooler bağlantı adresi>"
```

Ayarlar yapılmazsa kayıt özelliği kapalı kalır, uygulamanın geri kalanı çalışmaya devam eder. Yerelde girişsiz denemek için `.streamlit/secrets.toml` dosyasına `local_mode = true` yazın; kayıtlar `portfolios.db` dosyasına yazılır.

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

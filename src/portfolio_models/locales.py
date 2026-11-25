"""Çeviri kataloğu: Türkçe metin -> {"en": ..., "de": ...}.

Yeni bir t("...") metni eklediğinizde buraya da ekleyin; `tests/test_i18n.py` eksikleri yakalar.
Eksik çevirileri listelemek için: .venv/bin/python scripts/i18n_keys.py
"""

from __future__ import annotations


def E(en: str, de: str) -> dict[str, str]:
    return {"en": en, "de": de}


CATALOG: dict[str, dict[str, str]] = {
    # --- Genel ---------------------------------------------------------------------------------
    " ve ": E(" and ", " und "),
    "Portföy Modelleri": E("Portfolio Models", "Portfolio-Modelle"),
    "Model analizi": E("Model analysis", "Modellanalyse"),
    "📊 Model analizi": E("📊 Model analysis", "📊 Modellanalyse"),
    "Portföyüm": E("My portfolio", "Mein Portfolio"),
    "💼 Portföyüm": E("💼 My portfolio", "💼 Mein Portfolio"),
    "Eğitim amaçlıdır, yatırım tavsiyesi değildir.": E("For education only, not investment advice.",
                                                       "Nur zu Bildungszwecken, keine Anlageberatung."),
    "Gizlilik": E("Privacy", "Datenschutz"),
    "Koşullar": E("Terms", "Bedingungen"),
    "← Uygulamaya dön": E("← Back to the app", "← Zurück zur App"),
    "Seçin…": E("Select…", "Auswählen…"),
    "Yükle": E("Load", "Laden"),
    "Sil": E("Delete", "Löschen"),
    "Kaydet": E("Save", "Speichern"),
    "Hesapla": E("Calculate", "Berechnen"),
    "Açık": E("On", "An"),
    "Kapalı": E("Off", "Aus"),
    "puan": E("pp", "Prozentpunkte"),
    "Sharpe": E("Sharpe", "Sharpe"),
    "Sortino": E("Sortino", "Sortino"),
    "Yahoo Finance": E("Yahoo Finance", "Yahoo Finance"),
    "CSV dosyası": E("CSV file", "CSV-Datei"),
    "“{name}” yüklendi.": E("“{name}” loaded.", "„{name}“ geladen."),
    "“{name}” kaydedildi.": E("“{name}” saved.", "„{name}“ gespeichert."),
    "“{name}” silindi.": E("“{name}” deleted.", "„{name}“ gelöscht."),
    "Hesaplanamadı: {err}": E("Could not calculate: {err}", "Berechnung fehlgeschlagen: {err}"),
    "Dosya okunamadı: {err}": E("Could not read the file: {err}", "Datei konnte nicht gelesen werden: {err}"),

    # --- Giriş ve kayıt -------------------------------------------------------------------------
    "Giriş ve kayıt özelliği bu sunucuda henüz ayarlanmadı.": E(
        "Sign-in and saving are not set up on this server yet.",
        "Anmeldung und Speichern sind auf diesem Server noch nicht eingerichtet."),
    "Portföylerinizi kaydetmek için giriş yapın. Kayıtlarınızı yalnızca siz görürsünüz.": E(
        "Sign in to save your portfolios. Only you can see your records.",
        "Melden Sie sich an, um Ihre Portfolios zu speichern. Nur Sie sehen Ihre Einträge."),
    "Google ile giriş yap": E("Sign in with Google", "Mit Google anmelden"),
    "Yerel mod: giriş kapalı, kayıtlar bu bilgisayardaki portfolios.db dosyasında.": E(
        "Local mode: sign-in is off; records are stored in portfolios.db on this computer.",
        "Lokaler Modus: Anmeldung aus; Einträge liegen in portfolios.db auf diesem Rechner."),
    "Giriş: **{email}**": E("Signed in: **{email}**", "Angemeldet: **{email}**"),
    "Çıkış": E("Sign out", "Abmelden"),
    "Kaydetmek için giriş yapın.": E("Sign in to save.", "Zum Speichern bitte anmelden."),
    "Veritabanı ayarlanmamış; kayıt özelliği kapalı.": E(
        "No database configured; saving is disabled.", "Keine Datenbank eingerichtet; Speichern ist deaktiviert."),
    "Veritabanına bağlanılamadı: {err}": E("Could not connect to the database: {err}",
                                            "Keine Verbindung zur Datenbank: {err}"),
    "Analiz ayarlarım": E("My analysis settings", "Meine Analyse-Einstellungen"),
    "Kayıtlı ayarlar": E("Saved settings", "Gespeicherte Einstellungen"),
    "Henüz kayıtlı ayarınız yok.": E("No saved settings yet.", "Noch keine gespeicherten Einstellungen."),
    "Bu ayarları kaydet": E("Save these settings", "Diese Einstellungen speichern"),
    "Ad, örn. BIST + Altın": E("Name, e.g. BIST + Gold", "Name, z. B. BIST + Gold"),
    "CSV verisi kaydedilmez; kaydetmek için Yahoo Finance kaynağını kullanın.": E(
        "CSV data is not saved; use Yahoo Finance as the source to save.",
        "CSV-Daten werden nicht gespeichert; verwenden Sie zum Speichern Yahoo Finance als Quelle."),
    "Kullanıcı e-postası boş olamaz.": E("User email cannot be empty.", "Die E-Mail-Adresse darf nicht leer sein."),
    "Portföy adı boş olamaz.": E("Portfolio name cannot be empty.", "Der Portfolioname darf nicht leer sein."),
    "Portföy adı en fazla 120 karakter olabilir.": E("Portfolio name can be at most 120 characters.",
                                                     "Der Portfolioname darf höchstens 120 Zeichen lang sein."),
    "En fazla {n} portföy kaydedebilirsiniz.": E("You can save at most {n} portfolios.",
                                                 "Sie können höchstens {n} Portfolios speichern."),
    "Bilinmeyen kayıt türü: {kind}": E("Unknown record type: {kind}", "Unbekannter Eintragstyp: {kind}"),

    # --- Model analizi: kenar çubuğu ---------------------------------------------------------
    "Veri": E("Data", "Daten"),
    "Kaynak": E("Source", "Quelle"),
    "BIST hisseleri": E("BIST stocks", "BIST-Aktien"),
    "Boşlukla ayırın; .IS eki otomatik eklenir.": E("Separate with spaces; the .IS suffix is added automatically.",
                                                     "Mit Leerzeichen trennen; das Suffix .IS wird automatisch ergänzt."),
    "Diğer semboller": E("Other symbols", "Weitere Symbole"),
    "Yahoo sembolleri: GC=F (altın), USDTRY=X, BTC-USD, AAPL…": E(
        "Yahoo symbols: GC=F (gold), USDTRY=X, BTC-USD, AAPL…", "Yahoo-Symbole: GC=F (Gold), USDTRY=X, BTC-USD, AAPL…"),
    "Başlangıç": E("Start", "Beginn"),
    "Bitiş": E("End", "Ende"),
    "Fiyat dosyası (.csv)": E("Price file (.csv)", "Preisdatei (.csv)"),
    "İlk sütun tarih, diğer sütunlar varlık fiyatları.": E("First column dates, other columns asset prices.",
                                                          "Erste Spalte Datum, weitere Spalten Kurse der Werte."),
    "Modeller": E("Models", "Modelle"),
    "Karşılaştırılacak modeller": E("Models to compare", "Zu vergleichende Modelle"),
    "Tümünü seç": E("Select all", "Alle auswählen"),
    "Eğitim penceresi (iş günü)": E("Training window (business days)", "Trainingsfenster (Handelstage)"),
    "252 ≈ 1 yıl": E("252 ≈ 1 year", "252 ≈ 1 Jahr"),
    "Yeniden dengeleme aralığı (iş günü)": E("Rebalancing interval (business days)",
                                             "Rebalancing-Intervall (Handelstage)"),
    "21 ≈ 1 ay": E("21 ≈ 1 month", "21 ≈ 1 Monat"),

    # --- Model analizi: ana alan ----------------------------------------------------------------
    "Sol panelden bir CSV dosyası yükleyin.": E("Upload a CSV file in the left panel.",
                                                "Laden Sie links eine CSV-Datei hoch."),
    "En az 2 sembol girin.": E("Enter at least 2 symbols.", "Geben Sie mindestens 2 Symbole ein."),
    "Fiyatlar indiriliyor…": E("Downloading prices…", "Kurse werden geladen…"),
    "Veri yüklenemedi: {err}": E("Could not load data: {err}", "Daten konnten nicht geladen werden: {err}"),
    "En az bir model seçin.": E("Select at least one model.", "Wählen Sie mindestens ein Modell."),
    "Varlık": E("Asset", "Wert"),
    "Gün": E("Days", "Tage"),
    "Dönem": E("Period", "Zeitraum"),
    "Ağırlıklar": E("Weights", "Gewichte"),
    "📚 Modeller ve rehber": E("📚 Models & guide", "📚 Modelle & Leitfaden"),
    "**{name}** atlandı: {err}": E("**{name}** skipped: {err}", "**{name}** übersprungen: {err}"),
    "Ağırlık": E("Weight", "Gewicht"),
    "Güncel ağırlıklar": E("Current weights", "Aktuelle Gewichte"),
    "Her model seçilen dönemin tamamıyla eğitilir; bugün kurulacak portföyü gösterir.": E(
        "Each model is trained on the whole selected period and shows the portfolio you would build today.",
        "Jedes Modell wird mit dem gesamten Zeitraum trainiert und zeigt das Portfolio, das heute gebildet würde."),
    "Modeller eğitiliyor…": E("Training models…", "Modelle werden trainiert…"),
    "CSV indir": E("Download CSV", "CSV herunterladen"),
    "🧠 Yorumlar": E("🧠 Commentary", "🧠 Kommentare"),
    "Ekrandaki ağırlıklardan ve seçilen dönemin fiyat verisinden otomatik üretilir. Eğitim amaçlıdır, yatırım tavsiyesi değildir.": E(
        "Generated automatically from the weights on screen and the price data of the selected period. For education only, not investment advice.",
        "Automatisch aus den angezeigten Gewichten und den Kursdaten des gewählten Zeitraums erzeugt. Nur zu Bildungszwecken, keine Anlageberatung."),
    "**Genel tablo**": E("**Overall picture**", "**Gesamtbild**"),
    "**📚 Tarihçe ve okuma rehberi**": E("**📚 History & how to read it**", "**📚 Geschichte & Leseanleitung**"),
    "Her model {train} iş günü veriyle eğitilir, sonraki {test} gün tutulur, sonra pencere kaydırılır. Sonuçlar yalnızca modelin o an göremediği verilerden hesaplanır.": E(
        "Each model is trained on {train} business days, held for the next {test} days, then the window rolls forward. Results come only from data the model could not see at the time.",
        "Jedes Modell wird mit {train} Handelstagen trainiert, die nächsten {test} Tage gehalten, dann rollt das Fenster weiter. Die Ergebnisse stammen nur aus Daten, die das Modell zu dem Zeitpunkt nicht kannte."),
    "Bu ayarlar için veri kısa; başlangıç tarihini geriye alın veya eğitim penceresini küçültün.": E(
        "Not enough data for these settings; move the start date back or shorten the training window.",
        "Zu wenige Daten für diese Einstellungen; verlegen Sie das Startdatum nach vorne oder verkürzen Sie das Trainingsfenster."),
    "Backtest'i çalıştır": E("Run backtest", "Backtest starten"),
    "{n} model test ediliyor…": E("Testing {n} models…", "{n} Modelle werden getestet…"),
    "Ayarlar değişti; güncel sonuç için backtest'i yeniden çalıştırın.": E(
        "Settings changed; run the backtest again for up-to-date results.",
        "Einstellungen geändert; starten Sie den Backtest erneut für aktuelle Ergebnisse."),
    "**🧠 Yorum**": E("**🧠 Commentary**", "**🧠 Kommentar**"),
    "Özet CSV indir": E("Download summary CSV", "Zusammenfassung als CSV"),
    "Yıllık getiri": E("Annual return", "Jährliche Rendite"),
    "Yıllık volatilite": E("Annual volatility", "Jährliche Volatilität"),
    "Maks. düşüş": E("Max drawdown", "Max. Drawdown"),
    "CVaR %95": E("CVaR 95%", "CVaR 95 %"),
    "Kendi görüşlerinizle Black-Litterman": E("Black-Litterman with your own views",
                                              "Black-Litterman mit Ihren eigenen Einschätzungen"),
    "Görüşlerinizi yıllık getiri olarak girin. **Mutlak**: varlık bu kadar getirir. **Göreli**: Varlık 1, Varlık 2'yi bu kadar geçer. Model geçmiş veriyle görüşlerinizi harmanlar.": E(
        "Enter your views as annual returns. **Absolute**: the asset returns this much. **Relative**: Asset 1 beats Asset 2 by this much. The model blends your views with historical data.",
        "Geben Sie Ihre Einschätzungen als Jahresrendite ein. **Absolut**: Der Wert erzielt so viel. **Relativ**: Wert 1 schlägt Wert 2 um so viel. Das Modell mischt Ihre Einschätzungen mit historischen Daten."),
    "Mutlak": E("Absolute", "Absolut"),
    "Göreli": E("Relative", "Relativ"),
    "Tür": E("Type", "Art"),
    "Varlık 1": E("Asset 1", "Wert 1"),
    "Varlık 2": E("Asset 2", "Wert 2"),
    "Yıllık getiri %": E("Annual return %", "Jährliche Rendite %"),
    "Görüşlere güven (tau)": E("Confidence in views (tau)", "Vertrauen in Einschätzungen (Tau)"),
    "Büyüdükçe görüşleriniz daha ağır basar.": E("Higher values give your views more weight.",
                                                  "Je höher, desto stärker zählen Ihre Einschätzungen."),
    "Görüşsüz (maks. Sharpe)": E("Without views (max Sharpe)", "Ohne Einschätzungen (max. Sharpe)"),
    "Görüşlerle (Black-Litterman)": E("With views (Black-Litterman)", "Mit Einschätzungen (Black-Litterman)"),
    "📚 Black-Litterman nedir?": E("📚 What is Black-Litterman?", "📚 Was ist Black-Litterman?"),
    "Normalize fiyatlar (başlangıç = 100)": E("Normalised prices (start = 100)", "Normierte Kurse (Start = 100)"),
    "Korelasyon": E("Correlation", "Korrelation"),
    "Sonuçlar nasıl okunur?": E("How to read the results", "So lesen Sie die Ergebnisse"),
    "Modeller: tarihçe ve okuma rehberi": E("Models: history and reading guide", "Modelle: Geschichte und Leseanleitung"),
    "Her modelin kim tarafından, ne zaman geliştirildiği, temel fikri ve sonuçlarının nasıl okunacağı.": E(
        "Who developed each model and when, its core idea, and how to read its results.",
        "Wer jedes Modell wann entwickelt hat, seine Grundidee und wie man seine Ergebnisse liest."),

    # --- Model açıklamaları --------------------------------------------------------------------
    "Eşit ağırlık (1/N)": E("Equal weight (1/N)", "Gleichgewichtung (1/N)"),
    "Volatilitenin tersiyle ağırlık": E("Inverse-volatility weighting", "Gewichtung nach inverser Volatilität"),
    "Minimum varyans (Markowitz)": E("Minimum variance (Markowitz)", "Minimum-Varianz (Markowitz)"),
    "Maksimum Sharpe oranı": E("Maximum Sharpe ratio", "Maximale Sharpe-Ratio"),
    "Maks. Sharpe, büzülmüş (shrinkage) beklenti ve Ledoit-Wolf kovaryans": E(
        "Max Sharpe with shrunk expected returns and Ledoit-Wolf covariance",
        "Max. Sharpe mit geschrumpften Erwartungen und Ledoit-Wolf-Kovarianz"),
    "Minimum CVaR (%95)": E("Minimum CVaR (95%)", "Minimum-CVaR (95 %)"),
    "Maksimum Sortino oranı": E("Maximum Sortino ratio", "Maximale Sortino-Ratio"),
    "Minimum CDaR (drawdown riski)": E("Minimum CDaR (drawdown risk)", "Minimum-CDaR (Drawdown-Risiko)"),
    "Minimum maksimum düşüş": E("Minimum max drawdown", "Minimaler maximaler Drawdown"),
    "Maksimum çeşitlendirme oranı": E("Maximum diversification ratio", "Maximale Diversifikationsquote"),
    "Dağılımsal olarak dayanıklı CVaR (Wasserstein)": E("Distributionally robust CVaR (Wasserstein)",
                                                         "Verteilungsrobuster CVaR (Wasserstein)"),
    "Risk paritesi (eşit risk katkısı, varyans)": E("Risk parity (equal risk contribution, variance)",
                                                    "Risikoparität (gleicher Risikobeitrag, Varianz)"),
    "Risk paritesi (CVaR)": E("Risk parity (CVaR)", "Risikoparität (CVaR)"),
    "Hiyerarşik risk paritesi (Lopez de Prado)": E("Hierarchical risk parity (López de Prado)",
                                                   "Hierarchische Risikoparität (López de Prado)"),
    "HRP, CDaR risk ölçüsüyle": E("HRP with the CDaR risk measure", "HRP mit dem Risikomaß CDaR"),
    "Hiyerarşik eşit risk katkısı": E("Hierarchical equal risk contribution", "Hierarchischer gleicher Risikobeitrag"),
    "İç içe kümeler optimizasyonu": E("Nested clustered optimisation", "Verschachtelte Cluster-Optimierung"),
    "Schur tamamlayıcı tahsis (HRP ile min. varyans arası)": E(
        "Schur complementary allocation (between HRP and min variance)",
        "Schur-Komplement-Allokation (zwischen HRP und Minimum-Varianz)"),
    "Stacking: HRP + min var + risk paritesi + maks. çeşitlendirme": E(
        "Stacking: HRP + min var + risk parity + max diversification",
        "Stacking: HRP + Min-Var + Risikoparität + max. Diversifikation"),
    "Riskfolio-Lib HRP (ward)": E("Riskfolio-Lib HRP (Ward)", "Riskfolio-Lib HRP (Ward)"),
    "Riskfolio-Lib maks. getiri/CVaR": E("Riskfolio-Lib max return/CVaR", "Riskfolio-Lib max. Rendite/CVaR"),
    "Riskfolio-Lib minimum CDaR": E("Riskfolio-Lib minimum CDaR", "Riskfolio-Lib Minimum-CDaR"),
    "PyPortfolioOpt maks. Sharpe (Ledoit-Wolf)": E("PyPortfolioOpt max Sharpe (Ledoit-Wolf)",
                                                   "PyPortfolioOpt max. Sharpe (Ledoit-Wolf)"),
    "PyPortfolioOpt Critical Line Algorithm min. volatilite": E(
        "PyPortfolioOpt Critical Line Algorithm minimum volatility",
        "PyPortfolioOpt Critical Line Algorithm minimale Volatilität"),

    # --- Yorumlar (insights) -------------------------------------------------------------------
    "yüksek (dengeli dağılım)": E("high (well balanced)", "hoch (ausgewogen)"),
    "orta": E("moderate", "mittel"),
    "düşük (birkaç varlığa yoğunlaşmış)": E("low (concentrated in a few assets)", "niedrig (auf wenige Werte konzentriert)"),
    "**Ne yapar:** {what}": E("**What it does:** {what}", "**Was es tut:** {what}"),
    "**Dağılım:** En büyük pay **{top}** ({w}); ilk 3 varlığın toplam payı {top3}. Etkin varlık sayısı **{eff}** / {n} → çeşitlendirme {label}.": E(
        "**Allocation:** Largest weight **{top}** ({w}); the top 3 assets hold {top3}. Effective number of assets **{eff}** / {n} → diversification {label}.",
        "**Aufteilung:** Größtes Gewicht **{top}** ({w}); die Top 3 halten zusammen {top3}. Effektive Anzahl von Werten **{eff}** / {n} → Diversifikation {label}."),
    "**Dışarıda bıraktığı:** {assets} (payı {limit} altında).": E(
        "**Left out:** {assets} (weight below {limit}).", "**Ausgelassen:** {assets} (Gewicht unter {limit})."),
    "**Risk kaynağı:** Toplam riskin {share} kadarı **{asset}** varlığından geliyor.": E(
        "**Risk source:** {share} of total risk comes from **{asset}**.",
        "**Risikoquelle:** {share} des Gesamtrisikos stammen von **{asset}**."),
    "Sermaye payından daha fazla risk taşıyor; oynaklığı yüksek.": E(
        "It carries more risk than its share of capital; it is highly volatile.",
        "Es trägt mehr Risiko als sein Kapitalanteil; es ist sehr volatil."),
    "**Geçmiş veriye göre:** yıllık beklenen getiri ~{ret}, oynaklık ~{vol} (getiri/risk {sr}).": E(
        "**Based on history:** expected annual return ~{ret}, volatility ~{vol} (return/risk {sr}).",
        "**Laut Historie:** erwartete Jahresrendite ~{ret}, Volatilität ~{vol} (Rendite/Risiko {sr})."),
    "daha az riskle daha fazla getiri.": E("more return with less risk.", "mehr Rendite bei weniger Risiko."),
    "daha az risk, daha az getiri.": E("less risk, less return.", "weniger Risiko, weniger Rendite."),
    "daha fazla riskle daha fazla getiri.": E("more return with more risk.", "mehr Rendite bei mehr Risiko."),
    "daha fazla risk, daha az getiri; bu dönemde verimsiz.": E(
        "more risk, less return; inefficient in this period.", "mehr Risiko, weniger Rendite; in diesem Zeitraum ineffizient."),
    "Eşit ağırlığa göre oynaklık {dv}, getiri {dr} — {verdict}": E(
        "Versus equal weight: volatility {dv}, return {dr} — {verdict}",
        "Gegenüber Gleichgewichtung: Volatilität {dv}, Rendite {dr} — {verdict}"),
    "Portföyün yarısından fazlası tek varlıkta ({asset}); o varlıktaki bir düşüş portföyü sert etkiler.": E(
        "More than half the portfolio is in one asset ({asset}); a fall in it would hit the portfolio hard.",
        "Mehr als die Hälfte des Portfolios steckt in einem Wert ({asset}); ein Rückgang dort träfe das Portfolio hart."),
    "**Dikkat:** ": E("**Caution:** ", "**Vorsicht:** "),
    "En sakin varlık **{calm}** (yıllık oynaklık {v1}), en oynak varlık **{wild}** ({v2}). Riski azaltmaya çalışan modeller (min. varyans, risk paritesi, HRP) sakin varlığa yönelir.": E(
        "The calmest asset is **{calm}** (annual volatility {v1}), the most volatile is **{wild}** ({v2}). Risk-reducing models (min variance, risk parity, HRP) lean towards the calm one.",
        "Der ruhigste Wert ist **{calm}** (jährliche Volatilität {v1}), der volatilste **{wild}** ({v2}). Risikomindernde Modelle (Minimum-Varianz, Risikoparität, HRP) bevorzugen den ruhigen Wert."),
    "Dönemin en yüksek ortalama getirisi: **{best}** ({r1}/yıl); en düşüğü: **{worst}** ({r2}/yıl). Getiri odaklı modeller (maks. Sharpe/Sortino) ilkine yüklenir.": E(
        "Highest average return in the period: **{best}** ({r1}/yr); lowest: **{worst}** ({r2}/yr). Return-seeking models (max Sharpe/Sortino) pile into the former.",
        "Höchste Durchschnittsrendite im Zeitraum: **{best}** ({r1}/Jahr); niedrigste: **{worst}** ({r2}/Jahr). Renditeorientierte Modelle (max. Sharpe/Sortino) setzen stark auf Ersteren."),
    "En çok birlikte hareket eden ikili **{a} – {b}** (korelasyon {c1}); en bağımsız ikili **{d} – {e}** ({c2}). Düşük korelasyonlu varlıklar çeşitlendirmenin asıl kaynağıdır.": E(
        "The pair that moves together most is **{a} – {b}** (correlation {c1}); the most independent pair is **{d} – {e}** ({c2}). Low-correlation assets are the real source of diversification.",
        "Am stärksten gleichlaufend: **{a} – {b}** (Korrelation {c1}); am unabhängigsten: **{d} – {e}** ({c2}). Niedrig korrelierte Werte sind die eigentliche Quelle der Diversifikation."),
    "Modellerin çoğu şu varlıklara eşit ağırlıktan ({eq}) fazla pay öneriyor: **{assets}** ({k} modelden {counts}).": E(
        "Most models give more than equal weight ({eq}) to: **{assets}** ({counts} of {k} models).",
        "Die meisten Modelle geben mehr als Gleichgewicht ({eq}) für: **{assets}** ({counts} von {k} Modellen)."),
    "Çoğunluk şu varlıklara düşük pay veriyor: **{assets}**.": E(
        "The majority gives a low weight to: **{assets}**.", "Die Mehrheit gewichtet niedrig: **{assets}**."),
    "Modeller en çok **{asset}** konusunda ayrışıyor: payı {lo} ile {hi} arasında değişiyor. Bu varlık için seçtiğiniz model sonucu belirler.": E(
        "Models disagree most on **{asset}**: its weight ranges from {lo} to {hi}. For this asset, your choice of model decides the outcome.",
        "Am meisten uneinig sind die Modelle bei **{asset}**: Das Gewicht reicht von {lo} bis {hi}. Bei diesem Wert entscheidet Ihre Modellwahl."),
    "Tüm modellerin ortalaması: {items}.": E("Average across all models: {items}.", "Durchschnitt aller Modelle: {items}."),
    "Risk ayarlı en iyi sonuç **{best}** (Sharpe {s1}); en zayıf **{worst}** ({s2}).": E(
        "Best risk-adjusted result: **{best}** (Sharpe {s1}); weakest: **{worst}** ({s2}).",
        "Bestes risikobereinigtes Ergebnis: **{best}** (Sharpe {s1}); schwächstes: **{worst}** ({s2})."),
    "En yüksek yıllık getiri: **{model}** ({r}).": E("Highest annual return: **{model}** ({r}).",
                                                    "Höchste Jahresrendite: **{model}** ({r})."),
    "Bu modelde en derin düşüş {dd} oldu.": E("Its deepest drawdown was {dd}.", "Sein tiefster Drawdown betrug {dd}."),
    "En sığ düşüş: **{model}** ({dd}).": E("Shallowest drawdown: **{model}** ({dd}).", "Geringster Drawdown: **{model}** ({dd})."),
    "Karşılığında yıllık getiri {r}.": E("Its annual return in exchange: {r}.", "Dafür eine Jahresrendite von {r}."),
    "Hiçbir model basit eşit ağırlığı (1/N) risk ayarlı olarak geçemedi; bu varlık setinde optimizasyon ek değer katmıyor.": E(
        "No model beat simple equal weight (1/N) on a risk-adjusted basis; optimisation adds no value for this set of assets.",
        "Kein Modell schlug die einfache Gleichgewichtung (1/N) risikobereinigt; Optimierung bringt bei diesen Werten keinen Mehrwert."),
    "{others} modelden {n} tanesi eşit ağırlığı (Sharpe {ew}) geçti.": E(
        "{n} of {others} models beat equal weight (Sharpe {ew}).", "{n} von {others} Modellen schlugen die Gleichgewichtung (Sharpe {ew})."),
    "Fark küçük (0,10'dan az); basit 1/N kadar iyi sayılabilir.": E(
        "The gap is small (under 0.10); simple 1/N is about as good.",
        "Der Abstand ist klein (unter 0,10); einfaches 1/N ist ungefähr gleich gut."),
    "Modellerin sonuçları birbirine çok yakın; model seçimi bu varlıklarda kritik değil.": E(
        "The models' results are very close; model choice is not critical for these assets.",
        "Die Ergebnisse liegen sehr nah beieinander; die Modellwahl ist bei diesen Werten nicht entscheidend."),
    "Not: {model} geçmiş getiriye duyarlı bir model; bu dönemdeki başarısı bir sonraki dönemde tekrar etmeyebilir. Farklı başlangıç tarihleriyle tekrar deneyin.": E(
        "Note: {model} is sensitive to past returns; its success in this period may not repeat. Try again with different start dates.",
        "Hinweis: {model} reagiert empfindlich auf vergangene Renditen; sein Erfolg muss sich nicht wiederholen. Probieren Sie andere Startdaten."),
    "Backtest geçmiş veriye dayanır; komisyon, vergi ve kaymayı içermez. Gelecek performansı garanti etmez.": E(
        "The backtest is based on historical data and excludes fees, taxes and slippage. It does not guarantee future performance.",
        "Der Backtest beruht auf historischen Daten ohne Gebühren, Steuern und Slippage. Er garantiert keine künftige Wertentwicklung."),
    "Görüşleriniz şu varlıkların payını artırdı: {items}.": E("Your views increased the weight of: {items}.",
                                                            "Ihre Einschätzungen erhöhten das Gewicht von: {items}."),
    "Payı azalanlar: {items}.": E("Weights reduced: {items}.", "Gewichte gesenkt: {items}."),
    "Görüşleriniz ağırlıkları kayda değer biçimde değiştirmedi; ya geçmiş veriyle uyumlu ya da güven (tau) düşük. Güveni artırarak etkisini görebilirsiniz.": E(
        "Your views did not change the weights much; either they agree with history or confidence (tau) is low. Raise confidence to see their effect.",
        "Ihre Einschätzungen änderten die Gewichte kaum; entweder passen sie zur Historie oder das Vertrauen (Tau) ist gering. Erhöhen Sie das Vertrauen, um die Wirkung zu sehen."),
    "Görüşlerin portföyde yol açtığı toplam değişim: {x}.": E("Total portfolio change caused by your views: {x}.",
                                                            "Gesamte durch Ihre Einschätzungen bewirkte Veränderung: {x}."),
    "En büyük açık: **{asset}** — şu an {cur}, model {tgt} öneriyor.": E(
        "Largest gap: **{asset}** — now {cur}, the model suggests {tgt}.",
        "Größte Lücke: **{asset}** — derzeit {cur}, das Modell empfiehlt {tgt}."),
    "En fazla azaltılması önerilen: **{asset}** ({cur} → {tgt}).": E(
        "Biggest suggested reduction: **{asset}** ({cur} → {tgt}).", "Größte empfohlene Reduzierung: **{asset}** ({cur} → {tgt})."),
    "Portföyünüz bu modele zaten çok yakın (sapma {d}); işlem yapmaya değmeyebilir.": E(
        "Your portfolio is already very close to this model (drift {d}); trading may not be worth it.",
        "Ihr Portfolio liegt bereits sehr nah an diesem Modell (Abweichung {d}); Umschichten lohnt sich womöglich nicht."),
    "Orta düzey sapma ({d}). Küçük işlemleri komisyon maliyetine göre atlamayı düşünebilirsiniz.": E(
        "Moderate drift ({d}). Consider skipping small trades given commission costs.",
        "Mittlere Abweichung ({d}). Kleine Transaktionen können Sie wegen der Gebühren eventuell auslassen."),
    "Sapma yüksek ({d}). Önerinin tamamını tek seferde uygulamak yerine kademeli geçiş daha az maliyetli ve daha az riskli olabilir.": E(
        "High drift ({d}). Moving gradually may be cheaper and less risky than applying the whole suggestion at once.",
        "Hohe Abweichung ({d}). Ein schrittweiser Umbau kann günstiger und risikoärmer sein als alles auf einmal."),

    # --- Portföyüm: türler, işlemler, sütunlar -------------------------------------------------
    "BIST hissesi": E("BIST stock", "BIST-Aktie"),
    "TEFAS fonu": E("TEFAS fund", "TEFAS-Fonds"),
    "Yahoo sembolü": E("Yahoo symbol", "Yahoo-Symbol"),
    "Gram altın": E("Gold (gram)", "Gold (Gramm)"),
    "Nakit": E("Cash", "Cash"),
    "Al": E("Buy", "Kauf"),
    "Sat": E("Sell", "Verkauf"),
    "Temettü": E("Dividend", "Dividende"),
    "Para yatır": E("Deposit", "Einzahlung"),
    "Para çek": E("Withdrawal", "Auszahlung"),
    "Sembol": E("Symbol", "Symbol"),
    "Miktar": E("Quantity", "Menge"),
    "Ort. maliyet": E("Avg. cost", "Ø Kosten"),
    "Güncel fiyat": E("Current price", "Aktueller Preis"),
    "Tarih": E("Date", "Datum"),
    "İşlem": E("Action", "Aktion"),
    "Adet": E("Units", "Stück"),
    "Fiyat": E("Price", "Preis"),
    "Tutar": E("Amount", "Betrag"),
    "Son fiyat": E("Last price", "Letzter Preis"),
    "Para birimi": E("Currency", "Währung"),
    "Fiyat tarihi": E("Price date", "Preisdatum"),
    "Değer (TL)": E("Value (TRY)", "Wert (TRY)"),
    "Günlük %": E("Daily %", "Täglich %"),
    "Maliyet (TL)": E("Cost (TRY)", "Kosten (TRY)"),
    "K/Z (TL)": E("P/L (TRY)", "G/V (TRY)"),
    "K/Z %": E("P/L %", "G/V %"),
    "Mevcut (TL)": E("Current (TRY)", "Aktuell (TRY)"),
    "Mevcut ağırlık": E("Current weight", "Aktuelles Gewicht"),
    "Hedef ağırlık": E("Target weight", "Zielgewicht"),
    "Hedef (TL)": E("Target (TRY)", "Ziel (TRY)"),
    "Tutar (TL)": E("Amount (TRY)", "Betrag (TRY)"),
    "Kalan adet": E("Remaining qty", "Restbestand"),
    "Gerçekleşen K/Z": E("Realised P/L", "Realisierter G/V"),
    "İlk işlem": E("First trade", "Erste Transaktion"),
    "İşlem (Al/Sat)": E("Action (Buy/Sell)", "Aktion (Kauf/Verkauf)"),

    # --- Portföyüm: sayfa ------------------------------------------------------------------------
    "Varlıklarınızı girin; güncel değer, kâr/zarar, geçmiş performans ve modele göre yeniden dengeleme önerisi hesaplanır. Fiyatlar Yahoo Finance'ten (BIST ~15 dk gecikmeli). Eğitim amaçlıdır, yatırım tavsiyesi değildir.": E(
        "Enter your assets to see current value, profit/loss, past performance and model-based rebalancing suggestions. Prices from Yahoo Finance (BIST ~15 min delayed). For education only, not investment advice.",
        "Erfassen Sie Ihre Werte für aktuellen Wert, Gewinn/Verlust, bisherige Wertentwicklung und modellbasierte Rebalancing-Vorschläge. Kurse von Yahoo Finance (BIST ~15 Min. verzögert). Nur zu Bildungszwecken, keine Anlageberatung."),
    "Girdikleriniz bu oturum kapanınca silinir.": E("Your entries are lost when this session ends.",
                                                   "Ihre Eingaben gehen verloren, wenn diese Sitzung endet."),
    "Kayıtlar okunamadı: {err}": E("Could not read records: {err}", "Einträge konnten nicht gelesen werden: {err}"),
    "Kayıtlı portföyler": E("Saved portfolios", "Gespeicherte Portfolios"),
    "Henüz kayıt yok": E("Nothing saved yet", "Noch nichts gespeichert"),
    "Portföy adı": E("Portfolio name", "Portfolioname"),
    "Pozisyonları ve işlemleri kaydeder. Fon fiyatları ayrıca, kendi sekmesinde kaydedilir.": E(
        "Saves positions and transactions. Fund prices are saved separately in their own tab.",
        "Speichert Positionen und Transaktionen. Fondspreise werden separat in ihrem eigenen Reiter gespeichert."),
    "Haftalık e-posta özeti açıldı: her pazartesi sabah {email} adresine gönderilir (son kaydettiğiniz portföy).": E(
        "Weekly email summary enabled: sent to {email} every Monday morning (your most recently saved portfolio).",
        "Wöchentliche E-Mail-Zusammenfassung aktiviert: jeden Montagmorgen an {email} (Ihr zuletzt gespeichertes Portfolio)."),
    "Haftalık e-posta özeti kapatıldı.": E("Weekly email summary disabled.", "Wöchentliche E-Mail-Zusammenfassung deaktiviert."),
    "📧 Haftalık e-posta özeti": E("📧 Weekly email summary", "📧 Wöchentliche E-Mail-Zusammenfassung"),
    "Her pazartesi 09:00'da son kaydettiğiniz portföyün değerini, haftalık değişimini ve fiyatı eskimiş fonları e-postayla gönderir.": E(
        "Every Monday at 09:00 (Istanbul time) we email the value and weekly change of your last saved portfolio, plus funds with stale prices.",
        "Jeden Montag um 09:00 Uhr (Istanbuler Zeit) senden wir Wert und Wochenveränderung Ihres zuletzt gespeicherten Portfolios sowie Fonds mit veralteten Preisen."),
    "📋 Pozisyonlar": E("📋 Positions", "📋 Positionen"),
    "🧾 İşlemler": E("🧾 Transactions", "🧾 Transaktionen"),
    "📈 Fon fiyatları": E("📈 Fund prices", "📈 Fondspreise"),
    "Tüm tabloları temizle": E("Clear all tables", "Alle Tabellen leeren"),
    "Pozisyonları ve işlemleri boşaltır.": E("Empties positions and transactions.", "Leert Positionen und Transaktionen."),
    "Şu an elinizde olanlar (tarihsiz). **BIST hissesi:** THYAO · **TEFAS fonu:** fon kodu (TTE, AFT…) — fiyatı **Güncel fiyat** sütununa ya da *Fon fiyatları* sekmesine girin · **Yahoo sembolü:** AAPL, BTC-USD, VOO… · **Gram altın:** sembol boş · **Nakit:** TRY, USD, EUR… · **Ort. maliyet** isteğe bağlı, varlığın kendi para biriminde (AAPL için $). İşlem geçmişi girdiğiniz varlıkları burada tekrar yazmayın; ikisi toplanır.": E(
        "What you hold right now (undated). **BIST stock:** THYAO · **TEFAS fund:** fund code (TTE, AFT…) — enter its price in **Current price** or the *Fund prices* tab · **Yahoo symbol:** AAPL, BTC-USD, VOO… · **Gold (gram):** leave symbol empty · **Cash:** TRY, USD, EUR… · **Avg. cost** optional, in the asset's own currency ($ for AAPL). Don't repeat assets you entered as transactions; both are added together.",
        "Was Sie aktuell halten (ohne Datum). **BIST-Aktie:** THYAO · **TEFAS-Fonds:** Fondscode (TTE, AFT…) — Preis in **Aktueller Preis** oder im Reiter *Fondspreise* eintragen · **Yahoo-Symbol:** AAPL, BTC-USD, VOO… · **Gold (Gramm):** Symbol leer lassen · **Cash:** TRY, USD, EUR… · **Ø Kosten** optional, in der Währung des Werts ($ bei AAPL). Werte, die Sie als Transaktionen erfasst haben, hier nicht erneut eintragen; beides wird addiert."),
    "Yalnızca TEFAS fonları için: güncel birim fiyat (TL). Fon fiyatları sekmesinde geçmiş yüklediyseniz boş bırakabilirsiniz.": E(
        "TEFAS funds only: current unit price (TRY). Leave empty if you uploaded a history in the Fund prices tab.",
        "Nur für TEFAS-Fonds: aktueller Anteilspreis (TRY). Leer lassen, wenn Sie im Reiter Fondspreise eine Historie hochgeladen haben."),
    "Her alım ve satımı tarihiyle girin; miktar ve ortalama maliyet bunlardan hesaplanır. **Fiyat** birim fiyattır ve varlığın kendi para birimindedir (BIST ve fonlar TL, gram altın TL/gram, AAPL $). Dövizli işlemler işlem günündeki kurla TL'ye çevrilir. **Temettü:** varlığı seçip net tutarı **Tutar**'a yazın. **Para yatır / Para çek:** Tür *Nakit*, Sembol para birimi (TRY, USD…), tutar **Tutar**'a — girerseniz nakit takibi açılır ve nakit bakiyesi işlemlerden hesaplanır.": E(
        "Enter every buy and sell with its date; quantity and average cost are derived from them. **Price** is the unit price in the asset's own currency (BIST and funds TRY, gold TRY/gram, AAPL $). Foreign-currency trades are converted to TRY at that day's rate. **Dividend:** choose the asset and enter the net amount in **Amount**. **Deposit / Withdrawal:** Type *Cash*, Symbol the currency (TRY, USD…), amount in **Amount** — once you add these, cash tracking turns on and your cash balance is derived from the transactions.",
        "Erfassen Sie jeden Kauf und Verkauf mit Datum; Menge und Durchschnittskosten werden daraus berechnet. **Preis** ist der Stückpreis in der Währung des Werts (BIST und Fonds TRY, Gold TRY/Gramm, AAPL $). Fremdwährungsgeschäfte werden zum Tageskurs in TRY umgerechnet. **Dividende:** Wert wählen und Nettobetrag unter **Betrag** eintragen. **Einzahlung / Auszahlung:** Art *Cash*, Symbol die Währung (TRY, USD…), Betrag unter **Betrag** — sobald Sie diese erfassen, wird die Cash-Verfolgung aktiv und der Kontostand aus den Transaktionen berechnet."),
    "📥 Dosyadan içe aktar / 📤 dışa aktar": E("📥 Import from file / 📤 export", "📥 Aus Datei importieren / 📤 exportieren"),
    "Aracı kurum ekstresi ya da kendi tablonuz (CSV/Excel). Tarih, işlem yönü (Al/Alış/Buy — Sat/Satış/Sell), sembol, adet ve fiyat sütunları otomatik tanınır; tür sütunu yoksa aşağıda seçtiğiniz tür kullanılır. Aynı işlem iki kez eklenmez.": E(
        "A broker statement or your own sheet (CSV/Excel). Date, side (Buy/Sell, also Turkish and German terms), symbol, quantity and price columns are detected automatically; if there is no type column, the type you choose below is used. The same transaction is never added twice.",
        "Ein Depotauszug oder Ihre eigene Tabelle (CSV/Excel). Datum, Richtung (Kauf/Verkauf, auch englische und türkische Begriffe), Symbol, Menge und Preis werden automatisch erkannt; fehlt eine Spalte für die Art, wird die unten gewählte verwendet. Dieselbe Transaktion wird nie doppelt erfasst."),
    "İşlem dosyası": E("Transactions file", "Transaktionsdatei"),
    "Tür sütunu yoksa": E("If there is no type column", "Falls keine Spalte für die Art"),
    "İşlemleri içe aktar": E("Import transactions", "Transaktionen importieren"),
    "{n} işlem eklendi.": E("{n} transactions added.", "{n} Transaktionen hinzugefügt."),
    "{n} tekrar eden işlem atlandı.": E("{n} duplicate transactions skipped.", "{n} doppelte Transaktionen übersprungen."),
    "(+{n} uyarı)": E("(+{n} warnings)", "(+{n} Hinweise)"),
    "Kalıcı olması için Kaydet'e basın.": E("Press Save to keep them.", "Klicken Sie auf Speichern, um sie zu behalten."),
    "Şablonu indir": E("Download template", "Vorlage herunterladen"),
    "Örnek satırlı, Excel'de açılabilen CSV şablonu.": E("CSV template with example rows; opens in Excel.",
                                                         "CSV-Vorlage mit Beispielzeilen; lässt sich in Excel öffnen."),
    "İşlemleri indir": E("Download transactions", "Transaktionen herunterladen"),
    "Temettü, para yatırma ve çekmede toplam tutar. Temettüde bunun yerine Adet × hisse başı temettü de girebilirsiniz.": E(
        "Total amount for dividends, deposits and withdrawals. For dividends you may instead enter Quantity × dividend per share.",
        "Gesamtbetrag bei Dividenden, Ein- und Auszahlungen. Bei Dividenden können Sie stattdessen Stück × Dividende je Aktie eingeben."),
    "İşlemlerden hesaplanan özet (tutarlar varlığın kendi para biriminde):": E(
        "Summary derived from transactions (amounts in each asset's own currency):",
        "Aus den Transaktionen berechnete Übersicht (Beträge in der Währung des jeweiligen Werts):"),
    "TEFAS fonlarının fiyat geçmişini buradan yükleyin ya da elle girin. Geçmişi olan fonlar değer grafiğine, günlük değişime ve yeniden dengelemeye katılır. [TEFAS → Fon Verileri](https://www.tefas.gov.tr/tr/fon-verileri) sayfasında fonu ve tarih aralığını seçip **Excel** ya da **CSV** ile indirin.": E(
        "Upload or type in the price history of TEFAS funds here. Funds with a history are included in the value chart, daily change and rebalancing. On [TEFAS → Fund Data](https://www.tefas.gov.tr/tr/fon-verileri) choose the fund and date range and download as **Excel** or **CSV**.",
        "Laden Sie hier die Preishistorie von TEFAS-Fonds hoch oder tragen Sie sie ein. Fonds mit Historie fließen in Wertdiagramm, Tagesveränderung und Rebalancing ein. Wählen Sie auf [TEFAS → Fondsdaten](https://www.tefas.gov.tr/tr/fon-verileri) Fonds und Zeitraum und laden Sie **Excel** oder **CSV** herunter."),
    "Fiyatlar hesabınıza kaydedilir.": E("Prices are saved to your account.", "Die Preise werden in Ihrem Konto gespeichert."),
    "(Giriş yapmadığınız için yalnızca bu oturumda tutulur.)": E("(Kept for this session only because you are not signed in.)",
                                                                 "(Nur für diese Sitzung gespeichert, da Sie nicht angemeldet sind.)"),
    "**📄 Dosyadan yükle**": E("**📄 Upload from file**", "**📄 Aus Datei hochladen**"),
    "TEFAS dosyası": E("TEFAS file", "TEFAS-Datei"),
    "Dosyada fon kodu yoksa": E("If the file has no fund code", "Falls die Datei keinen Fondscode enthält"),
    "ör. TTE": E("e.g. TTE", "z. B. TTE"),
    "ör. AFT": E("e.g. AFT", "z. B. AFT"),
    "İçe aktar": E("Import", "Importieren"),
    "Dosyada geçerli fiyat satırı bulunamadı.": E("No valid price rows found in the file.",
                                                  "In der Datei wurden keine gültigen Preiszeilen gefunden."),
    "{code}: {n} gün": E("{code}: {n} days", "{code}: {n} Tage"),
    "İçe aktarıldı — {summary}.": E("Imported — {summary}.", "Importiert — {summary}."),
    "**✏️ Elle gir / düzenle**": E("**✏️ Enter / edit manually**", "**✏️ Manuell eingeben / bearbeiten**"),
    "Yeni fon kodu ekle": E("Add a new fund code", "Neuen Fondscode hinzufügen"),
    "Önce bir fon kodu yazın ya da pozisyon/işlem tablosuna TEFAS fonu ekleyin.": E(
        "Type a fund code first, or add a TEFAS fund to the positions/transactions table.",
        "Geben Sie zuerst einen Fondscode ein oder fügen Sie der Positions-/Transaktionstabelle einen TEFAS-Fonds hinzu."),
    "Fon": E("Fund", "Fonds"),
    "Fiyat (TL)": E("Price (TRY)", "Preis (TRY)"),
    "Grafik için en az 2 fiyat gerekir.": E("At least 2 prices are needed for a chart.",
                                            "Für ein Diagramm werden mindestens 2 Preise benötigt."),
    "Fiyatları kaydet": E("Save prices", "Preise speichern"),
    "{code}: {n} fiyat kaydedildi.": E("{code}: {n} prices saved.", "{code}: {n} Preise gespeichert."),
    "Geçmişi sil": E("Delete history", "Historie löschen"),
    "{code} fiyat geçmişi silindi.": E("{code} price history deleted.", "Preishistorie von {code} gelöscht."),
    "Pozisyonlar veya İşlemler sekmesine en az bir varlık ekleyin.": E(
        "Add at least one asset in the Positions or Transactions tab.",
        "Fügen Sie im Reiter Positionen oder Transaktionen mindestens einen Wert hinzu."),
    "Güncel fiyatlar alınıyor…": E("Fetching current prices…", "Aktuelle Kurse werden abgerufen…"),
    "Fiyatlar alınamadı: {err}": E("Could not fetch prices: {err}", "Kurse konnten nicht abgerufen werden: {err}"),
    "{label} bakiyesi işlemlere göre eksiye düşüyor ({b}). Eksik para yatırma işlemi olabilir; eksi bakiye sıfır kabul edildi.": E(
        "{label} balance turns negative according to your transactions ({b}). A deposit may be missing; the negative balance is treated as zero.",
        "Laut Ihren Transaktionen wird der Saldo von {label} negativ ({b}). Möglicherweise fehlt eine Einzahlung; der negative Saldo wird als null behandelt."),
    "Fiyatlar hesaplanamadı: {err}": E("Could not calculate prices: {err}", "Kurse konnten nicht berechnet werden: {err}"),
    "Fiyat bulunamadı, hesaba katılmadı: {assets}. Sembolü kontrol edin.": E(
        "No price found, left out: {assets}. Check the symbol.", "Kein Kurs gefunden, nicht berücksichtigt: {assets}. Prüfen Sie das Symbol."),
    "Toplam değer": E("Total value", "Gesamtwert"),
    "Günlük değişim": E("Daily change", "Tagesveränderung"),
    "Açık pozisyon K/Z": E("Open P/L", "Offener G/V"),
    "Maliyeti bilinen varlıklar için. Dövizli varlıklarda bugünkü kurla.": E(
        "For assets with a known cost. Foreign-currency assets use today's rate.",
        "Für Werte mit bekannten Kosten. Fremdwährungswerte zum heutigen Kurs."),
    "Ort. maliyet girdiğiniz ya da işlem geçmişi olan varlıklar için.": E(
        "For assets with an average cost or a transaction history.", "Für Werte mit Ø Kosten oder Transaktionshistorie."),
    "Yıllık getiri (XIRR)": E("Annual return (XIRR)", "Jahresrendite (XIRR)"),
    "İşlem tarihleri ve tutarlarına göre yıllıklandırılmış getiri; en az 3 aylık işlem geçmişi gerekir.": E(
        "Annualised return based on transaction dates and amounts; needs at least 3 months of history.",
        "Annualisierte Rendite anhand von Transaktionsdaten und -beträgen; mindestens 3 Monate Historie nötig."),
    "Nakit takibi açık: yalnızca para yatırma/çekme dış akış sayılır.": E(
        "Cash tracking on: only deposits and withdrawals count as external flows.",
        "Cash-Verfolgung aktiv: Nur Ein- und Auszahlungen zählen als externe Flüsse."),
    "Alımlar para girişi, satışlar ve temettüler para çıkışı sayılır.": E(
        "Buys count as money in; sales and dividends as money out.", "Käufe zählen als Zufluss, Verkäufe und Dividenden als Abfluss."),
    "Tarihsiz pozisyon satırları hesaba katılmaz.": E("Undated position rows are excluded.",
                                                      "Positionszeilen ohne Datum werden nicht berücksichtigt."),
    "Satışlardan elde edilen kâr/zarar (bugünkü kurla).": E("Profit/loss from sales (at today's rate).",
                                                           "Gewinn/Verlust aus Verkäufen (zum heutigen Kurs)."),
    "Alınan temettü": E("Dividends received", "Erhaltene Dividenden"),
    "Temettü tarihindeki kurla TL.": E("In TRY at the rate on the dividend date.", "In TRY zum Kurs am Dividendentag."),
    "Net yatırılan": E("Net invested", "Netto investiert"),
    "Para yatırma − çekme": E("Deposits − withdrawals", "Einzahlungen − Auszahlungen"),
    "Alımlar − satımlar − temettüler": E("Buys − sales − dividends", "Käufe − Verkäufe − Dividenden"),
    "Nakit takibi": E("Cash tracking", "Cash-Verfolgung"),
    "İşlemlere 'Para yatır' / 'Para çek' eklediğinizde açılır: alımlar nakitten düşer, satış ve temettüler nakde eklenir.": E(
        "Turns on when you add 'Deposit' / 'Withdrawal' transactions: buys reduce cash, sales and dividends add to it.",
        "Wird aktiv, sobald Sie 'Einzahlung' / 'Auszahlung' erfassen: Käufe verringern das Cash, Verkäufe und Dividenden erhöhen es."),
    "⚠️ Fiyatı 7 günden eski fonlar: {funds}. Fon fiyatları sekmesinden güncelleyin.": E(
        "⚠️ Funds with prices older than 7 days: {funds}. Update them in the Fund prices tab.",
        "⚠️ Fonds mit Preisen älter als 7 Tage: {funds}. Aktualisieren Sie sie im Reiter Fondspreise."),
    "Döviz cinsinden varlıklarda K/Z %, varlığın kendi para birimindedir; TL tutarları bugünkü kurla çevrilir.": E(
        "For foreign-currency assets, P/L % is in the asset's own currency; TRY amounts use today's rate.",
        "Bei Fremdwährungswerten ist G/V % in der Währung des Werts; TRY-Beträge zum heutigen Kurs."),
    "Dağılım": E("Allocation", "Aufteilung"),
    "Portföy değeri": E("Portfolio value", "Portfoliowert"),
    "Gerçek elde tutulan miktarlarla değer": E("Value with actual holdings over time", "Wert mit tatsächlichen Beständen"),
    "(tarihsiz pozisyonlar tüm dönem dahil)": E("(undated positions included for the whole period)",
                                                "(Positionen ohne Datum über den gesamten Zeitraum enthalten)"),
    "Bugünkü miktarlarla son 1 yıl": E("Last year at today's quantities", "Letztes Jahr mit heutigen Mengen"),
    "📊 Bu varlıkları Model analizi sayfasında kullan": E("📊 Use these assets on the Model analysis page",
                                                         "📊 Diese Werte in der Modellanalyse verwenden"),
    "Sembolleri analiz sayfasının kenar çubuğuna aktarır.": E("Copies the symbols to the analysis page sidebar.",
                                                             "Überträgt die Symbole in die Seitenleiste der Analyse."),
    "Semboller aktarıldı. Soldaki menüden **📊 Model analizi** sayfasına geçin.": E(
        "Symbols copied. Switch to **📊 Model analysis** in the left menu.",
        "Symbole übertragen. Wechseln Sie im linken Menü zu **📊 Modellanalyse**."),
    "Yeniden dengeleme önerisi": E("Rebalancing suggestion", "Rebalancing-Vorschlag"),
    "Öneri için fiyat geçmişi olan en az 2 varlık gerekir (nakit ve geçmişi girilmemiş fonlar hariç).": E(
        "A suggestion needs at least 2 assets with price history (excluding cash and funds without history).",
        "Für einen Vorschlag braucht es mindestens 2 Werte mit Preishistorie (ohne Cash und Fonds ohne Historie)."),
    "Öneri için varlıkların ortak en az ~6 aylık fiyat geçmişi gerekir. Fonların geçmişini uzatmak için Fon fiyatları sekmesinden daha uzun dönem yükleyin.": E(
        "A suggestion needs at least ~6 months of shared price history. Upload a longer period in the Fund prices tab to extend fund histories.",
        "Für einen Vorschlag braucht es mindestens ~6 Monate gemeinsame Preishistorie. Laden Sie im Reiter Fondspreise einen längeren Zeitraum hoch."),
    "Nakdi de yatırıma dahil et": E("Also invest the cash", "Cash ebenfalls investieren"),
    "Model, varlıkların son {n} yıllık TL getirileriyle eğitilir. BIST hisseleri tam adete yuvarlanır.": E(
        "The model is trained on the last {n} years of TRY returns. BIST stocks are rounded to whole shares.",
        "Das Modell wird mit den TRY-Renditen der letzten {n} Jahre trainiert. BIST-Aktien werden auf ganze Stück gerundet."),
    "Fiyat geçmişi olmayan fonlar ({funds}) olduğu gibi bırakılır.": E(
        "Funds without price history ({funds}) are left as they are.", "Fonds ohne Preishistorie ({funds}) bleiben unverändert."),
    "Hedef ağırlıklar hesaplanıyor…": E("Calculating target weights…", "Zielgewichte werden berechnet…"),
    "Bu model bu varlıklarla çözüm bulamadı: {err}. Başka bir model deneyin.": E(
        "This model found no solution for these assets: {err}. Try another model.",
        "Dieses Modell fand für diese Werte keine Lösung: {err}. Versuchen Sie ein anderes Modell."),
    "Bu işlemler için {x} ek nakit gerekir.": E("These trades need {x} of extra cash.",
                                                "Für diese Transaktionen werden zusätzlich {x} Cash benötigt."),
    "İşlemler sonrası kalan nakit: {x} (TL karşılığı).": E("Cash left after trades: {x} (TRY equivalent).",
                                                           "Verbleibendes Cash nach den Transaktionen: {x} (TRY-Gegenwert)."),
    "Toplam işlem hacmi: {x} — portföy değerine oranı {r}. Komisyon ve vergiler dahil değildir.": E(
        "Total turnover: {x} — {r} of portfolio value. Excludes commissions and taxes.",
        "Gesamtumsatz: {x} — {r} des Portfoliowerts. Ohne Gebühren und Steuern."),

    # --- Karşılaştırma --------------------------------------------------------------------------
    "Karşılaştırma": E("Comparison", "Vergleich"),
    "Karşılaştırma için yeterli portföy geçmişi yok.": E("Not enough portfolio history for a comparison.",
                                                        "Zu wenig Portfoliohistorie für einen Vergleich."),
    "1 ay": E("1 month", "1 Monat"),
    "3 ay": E("3 months", "3 Monate"),
    "6 ay": E("6 months", "6 Monate"),
    "1 yıl": E("1 year", "1 Jahr"),
    "Yılbaşından": E("Year to date", "Seit Jahresbeginn"),
    "Tümü": E("All", "Alles"),
    "Benchmark verisi alınamadı: {err}": E("Could not fetch benchmark data: {err}",
                                           "Benchmarkdaten konnten nicht abgerufen werden: {err}"),
    "Seçilen dönem için veri yok.": E("No data for the selected period.", "Keine Daten für den gewählten Zeitraum."),
    "Başlangıç = 100": E("Start = 100", "Start = 100"),
    "Dolar (USD/TRY)": E("Dollar (USD/TRY)", "Dollar (USD/TRY)"),
    "Enflasyon (TÜFE)": E("Inflation (CPI)", "Inflation (VPI)"),
    "Seri": E("Series", "Reihe"),
    "Toplam getiri": E("Total return", "Gesamtrendite"),
    "Yıllık": E("Annual", "Jährlich"),
    "Reel (TÜFE'ye göre)": E("Real (vs CPI)", "Real (ggü. VPI)"),
    "Portföy getirisi zaman ağırlıklıdır (TWR): para yatırma/çekme ve alımların etkisi ayıklanır.": E(
        "Portfolio return is time-weighted (TWR): the effect of deposits, withdrawals and purchases is removed.",
        "Die Portfoliorendite ist zeitgewichtet (TWR): Der Effekt von Ein-/Auszahlungen und Käufen wird herausgerechnet."),
    "TÜFE: {src}, {month} ayına kadar; sonrası için reel getiri hesaplanmaz.": E(
        "CPI: {src}, up to {month}; real returns are not computed beyond that.",
        "VPI: {src}, bis {month}; danach wird keine Realrendite berechnet."),
    "TÜFE verisi şu an alınamadı.": E("CPI data is not available right now.", "VPI-Daten sind derzeit nicht verfügbar."),

    # --- İşlem ve pozisyon doğrulama ------------------------------------------------------------
    "Bilinmeyen tür: {kind}": E("Unknown type: {kind}", "Unbekannte Art: {kind}"),
    "Satır {i}: miktar sayı olmalı.": E("Row {i}: quantity must be a number.", "Zeile {i}: Menge muss eine Zahl sein."),
    "Satır {i}: miktar sıfırdan büyük olmalı.": E("Row {i}: quantity must be greater than zero.",
                                                  "Zeile {i}: Menge muss größer als null sein."),
    "Satır {i}: tür seçin.": E("Row {i}: choose a type.", "Zeile {i}: Art auswählen."),
    "Satır {i}: nakit için para birimi kodu yazın (TRY, USD, EUR…).": E(
        "Row {i}: enter a currency code for cash (TRY, USD, EUR…).", "Zeile {i}: Währungscode für Cash eingeben (TRY, USD, EUR…)."),
    "Satır {i}: TEFAS fon kodunu yazın (ör. TTE, AFT).": E("Row {i}: enter the TEFAS fund code (e.g. TTE, AFT).",
                                                          "Zeile {i}: TEFAS-Fondscode eingeben (z. B. TTE, AFT)."),
    "Satır {i}: sembol boş.": E("Row {i}: symbol is empty.", "Zeile {i}: Symbol ist leer."),
    "Satır {i}: {label} için fiyat yok. 'Güncel fiyat' sütununa birim fiyatı yazın ya da Fon fiyatları sekmesinden fiyat geçmişi yükleyin.": E(
        "Row {i}: no price for {label}. Enter the unit price in 'Current price' or upload a price history in the Fund prices tab.",
        "Zeile {i}: kein Preis für {label}. Tragen Sie den Anteilspreis unter 'Aktueller Preis' ein oder laden Sie im Reiter Fondspreise eine Historie hoch."),
    "Satır {i}: {label} birden fazla kez girilmiş; miktarları tek satırda toplayın.": E(
        "Row {i}: {label} is entered more than once; combine the quantities into one row.",
        "Zeile {i}: {label} wurde mehrfach erfasst; fassen Sie die Mengen in einer Zeile zusammen."),
    "İşlem {i}: tarih geçersiz.": E("Transaction {i}: invalid date.", "Transaktion {i}: ungültiges Datum."),
    "İşlem {i}: ileri tarihli işlem atlandı.": E("Transaction {i}: future-dated transaction skipped.",
                                                 "Transaktion {i}: Transaktion mit künftigem Datum übersprungen."),
    "İşlem {i}: işlem türünü seçin ({options}).": E("Transaction {i}: choose an action ({options}).",
                                                    "Transaktion {i}: Aktion wählen ({options})."),
    "İşlem {i}: para yatırma/çekme için Tür 'Nakit', Sembol para birimi (TRY, USD…) olmalı.": E(
        "Transaction {i}: for deposits/withdrawals, Type must be 'Cash' and Symbol the currency (TRY, USD…).",
        "Transaktion {i}: Bei Ein-/Auszahlungen muss die Art 'Cash' und das Symbol die Währung sein (TRY, USD…)."),
    "İşlem {i}: tutarı 'Tutar' sütununa yazın.": E("Transaction {i}: enter the amount in the 'Amount' column.",
                                                   "Transaktion {i}: Betrag in der Spalte 'Betrag' eintragen."),
    "İşlem {i}: tür seçin.": E("Transaction {i}: choose a type.", "Transaktion {i}: Art auswählen."),
    "Nakit yalnızca para yatırma/çekmede kullanılır.": E("Cash is only used for deposits and withdrawals.",
                                                         "Cash wird nur für Ein- und Auszahlungen verwendet."),
    "İşlem {i}: sembol boş.": E("Transaction {i}: symbol is empty.", "Transaktion {i}: Symbol ist leer."),
    "İşlem {i}: temettü için 'Tutar' ya da adet ve hisse başı temettü girin.": E(
        "Transaction {i}: for a dividend enter 'Amount', or quantity and dividend per share.",
        "Transaktion {i}: Für eine Dividende 'Betrag' oder Stück und Dividende je Aktie eingeben."),
    "İşlem {i}: adet ve fiyat sıfırdan büyük olmalı.": E("Transaction {i}: quantity and price must be greater than zero.",
                                                         "Transaktion {i}: Stück und Preis müssen größer als null sein."),
    "{label}: {date} tarihinde elde {have} adet varken {sold} adet satış girilmiş; fazlası yok sayıldı.": E(
        "{label}: on {date} you held {have} but {sold} were sold; the excess was ignored.",
        "{label}: Am {date} wurden {have} gehalten, aber {sold} verkauft; der Überschuss wurde ignoriert."),

    # --- Dosya içe aktarma -----------------------------------------------------------------------
    "Şu sütunlar bulunamadı: {missing}. Bulunan sütunlar: {found}": E(
        "These columns were not found: {missing}. Columns found: {found}",
        "Diese Spalten wurden nicht gefunden: {missing}. Gefundene Spalten: {found}"),
    "tarih": E("date", "Datum"),
    "işlem yönü": E("side", "Richtung"),
    "tutar": E("amount", "Betrag"),
    "temettü tutarı": E("dividend amount", "Dividendenbetrag"),
    "adet": E("quantity", "Stück"),
    "fiyat": E("price", "Preis"),
    "sembol": E("symbol", "Symbol"),
    "Dosya satırı {n}: {fields} okunamadı, atlandı.": E("File row {n}: could not read {fields}; skipped.",
                                                         "Dateizeile {n}: {fields} nicht lesbar; übersprungen."),
    "Dosyanın karakter kodlaması okunamadı.": E("Could not detect the file's character encoding.",
                                                 "Die Zeichenkodierung der Datei konnte nicht erkannt werden."),
    "Dosyada 'Tarih' ve 'Fiyat' sütunları bulunamadı. Bulunan sütunlar: {found}": E(
        "No 'Date' and 'Price' columns found in the file. Columns found: {found}",
        "In der Datei wurden keine Spalten 'Datum' und 'Preis' gefunden. Gefundene Spalten: {found}"),
    "Dosyada 'Fon Kodu' sütunu yok; yüklemeden önce fon kodunu seçin.": E(
        "The file has no 'Fund code' column; enter the fund code before uploading.",
        "Die Datei hat keine Spalte 'Fondscode'; geben Sie vor dem Hochladen den Fondscode ein."),
    "{n} satır okunamadı ve atlandı.": E("{n} rows could not be read and were skipped.",
                                         "{n} Zeilen konnten nicht gelesen werden und wurden übersprungen."),
    "{n} satır ileri tarihli olduğu için atlandı.": E("{n} future-dated rows were skipped.",
                                                      "{n} Zeilen mit künftigem Datum wurden übersprungen."),
    "{d}: fiyat geçersiz, atlandı.": E("{d}: invalid price, skipped.", "{d}: ungültiger Preis, übersprungen."),
    "{d}: ileri tarih, atlandı.": E("{d}: future date, skipped.", "{d}: künftiges Datum, übersprungen."),

    # --- E-posta özeti -------------------------------------------------------------------------
    "Fiyat bulunamadı: {assets}": E("No price found: {assets}", "Kein Kurs gefunden: {assets}"),
    "Bu hafta": E("This week", "Diese Woche"),
    "Haftalık portföy özeti": E("Weekly portfolio summary", "Wöchentliche Portfolio-Zusammenfassung"),
    "Değer": E("Value", "Wert"),
    "Haftalık": E("Weekly", "Woche"),
    "Portföyümü aç →": E("Open my portfolio →", "Mein Portfolio öffnen →"),
    "⚠️ Fiyatı 7 günden eski fonlar: {funds}. Uygulamada Fon fiyatları sekmesinden güncelleyebilirsiniz.": E(
        "⚠️ Funds with prices older than 7 days: {funds}. You can update them in the app's Fund prices tab.",
        "⚠️ Fonds mit Preisen älter als 7 Tage: {funds}. Sie können sie in der App im Reiter Fondspreise aktualisieren."),
    "Haftalık değişim bugünkü miktarlarla hesaplanır. Eğitim amaçlıdır, yatırım tavsiyesi değildir. Bu e-postaları almak istemiyorsanız uygulamada Portföyüm sayfasındaki \"Haftalık e-posta özeti\" anahtarını kapatın.": E(
        "The weekly change is calculated with today's quantities. For education only, not investment advice. To stop these emails, switch off \"Weekly email summary\" on the My portfolio page.",
        "Die Wochenveränderung wird mit den heutigen Mengen berechnet. Nur zu Bildungszwecken, keine Anlageberatung. Um diese E-Mails abzubestellen, schalten Sie auf der Seite Mein Portfolio die \"Wöchentliche E-Mail-Zusammenfassung\" aus."),
    "Portföy özeti: {value}": E("Portfolio summary: {value}", "Portfolio-Zusammenfassung: {value}"),
    "Portföy değeri: {value}. Bu hafta: {change}. Ayrıntılar: {url}": E(
        "Portfolio value: {value}. This week: {change}. Details: {url}",
        "Portfoliowert: {value}. Diese Woche: {change}. Details: {url}"),

    # --- Ekran iyileştirmeleri, grafikler, örnek portföy ----------------------------------------
    "**Etkin sınır**": E("**Efficient frontier**", "**Effiziente Grenze**"),
    "**Risk katkısı**": E("**Risk contribution**", "**Risikobeitrag**"),
    "24 portföy optimizasyon modelini aynı veriyle karşılaştırın: ağırlıklar, walk-forward backtest, etkin sınır ve otomatik yorumlar.": E(
        "Compare 24 portfolio optimisation models on the same data: weights, walk-forward backtest, efficient frontier and automatic commentary.",
        "Vergleichen Sie 24 Portfolio-Optimierungsmodelle mit denselben Daten: Gewichte, Walk-Forward-Backtest, effiziente Grenze und automatische Kommentare."),
    "BIST · TEFAS · ABD · altın · kripto": E("BIST · TEFAS · US · gold · crypto", "BIST · TEFAS · USA · Gold · Krypto"),
    "Enflasyona göre reel getiri": E("Inflation-adjusted returns", "Inflationsbereinigte Renditen"),
    "Etkin sınır": E("Efficient frontier", "Effiziente Grenze"),
    "Etkin sınır hesaplanamadı: {err}": E("Could not compute the efficient frontier: {err}",
                                          "Effiziente Grenze konnte nicht berechnet werden: {err}"),
    "Gri eğri, her risk düzeyinde ulaşılabilecek en yüksek getiri (Markowitz). Eğriye yakın modeller verimli; elmaslar tek tek varlıklar.": E(
        "The grey curve is the highest return achievable at each level of risk (Markowitz). Models close to it are efficient; diamonds are individual assets.",
        "Die graue Kurve ist die höchste erreichbare Rendite je Risikoniveau (Markowitz). Modelle nahe der Kurve sind effizient; Rauten sind einzelne Werte."),
    "Her modelde toplam riskin varlıklara dağılımı. Sermaye payından farklıdır: oynak bir varlık küçük payla bile riskin çoğunu taşıyabilir.": E(
        "How each model's total risk is split across assets. It differs from capital share: a volatile asset can carry most of the risk even with a small weight.",
        "Wie sich das Gesamtrisiko jedes Modells auf die Werte verteilt. Es unterscheidet sich vom Kapitalanteil: Ein volatiler Wert kann schon mit kleinem Gewicht den Großteil des Risikos tragen."),
    "Hiçbir varlığa bu orandan fazla pay verilmez. 100 = sınır yok. Sınırı destekleyen modellere uygulanır (eşit ağırlık, NCO, stacking ve diğer kütüphanelerin modelleri hariç).": E(
        "No asset gets more than this share. 100 = no limit. Applied to models that support it (not equal weight, NCO, stacking or the other libraries' models).",
        "Kein Wert erhält mehr als diesen Anteil. 100 = keine Grenze. Gilt für Modelle, die das unterstützen (nicht Gleichgewichtung, NCO, Stacking und Modelle der anderen Bibliotheken)."),
    "Kendi sunucunuza kurun": E("Self-host it", "Selbst hosten"),
    "Riskteki pay": E("Share of risk", "Anteil am Risiko"),
    "Sınırı desteklemeyen modeller: {models}.": E("Models without limit support: {models}.",
                                                  "Modelle ohne Unterstützung der Grenze: {models}."),
    "Tek varlık üst sınırı (%)": E("Max weight per asset (%)", "Max. Gewicht je Wert (%)"),
    "Tek varlık üst sınırı: {x}.": E("Max weight per asset: {x}.", "Max. Gewicht je Wert: {x}."),
    "Varlıklar": E("Assets", "Werte"),
    "Yıllık beklenen getiri": E("Expected annual return", "Erwartete Jahresrendite"),
    "Yıllık oynaklık": E("Annual volatility", "Jährliche Volatilität"),
    "Örnek portföy": E("Sample portfolio", "Beispielportfolio"),
    "Örnek portföy yüklendi: işlem geçmişi, temettü, dolar hesabı ve bir TEFAS fonu içeriyor. Kendi verilerinizi girmek için tabloları temizleyin.": E(
        "Sample portfolio loaded: it includes a transaction history, a dividend, a USD account and a TEFAS fund. Clear the tables to enter your own data.",
        "Beispielportfolio geladen: mit Transaktionshistorie, Dividende, USD-Konto und einem TEFAS-Fonds. Leeren Sie die Tabellen, um eigene Daten einzugeben."),
    "İşlem geçmişi ve temettü": E("Transactions & dividends", "Transaktionen & Dividenden"),
    "İşlem geçmişi, temettü ve nakit takibini gösteren hazır bir örnek yükler.": E(
        "Loads a ready-made example showing transactions, dividends and cash tracking.",
        "Lädt ein fertiges Beispiel mit Transaktionen, Dividenden und Cash-Verfolgung."),
    "🎯 Örnek portföyle dene": E("🎯 Try a sample portfolio", "🎯 Beispielportfolio ausprobieren"),
    "Varlık sayısı": E("Assets", "Werte"),
}

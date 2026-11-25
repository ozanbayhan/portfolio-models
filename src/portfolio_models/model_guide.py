"""Model rehberi: tarihçe, temel fikir, sonuçların nasıl okunacağı (TR / EN / DE).

Her model için:
    year, origin : kim, ne zaman (kaynak)
    idea         : ne yapar (kısa)
    read         : sonuçlar nasıl okunur
    strengths    : güçlü yanlar
    caution      : dikkat edilecekler
"""

from __future__ import annotations

from .i18n import get_lang

# --- Ortak model aileleri -------------------------------------------------------------------

GUIDE: dict[str, dict] = {
    "equal_weighted": {
        "year": "—",
        "origin": {
            "tr": "Çok eski bir halk kuralı (Talmud'da bile geçer). Akademik ününü DeMiguel, Garlappi ve Uppal'ın 2009 tarihli \"Optimal Versus Naive Diversification\" makalesi kazandırdı: 14 optimizasyon modelinin çoğu, gerçek veride 1/N'yi istikrarlı biçimde geçemedi.",
            "en": "A very old rule of thumb (it even appears in the Talmud). Its academic fame comes from DeMiguel, Garlappi and Uppal's 2009 paper \"Optimal Versus Naive Diversification\": most of 14 optimisation models failed to beat 1/N consistently out of sample.",
            "de": "Eine sehr alte Faustregel (sie findet sich sogar im Talmud). Akademisch bekannt wurde sie durch DeMiguel, Garlappi und Uppal (2009), \"Optimal Versus Naive Diversification\": Die meisten von 14 Optimierungsmodellen schlugen 1/N außerhalb der Stichprobe nicht verlässlich.",
        },
        "idea": {
            "tr": "Her varlığa eşit pay verir; hiçbir tahmin yapmaz.",
            "en": "Gives every asset the same share; makes no forecasts at all.",
            "de": "Gibt jedem Wert denselben Anteil; trifft keinerlei Prognosen.",
        },
        "read": {
            "tr": "Bir model değil, kıyas çizgisidir. Diğer modellerin backtest sonuçlarını buna göre okuyun: bir model eşit ağırlığı risk ayarlı (Sharpe) geçemiyorsa, ek karmaşıklık bu varlıklarda değer katmıyor demektir.",
            "en": "Treat it as the benchmark rather than a model. Read every other backtest against it: if a model cannot beat equal weight on a risk-adjusted basis (Sharpe), its extra complexity adds no value for these assets.",
            "de": "Eher Messlatte als Modell. Lesen Sie jedes andere Backtest-Ergebnis im Vergleich dazu: Schlägt ein Modell die Gleichgewichtung risikobereinigt (Sharpe) nicht, bringt seine zusätzliche Komplexität bei diesen Werten nichts.",
        },
        "strengths": {
            "tr": "Tahmin hatası yoktur, yorumu kolaydır, işlem maliyeti düşüktür.",
            "en": "No estimation error, easy to understand, low trading costs.",
            "de": "Kein Schätzfehler, leicht verständlich, geringe Handelskosten.",
        },
        "caution": {
            "tr": "Varlıkların riskini dikkate almaz: çok oynak bir varlık, sakin bir varlıkla aynı payı alır ve riskin çoğunu taşır.",
            "en": "Ignores risk: a very volatile asset gets the same share as a calm one and ends up carrying most of the risk.",
            "de": "Ignoriert das Risiko: Ein sehr volatiler Wert erhält denselben Anteil wie ein ruhiger und trägt am Ende den Großteil des Risikos.",
        },
    },
    "inverse_volatility": {
        "year": {"tr": "1990'lar", "en": "1990s", "de": "1990er"},
        "origin": {
            "tr": "Uygulamacıların yaygın kuralı; risk paritesinin korelasyonları yok sayan en basit hali olarak kabul edilir.",
            "en": "A long-standing practitioner rule; considered the simplest form of risk parity, one that ignores correlations.",
            "de": "Eine verbreitete Praktikerregel; gilt als einfachste Form der Risikoparität, die Korrelationen ignoriert.",
        },
        "idea": {
            "tr": "Her varlığın payı, oynaklığıyla ters orantılıdır: sakin varlık daha çok pay alır.",
            "en": "Each asset's share is inversely proportional to its volatility: calmer assets get more.",
            "de": "Der Anteil jedes Werts ist umgekehrt proportional zu seiner Volatilität: Ruhigere Werte erhalten mehr.",
        },
        "read": {
            "tr": "Ağırlık tablosunda en büyük pay en sakin varlıktadır. Eşit ağırlığa göre oynaklığın ne kadar düştüğüne bakın; getiride ne kadar vazgeçildiğiyle kıyaslayın.",
            "en": "The largest weight sits in the calmest asset. Check how much volatility drops versus equal weight and compare it with how much return you give up.",
            "de": "Das größte Gewicht liegt im ruhigsten Wert. Prüfen Sie, wie stark die Volatilität gegenüber der Gleichgewichtung sinkt, und vergleichen Sie das mit der aufgegebenen Rendite.",
        },
        "strengths": {
            "tr": "Basit ve kararlıdır; yalnızca oynaklık tahmin edilir, getiri tahmini gerekmez.",
            "en": "Simple and stable; only volatilities are estimated, no return forecasts needed.",
            "de": "Einfach und stabil; nur Volatilitäten werden geschätzt, keine Renditeprognosen nötig.",
        },
        "caution": {
            "tr": "Korelasyonları hesaba katmaz; birbirine çok benzeyen iki sakin varlık birlikte fazla ağırlık alabilir.",
            "en": "Ignores correlations; two very similar calm assets can jointly end up overweight.",
            "de": "Ignoriert Korrelationen; zwei sehr ähnliche ruhige Werte können gemeinsam übergewichtet werden.",
        },
    },
    "min_variance": {
        "year": "1952",
        "origin": {
            "tr": "Harry Markowitz, \"Portfolio Selection\" (Journal of Finance, 1952). Modern portföy teorisinin başlangıcı; Markowitz 1990'da Nobel aldı. Getiri tahmini gerektirmeyen bu uç noktası, Clarke, de Silva ve Thorley'in (2006) çalışmalarıyla yeniden popüler oldu.",
            "en": "Harry Markowitz, \"Portfolio Selection\" (Journal of Finance, 1952), the start of modern portfolio theory; Markowitz won the 1990 Nobel Prize. This end point, which needs no return forecasts, regained popularity through Clarke, de Silva and Thorley (2006).",
            "de": "Harry Markowitz, \"Portfolio Selection\" (Journal of Finance, 1952), der Beginn der modernen Portfoliotheorie; Markowitz erhielt 1990 den Nobelpreis. Dieser Randpunkt ohne Renditeprognosen wurde durch Clarke, de Silva und Thorley (2006) wieder populär.",
        },
        "idea": {
            "tr": "Varlıkların oynaklığını ve birbirleriyle ilişkisini (kovaryans) kullanarak toplam oynaklığı en aza indiren dağılımı bulur.",
            "en": "Uses volatilities and co-movements (covariance) to find the mix with the lowest total volatility.",
            "de": "Nutzt Volatilitäten und Gleichlauf (Kovarianz), um die Mischung mit der geringsten Gesamtvolatilität zu finden.",
        },
        "read": {
            "tr": "Ağırlıklar düşük oynaklıklı ve diğerleriyle az ilişkili varlıklarda toplanır. 'Etkin varlık sayısı' düşükse portföy birkaç varlığa yığılmış demektir. Backtest'te genellikle en sığ düşüşlerden birini, ama ortalama altı getiri verir.",
            "en": "Weights pile into low-volatility assets that move little with the others. A low 'effective number of assets' means the portfolio is concentrated. In backtests it usually shows one of the shallowest drawdowns but below-average returns.",
            "de": "Die Gewichte sammeln sich in schwankungsarmen, wenig korrelierten Werten. Eine niedrige 'effektive Anzahl von Werten' bedeutet Konzentration. Im Backtest zeigt es meist einen der geringsten Drawdowns, aber unterdurchschnittliche Rendite.",
        },
        "strengths": {
            "tr": "Getiri tahmini kullanmadığı için tahmin hatasına görece dayanıklıdır.",
            "en": "Relatively robust to estimation error because it uses no return forecasts.",
            "de": "Relativ robust gegen Schätzfehler, da keine Renditeprognosen verwendet werden.",
        },
        "caution": {
            "tr": "Az sayıda sakin varlığa yoğunlaşabilir; düşük risk, düşük getiri anlamına da gelebilir.",
            "en": "Can concentrate in a few calm assets; low risk may also mean low return.",
            "de": "Kann sich auf wenige ruhige Werte konzentrieren; geringes Risiko kann auch geringe Rendite bedeuten.",
        },
    },
    "max_sharpe": {
        "year": "1958 / 1966",
        "origin": {
            "tr": "James Tobin'in ayrışım teoremi (1958) ve William Sharpe'ın getiri/risk oranı (1966). Markowitz etkin sınırının 'teğet portföyü'dür. Sharpe 1990'da Nobel aldı.",
            "en": "James Tobin's separation theorem (1958) and William Sharpe's reward-to-variability ratio (1966). It is the 'tangency portfolio' of Markowitz's efficient frontier. Sharpe shared the 1990 Nobel Prize.",
            "de": "James Tobins Separationstheorem (1958) und William Sharpes Rendite-Risiko-Kennzahl (1966). Es ist das 'Tangentialportfolio' der effizienten Grenze nach Markowitz. Sharpe erhielt 1990 den Nobelpreis.",
        },
        "idea": {
            "tr": "Birim risk başına beklenen getiriyi (Sharpe oranı) en yükseğe çıkaran dağılımı bulur.",
            "en": "Finds the mix with the highest expected return per unit of risk (Sharpe ratio).",
            "de": "Findet die Mischung mit der höchsten erwarteten Rendite je Risikoeinheit (Sharpe-Ratio).",
        },
        "read": {
            "tr": "Geçmişte en çok kazandıran varlıklara yüklenir. Ağırlıkların dönem değiştikçe ne kadar oynadığına bakın (başlangıç tarihini değiştirip tekrar çalıştırın). Backtest'te iyi görünse bile bir sonraki dönemde tekrar etmeyebilir.",
            "en": "It loads up on the past winners. Check how much the weights move when you change the start date. Even if it looks great in a backtest, that may not repeat next period.",
            "de": "Setzt stark auf die bisherigen Gewinner. Prüfen Sie, wie sehr sich die Gewichte beim Ändern des Startdatums verschieben. Selbst ein starker Backtest muss sich in der nächsten Periode nicht wiederholen.",
        },
        "strengths": {
            "tr": "Teoride en verimli risk/getiri dengesidir; getiri tahminleriniz iyiyse en güçlü sonucu verir.",
            "en": "In theory the most efficient risk/return trade-off; strongest when your return forecasts are good.",
            "de": "Theoretisch das effizienteste Rendite-Risiko-Verhältnis; am stärksten, wenn Ihre Renditeprognosen gut sind.",
        },
        "caution": {
            "tr": "Geçmiş ortalama getirilere çok duyarlıdır; küçük veri değişiklikleri ağırlıkları sert değiştirir (Michaud bunu 1989'da 'hata maksimizasyonu' diye adlandırdı).",
            "en": "Highly sensitive to past average returns; small data changes swing the weights sharply (Michaud called it 'error maximisation' in 1989).",
            "de": "Sehr empfindlich gegenüber historischen Durchschnittsrenditen; kleine Datenänderungen verschieben die Gewichte stark (Michaud nannte das 1989 'Fehlermaximierung').",
        },
    },
    "max_sharpe_shrunk": {
        "year": "1986 / 2004",
        "origin": {
            "tr": "Ortalamalar için James-Stein tipi büzülme (Jorion, 1986) ve kovaryans için Ledoit ve Wolf'un büzülme tahmincisi (2004).",
            "en": "James-Stein-type shrinkage of means (Jorion, 1986) and Ledoit and Wolf's covariance shrinkage estimator (2004).",
            "de": "James-Stein-Schrumpfung der Mittelwerte (Jorion, 1986) und der Kovarianz-Schrumpfungsschätzer von Ledoit und Wolf (2004).",
        },
        "idea": {
            "tr": "Maks. Sharpe'ın, uç tahminleri ortalamaya doğru çeken daha temkinli sürümü.",
            "en": "A more cautious max-Sharpe that pulls extreme estimates towards the average.",
            "de": "Eine vorsichtigere Max-Sharpe-Variante, die extreme Schätzungen zum Durchschnitt zieht.",
        },
        "read": {
            "tr": "Klasik maks. Sharpe ile yan yana koyun: daha dengeli dağılıyorsa büzülme tahmin hatasını yumuşatıyor demektir. Backtest'te klasik sürüme yakın getiriyi daha az düşüşle veriyorsa tercih edilebilir.",
            "en": "Compare it side by side with classic max-Sharpe: a more balanced mix means shrinkage is dampening estimation error. If it delivers similar backtest returns with shallower drawdowns, prefer it.",
            "de": "Vergleichen Sie es mit dem klassischen Max-Sharpe: Eine ausgewogenere Mischung zeigt, dass die Schrumpfung Schätzfehler dämpft. Liefert es im Backtest ähnliche Renditen bei geringeren Drawdowns, ist es vorzuziehen.",
        },
        "strengths": {
            "tr": "Maks. Sharpe'tan daha kararlıdır; aşırı uyum riski daha düşüktür.",
            "en": "More stable than max-Sharpe; lower overfitting risk.",
            "de": "Stabiler als Max-Sharpe; geringeres Overfitting-Risiko.",
        },
        "caution": {
            "tr": "Yine de geçmiş getirilere dayanır; büzülme hatayı azaltır ama yok etmez.",
            "en": "Still relies on past returns; shrinkage reduces error but does not remove it.",
            "de": "Beruht weiterhin auf historischen Renditen; Schrumpfung verringert Fehler, beseitigt sie aber nicht.",
        },
    },
    "max_sortino": {
        "year": "1991 / 1994",
        "origin": {
            "tr": "Frank Sortino; Sortino ve van der Meer (1991) ile Sortino ve Price (1994) çalışmaları. Yatırımcının yalnızca aşağı yönlü dalgalanmadan rahatsız olduğu fikrine dayanır.",
            "en": "Frank Sortino; Sortino & van der Meer (1991) and Sortino & Price (1994). Built on the idea that investors only dislike downside swings.",
            "de": "Frank Sortino; Sortino & van der Meer (1991) sowie Sortino & Price (1994). Beruht auf der Idee, dass Anleger nur Abwärtsschwankungen stören.",
        },
        "idea": {
            "tr": "Yalnızca aşağı yönlü oynaklığı risk sayarak getiri/risk oranını en yükseğe çıkarır.",
            "en": "Maximises return per unit of downside volatility only.",
            "de": "Maximiert die Rendite je Einheit Abwärtsvolatilität.",
        },
        "read": {
            "tr": "Maks. Sharpe'a benzer ama yukarı yönlü sıçramaları cezalandırmaz; bu yüzden çarpık (ani yükselen) varlıklara daha çok pay verebilir. Backtest'te Sortino sütununa bakın.",
            "en": "Similar to max-Sharpe but does not penalise upside jumps, so it may favour assets with positive skew. Check the Sortino column in the backtest.",
            "de": "Ähnlich wie Max-Sharpe, bestraft aber keine Aufwärtssprünge und kann daher Werte mit positiver Schiefe bevorzugen. Achten Sie im Backtest auf die Sortino-Spalte.",
        },
        "strengths": {
            "tr": "Yatırımcının gerçekte korktuğu riske, yani kayba odaklanır.",
            "en": "Focuses on the risk investors actually fear: losses.",
            "de": "Konzentriert sich auf das Risiko, das Anleger wirklich fürchten: Verluste.",
        },
        "caution": {
            "tr": "Maks. Sharpe gibi geçmiş getirilere çok duyarlıdır.",
            "en": "Like max-Sharpe, highly sensitive to past returns.",
            "de": "Wie Max-Sharpe sehr empfindlich gegenüber historischen Renditen.",
        },
    },
    "min_cvar": {
        "year": "2000",
        "origin": {
            "tr": "R. Tyrrell Rockafellar ve Stanislav Uryasev, \"Optimization of Conditional Value-at-Risk\" (2000). CVaR'ı doğrusal programlamayla optimize etmeyi mümkün kıldılar; Basel III piyasa riski kuralları da benzer bir ölçüye (Expected Shortfall) geçti.",
            "en": "R. Tyrrell Rockafellar and Stanislav Uryasev, \"Optimization of Conditional Value-at-Risk\" (2000), which made CVaR optimisable with linear programming. Basel III market-risk rules later moved to the same idea (Expected Shortfall).",
            "de": "R. Tyrrell Rockafellar und Stanislav Uryasev, \"Optimization of Conditional Value-at-Risk\" (2000), machten CVaR per linearer Optimierung handhabbar. Die Basel-III-Marktrisikoregeln setzen inzwischen auf dieselbe Idee (Expected Shortfall).",
        },
        "idea": {
            "tr": "En kötü %5'lik günlerin ortalama kaybını (CVaR %95) en aza indirir.",
            "en": "Minimises the average loss on the worst 5% of days (CVaR 95%).",
            "de": "Minimiert den durchschnittlichen Verlust der schlechtesten 5 % der Tage (CVaR 95 %).",
        },
        "read": {
            "tr": "Backtest'te 'CVaR %95' sütunu düşük olmalıdır. Min. varyansla benzer ağırlıklar veriyorsa veride uç kayıplar sınırlıdır; belirgin farklıysa bazı varlıkların kuyruk riski oynaklığından fazladır.",
            "en": "Its 'CVaR 95%' in the backtest should be low. If its weights resemble min-variance, tail losses in the data are limited; if they differ a lot, some assets carry more tail risk than their volatility suggests.",
            "de": "Im Backtest sollte die Spalte 'CVaR 95 %' niedrig sein. Ähneln die Gewichte der Minimum-Varianz, sind Extremverluste begrenzt; weichen sie stark ab, tragen manche Werte mehr Extremrisiko, als ihre Volatilität vermuten lässt.",
        },
        "strengths": {
            "tr": "Kuyruk riskini, yani sert düşüş günlerini doğrudan hedefler.",
            "en": "Directly targets tail risk, the days of sharp falls.",
            "de": "Zielt direkt auf das Extremrisiko, also die Tage starker Einbrüche.",
        },
        "caution": {
            "tr": "Az sayıda kötü güne dayanır; kısa veride sonuç kararsız olabilir.",
            "en": "Relies on a few bad days; results can be unstable with short histories.",
            "de": "Stützt sich auf wenige schlechte Tage; bei kurzen Historien können die Ergebnisse instabil sein.",
        },
    },
    "min_cdar": {
        "year": "2003",
        "origin": {
            "tr": "Alexei Chekhlov, Stanislav Uryasev ve Michael Zabarankin, \"Drawdown Measure in Portfolio Optimization\" (2003/2005).",
            "en": "Alexei Chekhlov, Stanislav Uryasev and Michael Zabarankin, \"Drawdown Measure in Portfolio Optimization\" (2003/2005).",
            "de": "Alexei Chekhlov, Stanislav Uryasev und Michael Zabarankin, \"Drawdown Measure in Portfolio Optimization\" (2003/2005).",
        },
        "idea": {
            "tr": "Zirveden uzun süreli düşüşlerin (drawdown) en kötü kısmının ortalamasını en aza indirir.",
            "en": "Minimises the average of the worst drawdowns from previous peaks.",
            "de": "Minimiert den Durchschnitt der schlimmsten Drawdowns gegenüber früheren Höchstständen.",
        },
        "read": {
            "tr": "Backtest'te 'Maks. düşüş' ve düşüş grafiğine bakın: düşüşler daha sığ ve daha kısa sürmelidir. Toparlanma süresini önemseyen yatırımcılar için anlamlıdır.",
            "en": "Look at 'Max drawdown' and the drawdown chart: falls should be shallower and shorter. Most relevant for investors who care about recovery time.",
            "de": "Achten Sie auf 'Max. Drawdown' und das Drawdown-Diagramm: Rückgänge sollten flacher und kürzer sein. Besonders relevant, wenn Ihnen die Erholungszeit wichtig ist.",
        },
        "strengths": {
            "tr": "Yatırımcı psikolojisine en yakın risk ölçüsüdür: 'zirveden ne kadar ve ne kadar süre geride kaldım?'",
            "en": "The risk measure closest to investor psychology: 'how far, and for how long, am I below my peak?'",
            "de": "Das Risikomaß, das der Anlegerpsychologie am nächsten kommt: 'Wie weit und wie lange liege ich unter meinem Höchststand?'",
        },
        "caution": {
            "tr": "Geçmişteki düşüş dönemlerinin sırasına bağlıdır; gelecekte farklı bir kriz farklı varlıkları vurabilir.",
            "en": "Depends on the order of past drawdown episodes; a future crisis may hit different assets.",
            "de": "Hängt von der Abfolge früherer Rückgänge ab; eine künftige Krise kann andere Werte treffen.",
        },
    },
    "min_max_drawdown": {
        "year": "2003",
        "origin": {
            "tr": "Chekhlov, Uryasev ve Zabarankin'in düşüş ölçüleri ailesinin uç noktası.",
            "en": "The extreme case of Chekhlov, Uryasev and Zabarankin's drawdown-measure family.",
            "de": "Der Extremfall der Drawdown-Maße von Chekhlov, Uryasev und Zabarankin.",
        },
        "idea": {
            "tr": "Geçmişteki tek en derin düşüşü en aza indirir.",
            "en": "Minimises the single deepest historical drawdown.",
            "de": "Minimiert den einzelnen tiefsten historischen Drawdown.",
        },
        "read": {
            "tr": "Sonuç büyük ölçüde tek bir kriz dönemine göre şekillenir. Başlangıç tarihini o krizi içermeyecek şekilde değiştirip ağırlıkların nasıl değiştiğine bakın.",
            "en": "The result is shaped largely by one crisis episode. Move the start date so that crisis is excluded and see how much the weights change.",
            "de": "Das Ergebnis wird weitgehend von einer einzigen Krise bestimmt. Verschieben Sie das Startdatum so, dass diese Krise herausfällt, und prüfen Sie, wie stark sich die Gewichte ändern.",
        },
        "strengths": {
            "tr": "En kötü senaryoya karşı en doğrudan korumayı hedefler.",
            "en": "Targets the most direct protection against the worst scenario.",
            "de": "Zielt auf den direktesten Schutz gegen das schlimmste Szenario.",
        },
        "caution": {
            "tr": "Tek bir olaya göre ayarlandığı için en kararsız risk modellerinden biridir.",
            "en": "Because it is tuned to one event, it is among the least stable risk models.",
            "de": "Da es auf ein einzelnes Ereignis abgestimmt ist, gehört es zu den instabilsten Risikomodellen.",
        },
    },
    "max_diversification": {
        "year": "2008",
        "origin": {
            "tr": "Yves Choueifaty ve Yves Coignard, \"Toward Maximum Diversification\" (Journal of Portfolio Management, 2008); TOBAM tarafından ticari fonlarda kullanıldı.",
            "en": "Yves Choueifaty and Yves Coignard, \"Toward Maximum Diversification\" (Journal of Portfolio Management, 2008); used commercially by TOBAM.",
            "de": "Yves Choueifaty und Yves Coignard, \"Toward Maximum Diversification\" (Journal of Portfolio Management, 2008); kommerziell von TOBAM eingesetzt.",
        },
        "idea": {
            "tr": "Çeşitlendirme oranını (varlık risklerinin ağırlıklı toplamı / portföy riski) en yükseğe çıkarır.",
            "en": "Maximises the diversification ratio (weighted sum of asset risks divided by portfolio risk).",
            "de": "Maximiert die Diversifikationsquote (gewichtete Summe der Einzelrisiken geteilt durch das Portfoliorisiko).",
        },
        "read": {
            "tr": "Birbirine en az benzeyen varlıklara pay verir. Korelasyon ısı haritasında (Veri sekmesi) düşük korelasyonlu varlıkların bu modelde öne çıktığını görmelisiniz.",
            "en": "It favours the least similar assets. In the correlation heat map (Data tab) the low-correlation assets should be the ones it overweights.",
            "de": "Bevorzugt die am wenigsten ähnlichen Werte. In der Korrelations-Heatmap (Reiter Daten) sollten die niedrig korrelierten Werte übergewichtet sein.",
        },
        "strengths": {
            "tr": "Getiri tahmini kullanmaz; gerçek çeşitlendirmeyi doğrudan hedefler.",
            "en": "Uses no return forecasts; targets genuine diversification directly.",
            "de": "Verwendet keine Renditeprognosen; zielt direkt auf echte Diversifikation.",
        },
        "caution": {
            "tr": "Korelasyonlar kriz anlarında artar; çeşitlendirme en çok gerektiğinde azalabilir.",
            "en": "Correlations rise in crises, so diversification may shrink just when you need it most.",
            "de": "Korrelationen steigen in Krisen, sodass die Diversifikation gerade dann schrumpfen kann, wenn sie am meisten gebraucht wird.",
        },
    },
    "dro_cvar": {
        "year": "2018",
        "origin": {
            "tr": "Peyman Mohajerin Esfahani ve Daniel Kuhn, Wasserstein mesafesiyle dağılımsal olarak dayanıklı optimizasyon (Mathematical Programming, 2018).",
            "en": "Peyman Mohajerin Esfahani and Daniel Kuhn, distributionally robust optimisation with the Wasserstein metric (Mathematical Programming, 2018).",
            "de": "Peyman Mohajerin Esfahani und Daniel Kuhn, verteilungsrobuste Optimierung mit der Wasserstein-Metrik (Mathematical Programming, 2018).",
        },
        "idea": {
            "tr": "Geçmiş veriye 'yakın' tüm olası dağılımlar içinde en kötüsüne göre CVaR'ı en aza indirir.",
            "en": "Minimises CVaR under the worst of all distributions 'close' to the historical data.",
            "de": "Minimiert den CVaR unter der ungünstigsten aller Verteilungen, die den historischen Daten 'nahe' sind.",
        },
        "read": {
            "tr": "Min. CVaR ile karşılaştırın: daha dengeli ağırlıklar, modelin geçmişe aşırı güvenmediğini gösterir. Belirsizlik payı (yarıçap) büyüdükçe eşit ağırlığa yaklaşır.",
            "en": "Compare it with min-CVaR: more balanced weights show the model is not over-trusting history. As the uncertainty radius grows it approaches equal weight.",
            "de": "Vergleichen Sie es mit Min-CVaR: Ausgewogenere Gewichte zeigen, dass das Modell der Historie nicht übermäßig vertraut. Mit wachsendem Unsicherheitsradius nähert es sich der Gleichgewichtung.",
        },
        "strengths": {
            "tr": "Verinin geleceği tam yansıtmadığı varsayımına dayanır; sürprizlere karşı temkinlidir.",
            "en": "Assumes the data will not perfectly reflect the future; cautious against surprises.",
            "de": "Geht davon aus, dass die Daten die Zukunft nicht exakt widerspiegeln; vorsichtig gegenüber Überraschungen.",
        },
        "caution": {
            "tr": "Hesaplaması ağırdır; çok temkinli olup getiriden fazla vazgeçebilir.",
            "en": "Computationally heavy; may be overly cautious and give up too much return.",
            "de": "Rechenintensiv; kann übervorsichtig sein und zu viel Rendite aufgeben.",
        },
    },
    "risk_parity": {
        "year": "1996 / 2005",
        "origin": {
            "tr": "Bridgewater'ın 'All Weather' fonu (Ray Dalio, 1996) ve terimi kullanan Edward Qian (PanAgora, 2005). Maillard, Roncalli ve Teïletche (2010) matematiksel özelliklerini ortaya koydu.",
            "en": "Bridgewater's All Weather fund (Ray Dalio, 1996) and Edward Qian, who coined the term (PanAgora, 2005). Maillard, Roncalli and Teïletche (2010) formalised its properties.",
            "de": "Bridgewaters All-Weather-Fonds (Ray Dalio, 1996) und Edward Qian, der den Begriff prägte (PanAgora, 2005). Maillard, Roncalli und Teïletche (2010) formalisierten die Eigenschaften.",
        },
        "idea": {
            "tr": "Sermayeyi değil riski eşit böler: her varlığın toplam riske katkısı aynıdır.",
            "en": "Splits risk, not capital, equally: every asset contributes the same to total risk.",
            "de": "Teilt das Risiko statt des Kapitals gleich auf: Jeder Wert trägt gleich viel zum Gesamtrisiko bei.",
        },
        "read": {
            "tr": "Ağırlıklar eşit değildir ama yorumlardaki 'Risk kaynağı' satırında tek bir varlığın baskın olmaması gerekir. Sakin varlıklar daha çok sermaye alır.",
            "en": "Weights are unequal, yet the 'Risk source' line in the comments should show no single dominant asset. Calm assets receive more capital.",
            "de": "Die Gewichte sind ungleich, doch die Zeile 'Risikoquelle' in den Kommentaren sollte keinen dominanten Einzelwert zeigen. Ruhige Werte erhalten mehr Kapital.",
        },
        "strengths": {
            "tr": "Getiri tahmini gerekmez; kriz dönemlerinde genellikle dengeli kalır.",
            "en": "Needs no return forecasts; usually stays balanced through crises.",
            "de": "Benötigt keine Renditeprognosen; bleibt in Krisen meist ausgewogen.",
        },
        "caution": {
            "tr": "Sakin varlıklara çok sermaye ayırır; bu varlıklar birlikte düşerse etkisi büyük olur.",
            "en": "Allocates a lot of capital to calm assets; if they fall together the impact is large.",
            "de": "Weist ruhigen Werten viel Kapital zu; fallen diese gemeinsam, ist die Wirkung groß.",
        },
    },
    "risk_parity_cvar": {
        "year": {"tr": "2010'lar", "en": "2010s", "de": "2010er"},
        "origin": {
            "tr": "Risk paritesinin kuyruk riski ölçüleriyle genellemesi (ör. Boudt, Carl ve Peterson, 2013).",
            "en": "A generalisation of risk parity to tail-risk measures (e.g. Boudt, Carl and Peterson, 2013).",
            "de": "Eine Verallgemeinerung der Risikoparität auf Extremrisikomaße (z. B. Boudt, Carl und Peterson, 2013).",
        },
        "idea": {
            "tr": "Her varlığın kuyruk riskine (CVaR) katkısını eşitler.",
            "en": "Equalises each asset's contribution to tail risk (CVaR).",
            "de": "Gleicht den Beitrag jedes Werts zum Extremrisiko (CVaR) an.",
        },
        "read": {
            "tr": "Varyans tabanlı risk paritesinden farkına bakın: ani ve sert düşüşleri olan varlıkların payı burada daha düşük olmalıdır.",
            "en": "Look at the difference from variance-based risk parity: assets with sudden sharp falls should get less here.",
            "de": "Achten Sie auf den Unterschied zur varianzbasierten Risikoparität: Werte mit plötzlichen starken Einbrüchen sollten hier weniger erhalten.",
        },
        "strengths": {
            "tr": "Normal dağılım varsayımı yapmaz; sert düşüşleri doğrudan hesaba katar.",
            "en": "Makes no normal-distribution assumption; accounts for sharp falls directly.",
            "de": "Keine Normalverteilungsannahme; berücksichtigt starke Einbrüche direkt.",
        },
        "caution": {
            "tr": "Kuyruk tahmini az sayıda gözleme dayanır; kısa veride kararsız olabilir.",
            "en": "Tail estimates rest on few observations; can be unstable with short data.",
            "de": "Extremwertschätzungen beruhen auf wenigen Beobachtungen; bei kurzen Daten möglicherweise instabil.",
        },
    },
    "hrp": {
        "year": "2016",
        "origin": {
            "tr": "Marcos López de Prado, \"Building Diversified Portfolios that Outperform Out of Sample\" (Journal of Portfolio Management, 2016). Makine öğrenmesindeki kümeleme yöntemlerini portföye taşıdı.",
            "en": "Marcos López de Prado, \"Building Diversified Portfolios that Outperform Out of Sample\" (Journal of Portfolio Management, 2016), bringing machine-learning clustering to portfolio construction.",
            "de": "Marcos López de Prado, \"Building Diversified Portfolios that Outperform Out of Sample\" (Journal of Portfolio Management, 2016); überträgt Clustering-Verfahren des maschinellen Lernens auf die Portfoliokonstruktion.",
        },
        "idea": {
            "tr": "Varlıkları benzerliklerine göre bir ağaçta kümeler, sonra riski bu ağacın dallarına yukarıdan aşağı böler.",
            "en": "Clusters assets into a tree by similarity, then splits risk top-down along the branches.",
            "de": "Gruppiert Werte nach Ähnlichkeit in einem Baum und teilt das Risiko dann von oben nach unten entlang der Äste auf.",
        },
        "read": {
            "tr": "Birbirine benzeyen varlıklar (ör. aynı sektördeki hisseler) toplu olarak pay paylaşır. Ağırlıklar dönemler arasında görece kararlı olmalıdır; değişkenliği maks. Sharpe ile kıyaslayın.",
            "en": "Similar assets (e.g. stocks in the same sector) share their weight as a group. Weights should be fairly stable across periods; compare their variability with max-Sharpe.",
            "de": "Ähnliche Werte (z. B. Aktien derselben Branche) teilen sich ihr Gewicht als Gruppe. Die Gewichte sollten über Perioden recht stabil sein; vergleichen Sie die Schwankung mit Max-Sharpe.",
        },
        "strengths": {
            "tr": "Kovaryans matrisini tersine çevirmez; tahmin hatalarına ve çok sayıda varlığa karşı dayanıklıdır.",
            "en": "Never inverts the covariance matrix; robust to estimation error and to many assets.",
            "de": "Invertiert die Kovarianzmatrix nicht; robust gegen Schätzfehler und viele Werte.",
        },
        "caution": {
            "tr": "Varlıkların oynaklıkları çok farklıysa sakin varlığa yoğunlaşabilir; kümeleme yöntemi sonucu etkiler.",
            "en": "Can concentrate in the calm asset when volatilities differ a lot; the clustering method affects the result.",
            "de": "Kann sich bei stark unterschiedlichen Volatilitäten auf den ruhigen Wert konzentrieren; das Clustering-Verfahren beeinflusst das Ergebnis.",
        },
    },
    "hrp_cdar": {
        "year": "2016+",
        "origin": {
            "tr": "HRP'nin varyans yerine düşüş riskiyle (CDaR) çalışan sürümü; skfolio ve Riskfolio-Lib'de genelleştirildi.",
            "en": "HRP with drawdown risk (CDaR) instead of variance, generalised in skfolio and Riskfolio-Lib.",
            "de": "HRP mit Drawdown-Risiko (CDaR) statt Varianz, verallgemeinert in skfolio und Riskfolio-Lib.",
        },
        "idea": {
            "tr": "HRP ağacını kullanır ama riski kümeler arasında düşüş riskine göre böler.",
            "en": "Uses the HRP tree but splits risk by drawdown risk.",
            "de": "Nutzt den HRP-Baum, teilt das Risiko aber nach Drawdown-Risiko auf.",
        },
        "read": {
            "tr": "Klasik HRP ile karşılaştırın: uzun süre zirvenin altında kalan varlıkların payı burada azalmalıdır.",
            "en": "Compare with classic HRP: assets that stay below their peaks for long should get less here.",
            "de": "Vergleichen Sie mit dem klassischen HRP: Werte, die lange unter ihrem Höchststand bleiben, sollten hier weniger erhalten.",
        },
        "strengths": {
            "tr": "HRP'nin dayanıklılığını düşüş odaklı risk ölçüsüyle birleştirir.",
            "en": "Combines HRP's robustness with a drawdown-focused risk measure.",
            "de": "Verbindet die Robustheit von HRP mit einem drawdown-orientierten Risikomaß.",
        },
        "caution": {
            "tr": "Düşüş ölçüleri geçmişteki kriz sırasına bağlıdır.",
            "en": "Drawdown measures depend on the order of past crises.",
            "de": "Drawdown-Maße hängen von der Reihenfolge früherer Krisen ab.",
        },
    },
    "herc": {
        "year": "2017",
        "origin": {
            "tr": "Thomas Raffinot, \"Hierarchical Clustering-Based Asset Allocation\" (2017) ve HERC (2018).",
            "en": "Thomas Raffinot, \"Hierarchical Clustering-Based Asset Allocation\" (2017) and HERC (2018).",
            "de": "Thomas Raffinot, \"Hierarchical Clustering-Based Asset Allocation\" (2017) und HERC (2018).",
        },
        "idea": {
            "tr": "Önce kümeleri belirler, her kümeye eşit risk payı verir, sonra küme içinde riski böler.",
            "en": "Identifies clusters first, gives each cluster an equal share of risk, then splits risk within clusters.",
            "de": "Bestimmt zuerst Cluster, gibt jedem Cluster denselben Risikoanteil und teilt das Risiko dann innerhalb der Cluster auf.",
        },
        "read": {
            "tr": "Küme sayısı sonucu belirler; az varlıkla tek bir varlık kendi kümesinde kalıp büyük pay alabilir. Ağırlık grafiğinde bunu kontrol edin.",
            "en": "The number of clusters drives the result; with few assets a lone asset in its own cluster can get a large share. Check this in the weight chart.",
            "de": "Die Anzahl der Cluster bestimmt das Ergebnis; bei wenigen Werten kann ein einzelner Wert in einem eigenen Cluster einen großen Anteil bekommen. Prüfen Sie das im Gewichtsdiagramm.",
        },
        "strengths": {
            "tr": "HRP'deki 'ağacı ikiye bölme' sorununu, gerçek küme yapısını kullanarak düzeltir.",
            "en": "Fixes HRP's 'split the tree in half' issue by using the actual cluster structure.",
            "de": "Behebt die 'Baum halbieren'-Schwäche von HRP, indem es die tatsächliche Clusterstruktur nutzt.",
        },
        "caution": {
            "tr": "Az varlıkla sonuçları sert değişebilir.",
            "en": "Results can swing sharply with few assets.",
            "de": "Bei wenigen Werten können die Ergebnisse stark schwanken.",
        },
    },
    "nco": {
        "year": "2019",
        "origin": {
            "tr": "Marcos López de Prado, \"A Robust Estimator of the Efficient Frontier\" (2019) ve \"Machine Learning for Asset Managers\" (2020).",
            "en": "Marcos López de Prado, \"A Robust Estimator of the Efficient Frontier\" (2019) and \"Machine Learning for Asset Managers\" (2020).",
            "de": "Marcos López de Prado, \"A Robust Estimator of the Efficient Frontier\" (2019) und \"Machine Learning for Asset Managers\" (2020).",
        },
        "idea": {
            "tr": "Önce her küme içinde, sonra kümeler arasında optimizasyon yapar.",
            "en": "Optimises first within each cluster, then across clusters.",
            "de": "Optimiert zuerst innerhalb jedes Clusters, dann zwischen den Clustern.",
        },
        "read": {
            "tr": "Çok sayıda varlıkta (20+) avantaj sağlar. Bu uygulamadaki gibi az varlıkta min. varyansa benzer sonuç verirse şaşırmayın.",
            "en": "Shines with many assets (20+). With few assets, as here, don't be surprised if it resembles min-variance.",
            "de": "Spielt seine Stärken bei vielen Werten (20+) aus. Bei wenigen Werten, wie hier, ähnelt es oft der Minimum-Varianz.",
        },
        "strengths": {
            "tr": "Kovaryans matrisindeki gürültünün optimizasyonu bozmasını sınırlar.",
            "en": "Limits how much noise in the covariance matrix can distort the optimisation.",
            "de": "Begrenzt, wie stark Rauschen in der Kovarianzmatrix die Optimierung verzerrt.",
        },
        "caution": {
            "tr": "Az varlıkta ek fayda sınırlıdır; kümeleme kararsızsa sonuç da kararsız olur.",
            "en": "Little extra benefit with few assets; unstable clustering means unstable results.",
            "de": "Wenig Zusatznutzen bei wenigen Werten; instabiles Clustering führt zu instabilen Ergebnissen.",
        },
    },
    "schur": {
        "year": "2024",
        "origin": {
            "tr": "Peter Cotton, \"Schur Complementary Allocation\" (2024). HRP ile Markowitz arasında köprü kurar.",
            "en": "Peter Cotton, \"Schur Complementary Allocation\" (2024), bridging HRP and Markowitz.",
            "de": "Peter Cotton, \"Schur Complementary Allocation\" (2024); schlägt eine Brücke zwischen HRP und Markowitz.",
        },
        "idea": {
            "tr": "HRP'nin ağacını kullanır ama kümeler arasındaki korelasyon bilgisini atmadan (Schur tamamlayıcısıyla) dağıtım yapar.",
            "en": "Uses HRP's tree but keeps cross-cluster correlation information (via the Schur complement) when allocating.",
            "de": "Nutzt den HRP-Baum, behält aber Korrelationsinformationen zwischen Clustern (über das Schur-Komplement) bei der Allokation bei.",
        },
        "read": {
            "tr": "Ağırlıkları genellikle HRP ile min. varyans arasında bir yere düşer; ikisiyle yan yana karşılaştırın.",
            "en": "Its weights usually land between HRP and min-variance; compare it side by side with both.",
            "de": "Die Gewichte liegen meist zwischen HRP und Minimum-Varianz; vergleichen Sie es mit beiden.",
        },
        "strengths": {
            "tr": "HRP'nin dayanıklılığını korurken korelasyon bilgisini daha iyi kullanır.",
            "en": "Keeps HRP's robustness while using correlation information better.",
            "de": "Bewahrt die Robustheit von HRP und nutzt Korrelationsinformationen besser.",
        },
        "caution": {
            "tr": "Yeni bir yöntemdir; uzun dönemli bağımsız sınamaları sınırlıdır.",
            "en": "A new method; long-term independent testing is limited.",
            "de": "Ein neues Verfahren; langfristige unabhängige Tests sind begrenzt.",
        },
    },
    "stacking": {
        "year": "1992",
        "origin": {
            "tr": "David Wolpert, \"Stacked Generalization\" (1992); makine öğrenmesinden portföye skfolio tarafından uyarlandı.",
            "en": "David Wolpert, \"Stacked Generalization\" (1992); adapted from machine learning to portfolios by skfolio.",
            "de": "David Wolpert, \"Stacked Generalization\" (1992); von skfolio aus dem maschinellen Lernen auf Portfolios übertragen.",
        },
        "idea": {
            "tr": "Birkaç modelin (HRP, min. varyans, risk paritesi, maks. çeşitlendirme) portföylerini 'varlık' gibi kabul edip aralarında yeniden optimizasyon yapar.",
            "en": "Treats the portfolios of several models (HRP, min-variance, risk parity, max diversification) as 'assets' and optimises across them.",
            "de": "Behandelt die Portfolios mehrerer Modelle (HRP, Minimum-Varianz, Risikoparität, maximale Diversifikation) als 'Werte' und optimiert zwischen ihnen.",
        },
        "read": {
            "tr": "Sonucu bileşen modellerin bir karışımıdır. Backtest'te bileşenlerin ortalamasından iyi değilse ek karmaşıklık değmiyordur.",
            "en": "Its result is a blend of the component models. If it doesn't beat their average in the backtest, the extra complexity isn't worth it.",
            "de": "Das Ergebnis ist eine Mischung der Einzelmodelle. Schlägt es im Backtest deren Durchschnitt nicht, lohnt sich die zusätzliche Komplexität nicht.",
        },
        "strengths": {
            "tr": "Tek modelin hatalarını dengelemeyi hedefler.",
            "en": "Aims to balance out the mistakes of any single model.",
            "de": "Soll die Fehler einzelner Modelle ausgleichen.",
        },
        "caution": {
            "tr": "Bileşenlerine bağlıdır ve hesaplaması daha yavaştır.",
            "en": "Depends on its components and is slower to compute.",
            "de": "Hängt von seinen Komponenten ab und ist rechenaufwendiger.",
        },
    },
    "riskfolio_hrp": {
        "year": "2016",
        "origin": {
            "tr": "López de Prado'nun HRP'sinin Riskfolio-Lib (Dany Cajas) uygulaması; 'ward' bağlantı yöntemiyle.",
            "en": "Riskfolio-Lib's (Dany Cajas) implementation of López de Prado's HRP, using Ward linkage.",
            "de": "Die Riskfolio-Lib-Implementierung (Dany Cajas) von López de Prados HRP mit Ward-Verknüpfung.",
        },
        "idea": {
            "tr": "HRP ile aynı fikir; farklı bir kümeleme (bağlantı) yöntemi kullanır.",
            "en": "Same idea as HRP with a different clustering (linkage) method.",
            "de": "Gleiche Idee wie HRP mit einem anderen Clustering-(Verknüpfungs-)Verfahren.",
        },
        "read": {
            "tr": "skfolio'daki HRP ile karşılaştırın; büyük fark, sonucun kümeleme yöntemine duyarlı olduğunu gösterir.",
            "en": "Compare with skfolio's HRP; a large difference shows the result is sensitive to the clustering method.",
            "de": "Vergleichen Sie mit dem HRP von skfolio; ein großer Unterschied zeigt, dass das Ergebnis vom Clustering-Verfahren abhängt.",
        },
        "strengths": {
            "tr": "Ward yöntemi daha dengeli, yoğun kümeler oluşturur.",
            "en": "Ward linkage tends to build more balanced, compact clusters.",
            "de": "Die Ward-Verknüpfung bildet tendenziell ausgewogenere, kompaktere Cluster.",
        },
        "caution": {
            "tr": "HRP'nin sınırlamaları burada da geçerlidir.",
            "en": "HRP's limitations apply here as well.",
            "de": "Die Grenzen von HRP gelten auch hier.",
        },
    },
    "riskfolio_max_sharpe_cvar": {
        "year": "2000+",
        "origin": {
            "tr": "Rockafellar-Uryasev CVaR'ının getiri/risk oranında kullanımı; Riskfolio-Lib uygulaması.",
            "en": "Rockafellar-Uryasev CVaR used in a return/risk ratio; Riskfolio-Lib implementation.",
            "de": "CVaR nach Rockafellar-Uryasev in einer Rendite-Risiko-Kennzahl; Implementierung in Riskfolio-Lib.",
        },
        "idea": {
            "tr": "Beklenen getiri / CVaR oranını en yükseğe çıkarır.",
            "en": "Maximises expected return divided by CVaR.",
            "de": "Maximiert die erwartete Rendite geteilt durch den CVaR.",
        },
        "read": {
            "tr": "Maks. Sharpe'tan farkı, oynaklık yerine sert düşüşleri cezalandırmasıdır. Ağırlıklar maks. Sharpe'a benziyorsa veride kuyruk riski belirgin değildir.",
            "en": "Unlike max-Sharpe it penalises sharp falls rather than volatility. If its weights resemble max-Sharpe, tail risk in the data is not pronounced.",
            "de": "Anders als Max-Sharpe bestraft es starke Einbrüche statt Volatilität. Ähneln die Gewichte Max-Sharpe, ist das Extremrisiko in den Daten gering.",
        },
        "strengths": {
            "tr": "Getiri arayışını kuyruk riski kontrolüyle birleştirir.",
            "en": "Combines return seeking with tail-risk control.",
            "de": "Verbindet Renditestreben mit Kontrolle des Extremrisikos.",
        },
        "caution": {
            "tr": "Geçmiş getirilere duyarlıdır.",
            "en": "Sensitive to past returns.",
            "de": "Empfindlich gegenüber historischen Renditen.",
        },
    },
    "riskfolio_min_cdar": {
        "year": "2003",
        "origin": {
            "tr": "Chekhlov-Uryasev-Zabarankin CDaR'ının Riskfolio-Lib uygulaması.",
            "en": "Riskfolio-Lib implementation of Chekhlov-Uryasev-Zabarankin CDaR.",
            "de": "Riskfolio-Lib-Implementierung des CDaR nach Chekhlov-Uryasev-Zabarankin.",
        },
        "idea": {
            "tr": "Min. CDaR ile aynı amaç; farklı bir kütüphane ve çözücü ayarı.",
            "en": "Same goal as min-CDaR with a different library and solver settings.",
            "de": "Gleiches Ziel wie Min-CDaR mit anderer Bibliothek und anderen Solver-Einstellungen.",
        },
        "read": {
            "tr": "skfolio'daki min. CDaR ile neredeyse aynı çıkmalıdır; fark varsa çözücü hassasiyetinden kaynaklanır.",
            "en": "Should almost match skfolio's min-CDaR; any difference comes from solver precision.",
            "de": "Sollte fast mit Min-CDaR aus skfolio übereinstimmen; Abweichungen stammen aus der Solver-Genauigkeit.",
        },
        "strengths": {
            "tr": "İki bağımsız uygulamayla sonucu çapraz doğrulamayı sağlar.",
            "en": "Lets you cross-check the result with two independent implementations.",
            "de": "Ermöglicht die Gegenprüfung mit zwei unabhängigen Implementierungen.",
        },
        "caution": {
            "tr": "Düşüş ölçülerinin sınırlamaları geçerlidir.",
            "en": "The usual drawdown-measure limitations apply.",
            "de": "Es gelten die üblichen Grenzen von Drawdown-Maßen.",
        },
    },
    "pypfopt_max_sharpe": {
        "year": "1966 / 2004",
        "origin": {
            "tr": "Sharpe oranı ve Ledoit-Wolf kovaryansı; PyPortfolioOpt (Robert Martin) uygulaması.",
            "en": "Sharpe ratio with Ledoit-Wolf covariance; PyPortfolioOpt (Robert Martin) implementation.",
            "de": "Sharpe-Ratio mit Ledoit-Wolf-Kovarianz; Implementierung in PyPortfolioOpt (Robert Martin).",
        },
        "idea": {
            "tr": "Kovaryansı büzerek maks. Sharpe portföyünü bulur.",
            "en": "Finds the max-Sharpe portfolio using a shrunk covariance.",
            "de": "Findet das Max-Sharpe-Portfolio mit geschrumpfter Kovarianz.",
        },
        "read": {
            "tr": "skfolio'nun maks. Sharpe'ıyla karşılaştırın; büzülme kovaryansı yumuşattığı için ağırlıklar biraz daha dengeli olabilir.",
            "en": "Compare with skfolio's max-Sharpe; shrinkage smooths the covariance so weights may be slightly more balanced.",
            "de": "Vergleichen Sie mit Max-Sharpe aus skfolio; die Schrumpfung glättet die Kovarianz, die Gewichte können etwas ausgewogener sein.",
        },
        "strengths": {
            "tr": "Klasik maks. Sharpe'tan biraz daha kararlıdır.",
            "en": "Slightly more stable than classic max-Sharpe.",
            "de": "Etwas stabiler als das klassische Max-Sharpe.",
        },
        "caution": {
            "tr": "Beklenen getiriler yine geçmiş ortalamalardır.",
            "en": "Expected returns are still historical averages.",
            "de": "Die erwarteten Renditen sind weiterhin historische Durchschnitte.",
        },
    },
    "pypfopt_cla_min_vol": {
        "year": "1956",
        "origin": {
            "tr": "Markowitz'in Critical Line Algorithm'i (1956); Bailey ve López de Prado'nun açık kaynak uygulaması (2013).",
            "en": "Markowitz's Critical Line Algorithm (1956); open-source implementation by Bailey and López de Prado (2013).",
            "de": "Markowitz' Critical Line Algorithm (1956); Open-Source-Implementierung von Bailey und López de Prado (2013).",
        },
        "idea": {
            "tr": "Etkin sınırın tamamını tam olarak çözen özel bir algoritmayla minimum oynaklık portföyünü bulur.",
            "en": "Finds the minimum-volatility portfolio with a dedicated algorithm that traces the whole efficient frontier exactly.",
            "de": "Findet das Minimum-Volatilitäts-Portfolio mit einem speziellen Algorithmus, der die gesamte effiziente Grenze exakt berechnet.",
        },
        "read": {
            "tr": "Min. varyansla neredeyse aynı çıkmalıdır; iki yöntemin sonucu doğrulaması olarak okuyun.",
            "en": "Should nearly match min-variance; read it as a cross-check of that result.",
            "de": "Sollte fast mit der Minimum-Varianz übereinstimmen; lesen Sie es als Gegenprobe.",
        },
        "strengths": {
            "tr": "Genel amaçlı çözücülere göre kesin ve hızlıdır.",
            "en": "Exact and fast compared with general-purpose solvers.",
            "de": "Exakt und schnell im Vergleich zu Allzweck-Solvern.",
        },
        "caution": {
            "tr": "Min. varyansın sınırlamaları geçerlidir.",
            "en": "Min-variance limitations apply.",
            "de": "Es gelten die Grenzen der Minimum-Varianz.",
        },
    },
    "black_litterman": {
        "year": "1990 / 1992",
        "origin": {
            "tr": "Fischer Black ve Robert Litterman, Goldman Sachs (1990; Financial Analysts Journal, 1992). Markowitz'in uç ağırlık sorununa yanıt olarak geliştirildi.",
            "en": "Fischer Black and Robert Litterman, Goldman Sachs (1990; Financial Analysts Journal, 1992), developed in response to Markowitz's extreme-weight problem.",
            "de": "Fischer Black und Robert Litterman, Goldman Sachs (1990; Financial Analysts Journal, 1992), als Antwort auf das Problem extremer Gewichte bei Markowitz.",
        },
        "idea": {
            "tr": "Piyasanın 'nötr' beklentisini sizin görüşlerinizle, görüşe olan güveninize göre harmanlar.",
            "en": "Blends a 'neutral' market expectation with your views, weighted by your confidence in them.",
            "de": "Mischt eine 'neutrale' Markterwartung mit Ihren Einschätzungen, gewichtet nach Ihrem Vertrauen in diese.",
        },
        "read": {
            "tr": "Görüşsüz ve görüşlü ağırlıkları karşılaştırın: değişim, görüşlerinizin portföye etkisidir. Güveni (tau) artırdıkça görüşleriniz daha ağır basar.",
            "en": "Compare the weights with and without views: the change is the impact of your views. Raising confidence (tau) gives your views more weight.",
            "de": "Vergleichen Sie die Gewichte mit und ohne Einschätzungen: Die Veränderung ist deren Wirkung. Ein höheres Vertrauen (Tau) gibt Ihren Einschätzungen mehr Gewicht.",
        },
        "strengths": {
            "tr": "Kişisel görüşleri tutarlı ve ölçülü biçimde portföye yansıtır.",
            "en": "Brings personal views into the portfolio consistently and in moderation.",
            "de": "Bringt persönliche Einschätzungen konsistent und maßvoll ins Portfolio.",
        },
        "caution": {
            "tr": "Sonuç görüşlerin kalitesine bağlıdır; yanlış görüş, ölçülü de olsa yanlış yöne iter.",
            "en": "Only as good as your views; a wrong view, even in moderation, still pushes in the wrong direction.",
            "de": "Nur so gut wie Ihre Einschätzungen; eine falsche Einschätzung führt, wenn auch maßvoll, in die falsche Richtung.",
        },
    },
}

# --- Metrik sözlüğü -----------------------------------------------------------------------

METRICS: list[tuple[dict, dict]] = [
    ({"tr": "Yıllık getiri", "en": "Annual return", "de": "Jährliche Rendite"},
     {"tr": "Günlük ortalama getirinin yıla ölçeklenmiş hali. Tek başına anlamı sınırlıdır; hangi riskle elde edildiğine bakın.",
      "en": "Average daily return scaled to a year. On its own it says little; always look at the risk taken to earn it.",
      "de": "Durchschnittliche Tagesrendite auf ein Jahr hochgerechnet. Allein wenig aussagekräftig; achten Sie immer auf das eingegangene Risiko."}),
    ({"tr": "Yıllık volatilite (oynaklık)", "en": "Annual volatility", "de": "Jährliche Volatilität"},
     {"tr": "Getirilerin ne kadar dalgalandığı. %20 oynaklık, kabaca yılların üçte ikisinde getirinin ortalamanın ±%20 çevresinde kalması demektir.",
      "en": "How much returns fluctuate. 20% volatility roughly means returns stay within ±20% of the average in about two years out of three.",
      "de": "Wie stark die Renditen schwanken. 20 % Volatilität heißt grob, dass die Rendite in etwa zwei von drei Jahren innerhalb von ±20 % um den Durchschnitt liegt."}),
    ({"tr": "Sharpe oranı", "en": "Sharpe ratio", "de": "Sharpe-Ratio"},
     {"tr": "Birim oynaklık başına getiri. Kabaca: 0,5 altı zayıf, 0,5–1 makul, 1 üstü iyi, 2 üstü olağanüstü (ve şüpheyle bakılmalı). Modelleri karşılaştırmanın ana ölçüsüdür.",
      "en": "Return per unit of volatility. Roughly: below 0.5 weak, 0.5–1 reasonable, above 1 good, above 2 exceptional (and worth questioning). The main yardstick for comparing models.",
      "de": "Rendite je Volatilitätseinheit. Grob: unter 0,5 schwach, 0,5–1 vernünftig, über 1 gut, über 2 außergewöhnlich (und kritisch zu prüfen). Der wichtigste Maßstab für den Modellvergleich."}),
    ({"tr": "Sortino oranı", "en": "Sortino ratio", "de": "Sortino-Ratio"},
     {"tr": "Sharpe gibi, ama yalnızca aşağı yönlü oynaklığı risk sayar. Sharpe'tan belirgin yüksekse yükselişler düşüşlerden daha sert demektir.",
      "en": "Like Sharpe but counting only downside volatility as risk. If it is clearly higher than Sharpe, rallies are sharper than sell-offs.",
      "de": "Wie Sharpe, zählt aber nur die Abwärtsvolatilität als Risiko. Liegt sie deutlich über Sharpe, sind Anstiege stärker als Rückgänge."}),
    ({"tr": "Maks. düşüş", "en": "Max drawdown", "de": "Max. Drawdown"},
     {"tr": "Bir zirveden sonraki en derin kayıp. %30 düşüşten çıkmak için %43 kazanç gerekir. Psikolojik olarak dayanabileceğiniz seviyeyle karşılaştırın.",
      "en": "The deepest loss after a peak. Recovering from a 30% drawdown takes a 43% gain. Compare it with what you could stomach.",
      "de": "Der tiefste Verlust nach einem Höchststand. Nach 30 % Rückgang braucht es 43 % Gewinn zur Erholung. Vergleichen Sie das mit dem, was Sie aushalten würden."}),
    ({"tr": "CVaR %95", "en": "CVaR 95%", "de": "CVaR 95 %"},
     {"tr": "En kötü %5'lik günlerdeki ortalama günlük kayıp. %3 ise, kötü günlerde portföy ortalama %3 eriyor demektir.",
      "en": "Average daily loss on the worst 5% of days. 3% means the portfolio loses about 3% on a typical bad day.",
      "de": "Durchschnittlicher Tagesverlust an den schlechtesten 5 % der Tage. 3 % heißt, an einem typischen schlechten Tag verliert das Portfolio etwa 3 %."}),
    ({"tr": "Etkin varlık sayısı", "en": "Effective number of assets", "de": "Effektive Anzahl von Werten"},
     {"tr": "1 / Σw². Ağırlıkların gerçekte kaç varlığa yayıldığı: 6 varlıkta 6 tam dengeli, 1,5 ise neredeyse tek varlığa yığılmış demektir.",
      "en": "1 / Σw². How many assets the weights are really spread across: with 6 assets, 6 is perfectly balanced and 1.5 means nearly all in one.",
      "de": "1 / Σw². Auf wie viele Werte die Gewichte tatsächlich verteilt sind: Bei 6 Werten ist 6 perfekt ausgewogen, 1,5 heißt fast alles in einem."}),
    ({"tr": "Risk katkısı", "en": "Risk contribution", "de": "Risikobeitrag"},
     {"tr": "Toplam riskin ne kadarının bir varlıktan geldiği. Sermaye payı %20, risk payı %40 olan varlık, portföyün en büyük risk kaynağıdır.",
      "en": "How much of total risk comes from one asset. An asset with 20% of capital but 40% of risk is the portfolio's main risk driver.",
      "de": "Welcher Anteil des Gesamtrisikos auf einen Wert entfällt. Ein Wert mit 20 % Kapital, aber 40 % Risiko ist der Haupttreiber des Portfoliorisikos."}),
    ({"tr": "Walk-forward backtest", "en": "Walk-forward backtest", "de": "Walk-Forward-Backtest"},
     {"tr": "Model geçmişin bir penceresiyle eğitilir, hemen sonraki dönemde (görmediği veride) test edilir, pencere kaydırılır. Gerçek kullanıma en yakın sınamadır; yine de komisyon ve vergiyi içermez.",
      "en": "The model is trained on one window of history, tested on the next (unseen) period, and the window rolls forward. The closest test to real use, though it excludes fees and taxes.",
      "de": "Das Modell wird auf einem historischen Fenster trainiert, im folgenden (ungesehenen) Zeitraum getestet und das Fenster verschoben. Der realitätsnächste Test, allerdings ohne Gebühren und Steuern."}),
    ({"tr": "Zaman ağırlıklı getiri (TWR)", "en": "Time-weighted return (TWR)", "de": "Zeitgewichtete Rendite (TWR)"},
     {"tr": "Para yatırma ve çekmelerin etkisini ayıklar; yalnızca yatırım kararlarının başarısını ölçer. Fon ve benchmark karşılaştırmalarında kullanılır.",
      "en": "Strips out the effect of deposits and withdrawals, measuring only investment skill. Used to compare against funds and benchmarks.",
      "de": "Bereinigt um Ein- und Auszahlungen und misst nur den Anlageerfolg. Wird für Vergleiche mit Fonds und Benchmarks verwendet."}),
    ({"tr": "XIRR (para ağırlıklı getiri)", "en": "XIRR (money-weighted return)", "de": "XIRR (geldgewichtete Rendite)"},
     {"tr": "Paranızın ne zaman girip çıktığını hesaba katan yıllık getiri. Sizin cebinize yansıyan getiridir; TWR'den farkı, zamanlamanızın etkisidir.",
      "en": "Annual return that accounts for when your money went in and out. It is the return you actually experienced; the gap to TWR is the effect of your timing.",
      "de": "Jahresrendite unter Berücksichtigung, wann Geld zu- und abfloss. Die tatsächlich erlebte Rendite; der Unterschied zur TWR ist der Effekt Ihres Timings."}),
    ({"tr": "Reel getiri", "en": "Real return", "de": "Realrendite"},
     {"tr": "Enflasyondan arındırılmış getiri: (1 + getiri) / (1 + enflasyon) − 1. Satın alma gücünüzün gerçekten artıp artmadığını gösterir.",
      "en": "Inflation-adjusted return: (1 + return) / (1 + inflation) − 1. Shows whether your purchasing power actually grew.",
      "de": "Inflationsbereinigte Rendite: (1 + Rendite) / (1 + Inflation) − 1. Zeigt, ob Ihre Kaufkraft tatsächlich gestiegen ist."}),
]

LABELS = {
    "year": {"tr": "Yıl", "en": "Year", "de": "Jahr"},
    "origin": {"tr": "Kökeni", "en": "Origin", "de": "Herkunft"},
    "idea": {"tr": "Temel fikir", "en": "Core idea", "de": "Grundidee"},
    "read": {"tr": "Sonuçlar nasıl okunur", "en": "How to read the results", "de": "So lesen Sie die Ergebnisse"},
    "strengths": {"tr": "Güçlü yanı", "en": "Strength", "de": "Stärke"},
    "caution": {"tr": "Dikkat", "en": "Caution", "de": "Vorsicht"},
}


def _pick(d: dict | str, lang: str | None = None) -> str:
    if isinstance(d, str):
        return d
    lang = lang or get_lang()
    return d.get(lang) or d.get("tr", "")


def info(model: str, field: str, lang: str | None = None) -> str:
    entry = GUIDE.get(model)
    if not entry or field not in entry:
        return ""
    return _pick(entry[field], lang)


def markdown(model: str, lang: str | None = None) -> str:
    """Bir modelin rehber kartı (Markdown)."""
    if model not in GUIDE:
        return ""
    lang = lang or get_lang()
    e = GUIDE[model]
    parts = [f"**{_pick(LABELS['year'], lang)}:** {_pick(e['year'], lang)}"]
    for f in ("origin", "idea", "read", "strengths", "caution"):
        parts.append(f"**{_pick(LABELS[f], lang)}:** {_pick(e[f], lang)}")
    return "\n\n".join(parts)


def metrics_markdown(lang: str | None = None) -> str:
    lang = lang or get_lang()
    return "\n".join(f"- **{_pick(name, lang)}** — {_pick(desc, lang)}" for name, desc in METRICS)

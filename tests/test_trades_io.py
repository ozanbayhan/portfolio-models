import pandas as pd
import pytest

from portfolio_models.holdings import KIND_BIST, KIND_FUND, KIND_GOLD, KIND_YAHOO, aggregate_trades, parse_trades
from portfolio_models.trades_io import export_csv, merge_trades, parse_trades_file, template_csv


def test_template_roundtrip():
    rows, warns = parse_trades_file(template_csv(), "sablon.csv")
    assert warns == [] and len(rows) == 7
    assert rows[0] == {"Tarih": "2025-01-15", "İşlem": "Al", "Tür": KIND_BIST, "Sembol": "THYAO",
                       "Adet": 100.0, "Fiyat": 290.5}
    assert rows[3]["Tür"] == KIND_GOLD and rows[3]["Sembol"] == ""
    trades, tw = parse_trades(rows)
    assert tw == [] and len(trades) == 7
    # dışa aktar -> tekrar içe aktar aynı sonucu verir
    again, _ = parse_trades_file(export_csv(rows), "export.csv")
    assert again == rows


def test_broker_style_statement():
    csv = (
        "İşlem Tarihi;Menkul;İşlem Tipi;Miktar;Ortalama Fiyat;Tutar;Komisyon\n"
        "05.01.2026;THYAO;Alış;100;298,40;29.840,00;5,97\n"
        "06.01.2026;ASELS;ALIŞ;50;121,10;6.055,00;1,21\n"
        "20.02.2026;THYAO;Satış;40;331,00;13.240,00;2,65\n"
        "toplam;;;;;49.135,00;\n"
    ).encode("cp1254")
    rows, warns = parse_trades_file(csv, "ekstre.csv")
    assert [(r["Sembol"], r["İşlem"], r["Adet"], r["Fiyat"]) for r in rows] == [
        ("THYAO", "Al", 100, 298.4), ("ASELS", "Al", 50, 121.1), ("THYAO", "Sat", 40, 331.0)]
    assert all(r["Tür"] == KIND_BIST for r in rows)
    assert len(warns) == 1  # toplam satırı
    summ, _ = aggregate_trades(parse_trades(rows)[0])
    assert summ["THYAO"].qty == 60


def test_english_excel_with_kind_column(tmp_path):
    pd.DataFrame({
        "Date": ["2026-01-05", "2026-01-06"], "Side": ["BUY", "SELL"], "Ticker": ["aapl", "AAPL"],
        "Quantity": [3, 1], "Price": [210.5, 220], "Asset type": ["ETF", "Yahoo"],
    }).to_excel(tmp_path / "t.xlsx", index=False)
    rows, warns = parse_trades_file((tmp_path / "t.xlsx").read_bytes(), "t.xlsx", default_kind=KIND_FUND)
    assert warns == []
    assert [(r["Tür"], r["Sembol"], r["İşlem"]) for r in rows] == [(KIND_YAHOO, "AAPL", "Al"), (KIND_YAHOO, "AAPL", "Sat")]


def test_missing_columns_message():
    with pytest.raises(ValueError, match="İşlem"):
        parse_trades_file(b"Tarih;Sembol;Adet;Fiyat\n01.01.2026;X;1;1\n", "x.csv")


def test_merge_skips_duplicates():
    rows, _ = parse_trades_file(template_csv(), "s.csv")
    merged, skipped = merge_trades(rows[:3], rows)
    assert len(merged) == 7 and skipped == 3


def test_statement_with_dividend_and_cash():
    csv = (
        "Tarih;İşlem;Sembol;Adet;Fiyat;Tutar\n"
        "02.01.2026;Para Yatırma;;;;50.000,00\n"
        "05.01.2026;Alış;THYAO;100;300;30.000,00\n"
        "15.05.2026;Temettü;THYAO;;;1.250,50\n"
        "01.06.2026;Para Çekme;;;;-5.000,00\n"
    ).encode("utf-8")
    rows, warns = parse_trades_file(csv, "x.csv")
    assert warns == []
    assert [(r["İşlem"], r["Tür"], r["Sembol"], r.get("Tutar")) for r in rows] == [
        ("Para yatır", "Nakit", "TRY", 50000.0), ("Al", KIND_BIST, "THYAO", None),
        ("Temettü", KIND_BIST, "THYAO", 1250.5), ("Para çek", "Nakit", "TRY", 5000.0)]


def test_german_and_english_statements():
    csv = (
        "Datum;Aktion;Art;Symbol;Stück;Preis;Betrag\n"
        "05.01.2026;Kauf;BIST-Aktie;THYAO;10;300;\n"
        "06.01.2026;Verkauf;BIST stock;THYAO;5;310;\n"
        "07.01.2026;Dividende;BIST-Aktie;THYAO;;;12,50\n"
        "08.01.2026;Einzahlung;Cash;EUR;;;1.000,00\n"
        "09.01.2026;Withdrawal;Cash;TRY;;;500\n"
    ).encode("utf-8")
    rows, warns = parse_trades_file(csv, "de.csv")
    assert warns == []
    assert [(r["İşlem"], r["Tür"], r["Sembol"]) for r in rows] == [
        ("Al", KIND_BIST, "THYAO"), ("Sat", KIND_BIST, "THYAO"), ("Temettü", KIND_BIST, "THYAO"),
        ("Para yatır", "Nakit", "EUR"), ("Para çek", "Nakit", "TRY")]

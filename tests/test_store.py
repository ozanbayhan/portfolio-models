import pytest

from portfolio_models.store import (
    delete_portfolio,
    list_portfolios,
    load_portfolio,
    make_engine,
    save_portfolio,
)


@pytest.fixture
def engine(tmp_path):
    return make_engine(f"sqlite:///{tmp_path / 'test.db'}")


def test_save_load_overwrite(engine):
    save_portfolio(engine, "Ali@Example.com", "BIST", {"bist": "THYAO ASELS"})
    assert load_portfolio(engine, "ali@example.com", "BIST") == {"bist": "THYAO ASELS"}
    save_portfolio(engine, "ali@example.com", "BIST", {"bist": "EREGL"})
    assert load_portfolio(engine, "ali@example.com", "BIST") == {"bist": "EREGL"}
    assert [p["name"] for p in list_portfolios(engine, "ali@example.com")] == ["BIST"]


def test_users_are_isolated(engine):
    save_portfolio(engine, "ali@example.com", "Ortak ad", {"owner": "ali"})
    save_portfolio(engine, "ayse@example.com", "Ortak ad", {"owner": "ayse"})
    assert load_portfolio(engine, "ali@example.com", "Ortak ad") == {"owner": "ali"}
    assert load_portfolio(engine, "ayse@example.com", "Ortak ad") == {"owner": "ayse"}
    assert [p["name"] for p in list_portfolios(engine, "veli@example.com")] == []
    # Başkasının kaydı silinemez
    assert delete_portfolio(engine, "veli@example.com", "Ortak ad") is False
    assert delete_portfolio(engine, "ali@example.com", "Ortak ad") is True
    assert load_portfolio(engine, "ayse@example.com", "Ortak ad") == {"owner": "ayse"}


def test_validation(engine):
    with pytest.raises(ValueError):
        save_portfolio(engine, "", "x", {})
    with pytest.raises(ValueError):
        save_portfolio(engine, "ali@example.com", "   ", {})

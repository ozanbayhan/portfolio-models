"""Kullanıcıya özel portföy kayıtları.

Her sorgu kullanıcının e-postasıyla filtrelenir; bir kullanıcı başkasının
kaydını göremez, değiştiremez veya silemez. Veritabanı bağlantı bilgisi
yalnızca sunucuda (Streamlit secrets) durur, tarayıcıya gönderilmez.
"""

from __future__ import annotations

from .i18n import t as T

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    insert,
    select,
    update,
)

metadata = MetaData()

portfolios = Table(
    "portfolios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_email", String(320), nullable=False, index=True),
    Column("name", String(120), nullable=False),
    Column("config", Text, nullable=False),  # JSON: semboller, tarihler, modeller, görüşler…
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_email", "name", name="uq_portfolios_user_name"),
)

holdings = Table(
    "holdings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_email", String(320), nullable=False, index=True),
    Column("name", String(120), nullable=False),
    Column("config", Text, nullable=False),  # JSON: pozisyon satırları
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_email", "name", name="uq_holdings_user_name"),
)

fund_prices = Table(
    "fund_prices",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_email", String(320), nullable=False, index=True),
    Column("name", String(120), nullable=False),  # fon kodu
    Column("config", Text, nullable=False),  # JSON: {"YYYY-MM-DD": fiyat}
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_email", "name", name="uq_fund_prices_user_name"),
)

settings = Table(
    "user_settings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_email", String(320), nullable=False, index=True),
    Column("name", String(120), nullable=False),  # ayar adı
    Column("config", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_email", "name", name="uq_user_settings_user_name"),
)

model_portfolios = Table(
    "model_portfolios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_email", String(320), nullable=False, index=True),
    Column("name", String(120), nullable=False),  # model portföy adı
    Column("config", Text, nullable=False),  # JSON: kurum, ülke, kaynak, tarihli revizyonlar
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_email", "name", name="uq_model_portfolios_user_name"),
)

TABLES = {"portfolio": portfolios, "holdings": holdings, "fund_prices": fund_prices, "settings": settings,
          "model_portfolio": model_portfolios}
MAX_PORTFOLIOS_PER_USER = 50


def _t(kind: str) -> Table:
    try:
        return TABLES[kind]
    except KeyError:
        raise ValueError(T("Bilinmeyen kayıt türü: {kind}", kind=kind)) from None


def make_engine(url: str) -> Engine:
    engine = create_engine(url, pool_pre_ping=True)
    metadata.create_all(engine)
    return engine


def _norm(email: str) -> str:
    email = (email or "").strip().lower()
    if not email:
        raise ValueError(T("Kullanıcı e-postası boş olamaz."))
    return email


def list_portfolios(engine: Engine, email: str, kind: str = "portfolio") -> list[dict[str, Any]]:
    t = _t(kind)
    q = (
        select(t.c.name, t.c.updated_at)
        .where(t.c.user_email == _norm(email))
        .order_by(t.c.updated_at.desc())
    )
    with engine.connect() as conn:
        return [dict(r._mapping) for r in conn.execute(q)]


def load_portfolio(engine: Engine, email: str, name: str, kind: str = "portfolio") -> Any | None:
    t = _t(kind)
    q = select(t.c.config).where(t.c.user_email == _norm(email), t.c.name == name)
    with engine.connect() as conn:
        row = conn.execute(q).first()
    return json.loads(row.config) if row else None


def save_portfolio(engine: Engine, email: str, name: str, config: Any, kind: str = "portfolio") -> None:
    """Aynı adla kayıt varsa üzerine yazar, yoksa yenisini ekler."""
    email, name = _norm(email), name.strip()
    if not name:
        raise ValueError(T("Portföy adı boş olamaz."))
    if len(name) > 120:
        raise ValueError(T("Portföy adı en fazla 120 karakter olabilir."))
    payload = json.dumps(config, ensure_ascii=False, default=str)
    now = datetime.now(timezone.utc)
    t = _t(kind)
    where = (t.c.user_email == email) & (t.c.name == name)
    with engine.begin() as conn:
        exists = conn.execute(select(t.c.id).where(where)).first()
        if exists:
            conn.execute(update(t).where(where).values(config=payload, updated_at=now))
            return
        count = len(conn.execute(select(t.c.id).where(t.c.user_email == email)).all())
        if count >= MAX_PORTFOLIOS_PER_USER:
            raise ValueError(T("En fazla {n} portföy kaydedebilirsiniz.", n=MAX_PORTFOLIOS_PER_USER))
        conn.execute(
            insert(t).values(user_email=email, name=name, config=payload, updated_at=now)
        )


def delete_portfolio(engine: Engine, email: str, name: str, kind: str = "portfolio") -> bool:
    t = _t(kind)
    with engine.begin() as conn:
        result = conn.execute(delete(t).where(t.c.user_email == _norm(email), t.c.name == name))
    return result.rowcount > 0

"""Kullanıcıya özel portföy kayıtları.

Her sorgu kullanıcının e-postasıyla filtrelenir; bir kullanıcı başkasının
kaydını göremez, değiştiremez veya silemez. Veritabanı bağlantı bilgisi
yalnızca sunucuda (Streamlit secrets) durur, tarayıcıya gönderilmez.
"""

from __future__ import annotations

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

MAX_PORTFOLIOS_PER_USER = 50


def make_engine(url: str) -> Engine:
    engine = create_engine(url, pool_pre_ping=True)
    metadata.create_all(engine)
    return engine


def _norm(email: str) -> str:
    email = (email or "").strip().lower()
    if not email:
        raise ValueError("Kullanıcı e-postası boş olamaz.")
    return email


def list_portfolios(engine: Engine, email: str) -> list[dict[str, Any]]:
    q = (
        select(portfolios.c.name, portfolios.c.updated_at)
        .where(portfolios.c.user_email == _norm(email))
        .order_by(portfolios.c.updated_at.desc())
    )
    with engine.connect() as conn:
        return [dict(r._mapping) for r in conn.execute(q)]


def load_portfolio(engine: Engine, email: str, name: str) -> dict[str, Any] | None:
    q = select(portfolios.c.config).where(
        portfolios.c.user_email == _norm(email), portfolios.c.name == name
    )
    with engine.connect() as conn:
        row = conn.execute(q).first()
    return json.loads(row.config) if row else None


def save_portfolio(engine: Engine, email: str, name: str, config: dict[str, Any]) -> None:
    """Aynı adla kayıt varsa üzerine yazar, yoksa yenisini ekler."""
    email, name = _norm(email), name.strip()
    if not name:
        raise ValueError("Portföy adı boş olamaz.")
    if len(name) > 120:
        raise ValueError("Portföy adı en fazla 120 karakter olabilir.")
    payload = json.dumps(config, ensure_ascii=False, default=str)
    now = datetime.now(timezone.utc)
    where = (portfolios.c.user_email == email) & (portfolios.c.name == name)
    with engine.begin() as conn:
        exists = conn.execute(select(portfolios.c.id).where(where)).first()
        if exists:
            conn.execute(update(portfolios).where(where).values(config=payload, updated_at=now))
            return
        count = len(conn.execute(select(portfolios.c.id).where(portfolios.c.user_email == email)).all())
        if count >= MAX_PORTFOLIOS_PER_USER:
            raise ValueError(f"En fazla {MAX_PORTFOLIOS_PER_USER} portföy kaydedebilirsiniz.")
        conn.execute(
            insert(portfolios).values(user_email=email, name=name, config=payload, updated_at=now)
        )


def delete_portfolio(engine: Engine, email: str, name: str) -> bool:
    with engine.begin() as conn:
        result = conn.execute(
            delete(portfolios).where(
                portfolios.c.user_email == _norm(email), portfolios.c.name == name
            )
        )
    return result.rowcount > 0

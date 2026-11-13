from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine

import app.models  # noqa: F401  (regista todas as tabelas no metadata)


def init_db() -> None:
    """Cria no arranque as tabelas/enums que ainda não existem (não altera as existentes)."""
    Base.metadata.create_all(bind=engine, checkfirst=True)
    # create_all não acrescenta colunas a tabelas já criadas.
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS estado VARCHAR(20) NOT NULL DEFAULT 'aberta'"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS estado VARCHAR(20) NOT NULL DEFAULT 'pendente'"
            )
        )

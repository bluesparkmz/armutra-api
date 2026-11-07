from app.db.base import Base
from app.db.session import engine

import app.models  # noqa: F401  (regista todas as tabelas no metadata)


def init_db() -> None:
    """Cria no arranque as tabelas/enums que ainda não existem (não altera as existentes)."""
    Base.metadata.create_all(bind=engine, checkfirst=True)

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.interaction import PostComment, PostLike, PostShare
    from app.models.job import Job
    from app.models.service import Service


class PostTipo(str, enum.Enum):
    VAGA = "vaga"
    SERVICO = "servico"
    GERAL = "geral"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tipo_post: Mapped[PostTipo] = mapped_column(
        SAEnum(PostTipo, name="post_tipo"), nullable=False
    )
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    salario: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    localizacao: Mapped[str] = mapped_column(String(255), nullable=False)
    imagens: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    service_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="SET NULL"),
        nullable=True,
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    author: Mapped["User"] = relationship(back_populates="posts")
    linked_job: Mapped[Optional["Job"]] = relationship(
        back_populates="feed_posts", foreign_keys=[job_id]
    )
    linked_service: Mapped[Optional["Service"]] = relationship(
        back_populates="feed_posts", foreign_keys=[service_id]
    )
    likes: Mapped[list["PostLike"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    comments: Mapped[list["PostComment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    shares: Mapped[list["PostShare"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )

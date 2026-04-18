import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.profile import CandidatoProfile, EmpresaProfile
    from app.models.post import Post
    from app.models.job import Job, JobApplication
    from app.models.service import Service
    from app.models.message import Conversation, Message


class UserType(str, enum.Enum):
    EMPRESA = "empresa"
    CANDIDATO = "candidato"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[UserType] = mapped_column(
        SAEnum(UserType, name="user_type"), nullable=False
    )
    foto_perfil: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    localizacao: Mapped[str] = mapped_column(String(255), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    empresa_profile: Mapped[Optional["EmpresaProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    candidato_profile: Mapped[Optional["CandidatoProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    posts: Mapped[list["Post"]] = relationship(back_populates="author")
    jobs_posted: Mapped[list["Job"]] = relationship(
        back_populates="empresa", foreign_keys="Job.empresa_user_id"
    )
    applications: Mapped[list["JobApplication"]] = relationship(
        back_populates="candidato", foreign_keys="JobApplication.candidato_user_id"
    )
    services: Mapped[list["Service"]] = relationship(back_populates="owner")

    conversations_a: Mapped[list["Conversation"]] = relationship(
        back_populates="participant_a",
        foreign_keys="Conversation.participant_a_id",
    )
    conversations_b: Mapped[list["Conversation"]] = relationship(
        back_populates="participant_b",
        foreign_keys="Conversation.participant_b_id",
    )
    messages_sent: Mapped[list["Message"]] = relationship(
        back_populates="sender", foreign_keys="Message.sender_id"
    )

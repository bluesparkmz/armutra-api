import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.payment import Payment
    from app.models.post import Post
    from app.models.service import Service
    from app.models.user import User


class Ad(Base):
    """Boost/anúncio pago de uma vaga, serviço ou publicação (exactamente um alvo)."""

    __tablename__ = "ads"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(job_id, service_id, post_id) = 1", name="ck_ad_single_target"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(10), nullable=False)  # job | service | post
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True
    )
    post_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    preco: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MZN")
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    # pending_payment | active | expired
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_payment")
    payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    job: Mapped[Optional["Job"]] = relationship(foreign_keys=[job_id])
    service: Mapped[Optional["Service"]] = relationship(foreign_keys=[service_id])
    post: Mapped[Optional["Post"]] = relationship(foreign_keys=[post_id])
    payment: Mapped[Optional["Payment"]] = relationship(foreign_keys=[payment_id])

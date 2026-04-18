from uuid import UUID


def ordered_user_ids(a: UUID, b: UUID) -> tuple[UUID, UUID]:
    """Garante ordem estável para conversas 1:1 (menor UUID primeiro)."""
    if a <= b:
        return a, b
    return b, a

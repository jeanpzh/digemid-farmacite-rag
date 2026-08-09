from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

class EmbeddingConfig(Base):
    __tablename__ = "embedding_config"
    __table_args__ = {"schema": "rag"}

    id: Mapped[bool] = mapped_column(Boolean, primary_key=True, default=True)
    model: Mapped[str] = mapped_column(String, nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)

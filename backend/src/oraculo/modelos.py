import enum
import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Tamanho do vetor do nomic-embed-text. Fica fixo na coluna do banco: trocar o
# modelo de embeddings exige uma migracao nova e reprocessar os documentos.
DIMENSAO_EMBEDDINGS = 768


def agora() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class StatusDocumento(enum.StrEnum):
    PROCESSANDO = "processando"
    PRONTO = "pronto"
    ERRO = "erro"


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class Documento(Base):
    __tablename__ = "documento"

    # UUID e nao sequencial: id sequencial na URL deixa adivinhar quantos
    # documentos existem e tentar os dos outros.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    nome_arquivo: Mapped[str] = mapped_column(String(255))
    tamanho_bytes: Mapped[int] = mapped_column(Integer)
    paginas: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[StatusDocumento] = mapped_column(
        Enum(
            StatusDocumento, name="status_documento", values_callable=lambda e: [m.value for m in e]
        ),
        default=StatusDocumento.PROCESSANDO,
    )
    erro: Mapped[str | None] = mapped_column(String(500))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)

    trechos: Mapped[list["Trecho"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan", passive_deletes=True
    )


class Trecho(Base):
    __tablename__ = "trecho"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    documento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documento.id", ondelete="CASCADE"), index=True
    )
    pagina: Mapped[int] = mapped_column(Integer)
    ordem: Mapped[int] = mapped_column(Integer)
    texto: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(DIMENSAO_EMBEDDINGS))

    documento: Mapped[Documento] = relationship(back_populates="trechos")

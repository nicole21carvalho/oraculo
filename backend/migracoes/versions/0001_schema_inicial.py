"""Schema inicial: usuarios, documentos e trechos com vetor

Revision ID: 0001
Revises:
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )

    status = sa.Enum("processando", "pronto", "erro", name="status_documento")
    op.create_table(
        "documento",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "usuario_id",
            sa.Integer,
            sa.ForeignKey("usuario.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nome_arquivo", sa.String(255), nullable=False),
        sa.Column("tamanho_bytes", sa.Integer, nullable=False),
        sa.Column("paginas", sa.Integer),
        sa.Column("status", status, nullable=False),
        sa.Column("erro", sa.String(500)),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documento_usuario_id", "documento", ["usuario_id", "criado_em"])

    op.create_table(
        "trecho",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "documento_id",
            sa.Uuid,
            sa.ForeignKey("documento.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pagina", sa.Integer, nullable=False),
        sa.Column("ordem", sa.Integer, nullable=False),
        sa.Column("texto", sa.Text, nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
    )
    op.create_index("ix_trecho_documento_id", "trecho", ["documento_id"])

    # HNSW: busca aproximada dos vizinhos mais proximos em tempo quase
    # constante. Sem indice, cada pergunta compara o vetor com todos os
    # trechos do banco. vector_cosine_ops porque a busca usa distancia cosseno.
    op.execute(
        "CREATE INDEX ix_trecho_embedding ON trecho USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("trecho")
    op.drop_table("documento")
    op.drop_table("usuario")
    sa.Enum(name="status_documento").drop(op.get_bind())

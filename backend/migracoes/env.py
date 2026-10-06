import os

from alembic import context
from sqlalchemy import create_engine, text

from oraculo.modelos import Base

# Numero qualquer, fixo: identifica a trava das migracoes no Postgres.
TRAVA_MIGRACOES = 7_004_220

config = context.config


def url_do_banco() -> str:
    # Os testes passam a URL do container pela configuracao do Alembic;
    # fora deles, ela vem da mesma variavel que a API usa.
    url = config.get_main_option("sqlalchemy.url") or os.environ.get("ORACULO_DATABASE_URL")
    if not url:
        raise RuntimeError("Defina ORACULO_DATABASE_URL para rodar as migracoes")
    return url


motor = create_engine(url_do_banco())
with motor.connect() as conexao:
    context.configure(connection=conexao, target_metadata=Base.metadata)
    with context.begin_transaction():
        # Cada replica da API roda as migracoes ao subir. Sem a trava, duas
        # replicas subindo juntas (Kubernetes) criariam a mesma tabela ao mesmo
        # tempo e uma delas falharia. A trava solta sozinha no fim da transacao.
        conexao.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": TRAVA_MIGRACOES})
        context.run_migrations()

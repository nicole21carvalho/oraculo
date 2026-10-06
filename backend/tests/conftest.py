"""Infraestrutura dos testes.

O banco e um Postgres com pgvector de verdade, num container (Testcontainers):
a busca vetorial depende do operador <=> e do indice HNSW, que um banco em
memoria nao tem. Os modelos de IA sao falsos, para os testes nao dependerem
do Ollama e darem sempre o mesmo resultado.
"""

import hashlib
import math
import re
from collections.abc import Iterator
from pathlib import Path

import fakeredis
import pytest
from alembic import command
from alembic.config import Config as ConfigAlembic
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

from oraculo.config import Configuracoes
from oraculo.ia import Vetorizador
from oraculo.main import criar_app
from oraculo.modelos import DIMENSAO_EMBEDDINGS

RESPOSTA_DO_MODELO_FALSO = "O prazo de inscrição termina em 5 de dezembro [1]."


class EmbeddingsDePalavras(Embeddings):
    """Vetor por saco de palavras: textos com palavras em comum ficam proximos.

    Imita o comportamento que importa de um modelo real (similaridade maior
    para textos relacionados) sem rede e de forma deterministica.
    """

    def _vetor(self, texto: str) -> list[float]:
        vetor = [0.0] * DIMENSAO_EMBEDDINGS
        for palavra in re.findall(r"\w{3,}", texto.lower()):
            if palavra in {"search_document", "search_query"}:
                continue
            posicao = int(hashlib.md5(palavra.encode()).hexdigest(), 16) % DIMENSAO_EMBEDDINGS  # noqa: S324
            vetor[posicao] += 1.0
        norma = math.sqrt(sum(v * v for v in vetor)) or 1.0
        return [v / norma for v in vetor]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vetor(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vetor(text)


@pytest.fixture(scope="session")
def motor() -> Iterator[Engine]:
    with PostgresContainer("pgvector/pgvector:0.8.7-pg17", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        alembic = ConfigAlembic(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic.set_main_option("sqlalchemy.url", url)
        command.upgrade(alembic, "head")
        motor = create_engine(url)
        yield motor
        motor.dispose()


@pytest.fixture
def fabrica_sessao(motor: Engine) -> Iterator[sessionmaker[Session]]:
    yield sessionmaker(motor, expire_on_commit=False)
    with motor.begin() as conexao:
        conexao.execute(text("TRUNCATE usuario, documento, trecho RESTART IDENTITY CASCADE"))


@pytest.fixture
def config(motor: Engine) -> Configuracoes:
    return Configuracoes(
        jwt_secret="segredo-de-teste-com-mais-de-32-bytes!!",
        database_url=motor.url.render_as_string(hide_password=False),
        # O vetor por palavras da notas mais baixas que um modelo real.
        similaridade_minima=0.2,
        perguntas_por_minuto=3,
        documentos_por_usuario=3,
        paginas_maximas_pdf=10,
        # O TestClient fala http://testserver; cookie Secure so iria por HTTPS.
        cookie_segura=False,
    )


@pytest.fixture
def chat() -> BaseChatModel:
    return FakeListChatModel(responses=[RESPOSTA_DO_MODELO_FALSO])


@pytest.fixture
def app(
    config: Configuracoes, fabrica_sessao: sessionmaker[Session], chat: BaseChatModel
) -> FastAPI:
    return criar_app(
        config,
        fabrica_sessao=fabrica_sessao,
        # Servidor proprio por teste: os contadores de limite nao vazam entre testes.
        redis=fakeredis.FakeRedis(server=fakeredis.FakeServer()),
        vetorizador=Vetorizador(EmbeddingsDePalavras(), usar_prefixos=True),
        chat=chat,
    )


@pytest.fixture
def cliente(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def outro_cliente(app: FastAPI) -> TestClient:
    """Segundo navegador, com o cookie de sessao de outro usuario."""
    return TestClient(app)


SENHA = "senha-forte-123"


def cadastrar(cliente: TestClient, email: str = "ana@exemplo.com") -> None:
    """Cria um usuario; o cookie de sessao fica guardado no proprio cliente."""
    resposta = cliente.post(
        "/api/auth/cadastro", json={"nome": "Ana", "email": email, "senha": SENHA}
    )
    assert resposta.status_code == 201, resposta.text


def gerar_pdf(paginas: list[str]) -> bytes:
    """Monta um PDF valido com uma pagina por item, sem biblioteca externa."""

    def escapar(linha: str) -> str:
        return linha.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objetos: list[bytes] = []
    total = len(paginas)
    fonte = 3 + 2 * total
    filhos = " ".join(f"{3 + 2 * i} 0 R" for i in range(total))
    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objetos.append(f"<< /Type /Pages /Kids [{filhos}] /Count {total} >>".encode())
    for i, conteudo in enumerate(paginas):
        linhas = " ".join(f"({escapar(linha)}) Tj 0 -16 Td" for linha in conteudo.split("\n"))
        fluxo = f"BT /F1 12 Tf 72 720 Td {linhas} ET".encode("latin-1")
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {fonte} 0 R >> >> /Contents {4 + 2 * i} 0 R >>".encode()
        )
        objetos.append(b"<< /Length %d >>\nstream\n" % len(fluxo) + fluxo + b"\nendstream")
    objetos.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )

    saida = bytearray(b"%PDF-1.4\n")
    posicoes = []
    for numero, corpo in enumerate(objetos, start=1):
        posicoes.append(len(saida))
        saida += f"{numero} 0 obj\n".encode() + corpo + b"\nendobj\n"
    inicio_xref = len(saida)
    saida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for posicao in posicoes:
        saida += f"{posicao:010d} 00000 n \n".encode()
    saida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n"
    ).encode()
    return bytes(saida)


EDITAL = [
    "Edital de concurso publico 2026.\nO concurso oferece 40 vagas para analista.",
    "Cronograma.\nO prazo de inscricao vai de 10 de novembro a 5 de dezembro de 2026.",
    "Remuneracao.\nO salario inicial do cargo de analista e de 8500 reais.",
]


def enviar_pdf(
    cliente: TestClient,
    paginas: list[str] | None = None,
    nome: str = "edital.pdf",
) -> dict[str, object]:
    resposta = cliente.post(
        "/api/documentos",
        files={"arquivo": (nome, gerar_pdf(paginas or EDITAL), "application/pdf")},
    )
    assert resposta.status_code == 202, resposta.text
    corpo: dict[str, object] = resposta.json()
    return corpo

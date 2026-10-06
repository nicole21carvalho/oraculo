import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.language_models import BaseChatModel
from prometheus_fastapi_instrumentator import Instrumentator
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from oraculo.config import Configuracoes, carregar_configuracoes
from oraculo.ia import Vetorizador, criar_chat, criar_vetorizador
from oraculo.rotas import auth, documentos, perguntas, saude

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def _erro_de_validacao(_: Request, erro: Exception) -> JSONResponse:
    """422 sem o valor recebido.

    O padrao do FastAPI devolve o campo "input" com o que foi enviado: numa
    senha curta demais, a resposta traria a propria senha, que pode acabar em
    log de proxy ou de navegador.
    """
    erros = erro.errors() if isinstance(erro, RequestValidationError) else []
    detalhes = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in erros]
    return JSONResponse({"detail": detalhes}, status_code=422)


def criar_app(
    config: Configuracoes,
    fabrica_sessao: sessionmaker[Session] | None = None,
    redis: Redis | None = None,
    vetorizador: Vetorizador | None = None,
    chat: BaseChatModel | None = None,
) -> FastAPI:
    """Monta a aplicacao. Os testes passam versoes falsas dos recursos externos."""
    app = FastAPI(
        title="Oráculo",
        description="Pergunte aos seus documentos: respostas com IA citando a fonte.",
        version="0.1.0",
    )

    if fabrica_sessao is None:
        # pool_pre_ping: descarta conexao que o Postgres derrubou (reinicio,
        # timeout) antes de entregar para a rota, em vez de falhar a requisicao.
        motor = create_engine(config.database_url, pool_pre_ping=True)
        fabrica_sessao = sessionmaker(motor, expire_on_commit=False)

    app.state.config = config
    app.state.fabrica_sessao = fabrica_sessao
    app.state.redis = redis or Redis.from_url(config.redis_url, socket_timeout=2)
    app.state.vetorizador = vetorizador or criar_vetorizador(config)
    app.state.chat = chat or criar_chat(config)

    app.add_exception_handler(RequestValidationError, _erro_de_validacao)

    # CORS so importa no desenvolvimento (interface na porta 3000, API na
    # 8000). Em producao o nginx serve as duas no mesmo endereco. Origens
    # explicitas, nunca "*": com cookie de sessao, "*" e proibido e perigoso.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origens,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    for modulo in (auth, documentos, perguntas, saude):
        app.include_router(modulo.router)

    # /metrics fica fora do /api de proposito: o nginx so publica /api, e o
    # Prometheus le as metricas pela rede interna.
    Instrumentator(excluded_handlers=["/metrics", "/api/saude.*"]).instrument(app).expose(
        app, include_in_schema=False
    )
    return app


def app_padrao() -> FastAPI:
    """Ponto de entrada do uvicorn (--factory)."""
    return criar_app(carregar_configuracoes())

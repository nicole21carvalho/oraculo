"""Dependencias injetadas nas rotas pelo FastAPI.

Os recursos (banco, Redis, modelos) ficam em app.state, criados uma vez em
criar_app. Nos testes, criar_app recebe versoes falsas no lugar dos reais.
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyCookie
from langchain_core.language_models import BaseChatModel
from redis import Redis
from sqlalchemy.orm import Session, sessionmaker

from oraculo.config import Configuracoes
from oraculo.ia import Vetorizador
from oraculo.modelos import Usuario
from oraculo.seguranca import NOME_COOKIE, ler_token

_cookie_sessao = APIKeyCookie(name=NOME_COOKIE, auto_error=False)


def obter_config(request: Request) -> Configuracoes:
    config: Configuracoes = request.app.state.config
    return config


def obter_fabrica_sessao(request: Request) -> sessionmaker[Session]:
    fabrica: sessionmaker[Session] = request.app.state.fabrica_sessao
    return fabrica


def obter_sessao(
    fabrica: Annotated[sessionmaker[Session], Depends(obter_fabrica_sessao)],
) -> Iterator[Session]:
    with fabrica() as sessao:
        yield sessao


def obter_redis(request: Request) -> Redis:
    redis: Redis = request.app.state.redis
    return redis


def obter_vetorizador(request: Request) -> Vetorizador:
    vetorizador: Vetorizador = request.app.state.vetorizador
    return vetorizador


def obter_chat(request: Request) -> BaseChatModel:
    chat: BaseChatModel = request.app.state.chat
    return chat


Config = Annotated[Configuracoes, Depends(obter_config)]
SessaoBD = Annotated[Session, Depends(obter_sessao)]


def usuario_atual(
    sessao: SessaoBD,
    config: Config,
    token: Annotated[str | None, Depends(_cookie_sessao)],
) -> Usuario:
    """O token vem num cookie httpOnly, que o JavaScript da pagina nao le.

    No localStorage, qualquer script injetado na pagina (XSS) copiaria o
    token e entraria na conta de outro lugar. O SameSite=Strict do cookie
    impede que outro site faca requisicoes em nome do usuario (CSRF).
    """
    usuario_id = ler_token(token, config) if token else None
    usuario = sessao.get(Usuario, usuario_id) if usuario_id is not None else None
    if usuario is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada. Entre novamente."
        )
    return usuario


UsuarioAtual = Annotated[Usuario, Depends(usuario_atual)]


def ip_do_cliente(request: Request) -> str:
    """IP de quem fez a requisicao, para o limite de tentativas.

    O nginx sobrescreve o X-Real-IP com o IP que ele viu, entao um valor
    forjado pelo cliente nao passa. Confiar no cabecalho so e seguro porque a
    API nao e alcancavel por fora do nginx: no compose ela nao publica porta,
    e no Kubernetes a NetworkPolicy so deixa o pod "web" falar com ela.
    """
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "?")


IpCliente = Annotated[str, Depends(ip_do_cliente)]

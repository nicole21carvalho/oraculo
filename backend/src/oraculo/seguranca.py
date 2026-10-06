import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Response
from pwdlib import PasswordHash
from redis import Redis
from redis.exceptions import RedisError

from oraculo.config import Configuracoes

log = logging.getLogger(__name__)

NOME_COOKIE = "oraculo_sessao"

# Argon2id, o algoritmo recomendado pela OWASP para guardar senha.
_hasher = PasswordHash.recommended()

# Usado quando o e-mail nao existe, para o login levar o mesmo tempo nos dois
# casos. Sem isso, medir o tempo de resposta revela quais e-mails tem conta.
_HASH_FALSO = _hasher.hash("senha-que-nao-pertence-a-ninguem")


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def conferir_senha(senha: str, senha_hash: str | None) -> bool:
    if senha_hash is None:
        _hasher.verify(senha, _HASH_FALSO)
        return False
    return _hasher.verify(senha, senha_hash)


def gerar_token(usuario_id: int, config: Configuracoes) -> str:
    agora = datetime.now(UTC)
    dados = {
        "sub": str(usuario_id),
        "iat": agora,
        "exp": agora + timedelta(minutes=config.jwt_expiracao_minutos),
    }
    return jwt.encode(dados, config.jwt_secret.get_secret_value(), algorithm="HS256")


def iniciar_sessao(resposta: Response, usuario_id: int, config: Configuracoes) -> None:
    resposta.set_cookie(
        NOME_COOKIE,
        gerar_token(usuario_id, config),
        max_age=config.jwt_expiracao_minutos * 60,
        # httponly: o JavaScript da pagina nao le o cookie (protege contra XSS).
        httponly=True,
        # secure: o navegador so envia o cookie por HTTPS.
        secure=config.cookie_segura,
        # strict: o cookie nao vai em requisicao que comeca em outro site (CSRF).
        samesite="strict",
        # So as rotas da API recebem o cookie; os arquivos da interface, nao.
        path="/api",
    )


def encerrar_sessao(resposta: Response, config: Configuracoes) -> None:
    resposta.delete_cookie(
        NOME_COOKIE, path="/api", httponly=True, secure=config.cookie_segura, samesite="strict"
    )


def ler_token(token: str, config: Configuracoes) -> int | None:
    try:
        # algorithms explicito: sem ele, um token com "alg": "none" passaria.
        dados = jwt.decode(
            token,
            config.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
        return int(dados["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None


def dentro_do_limite(redis: Redis, chave: str, maximo: int, janela_segundos: int = 60) -> bool:
    """Conta as chamadas no Redis; a janela comeca na primeira chamada.

    O contador fica no Redis, e nao na memoria do processo, para valer igual
    com varias replicas da API (no Kubernetes, por exemplo).
    """
    try:
        # SET NX com expiracao e INCR na mesma transacao (MULTI): o contador
        # nunca fica sem prazo, mesmo se o processo cair entre os dois comandos.
        with redis.pipeline() as pipe:
            pipe.set(f"limite:{chave}", 0, ex=janela_segundos, nx=True)
            pipe.incr(f"limite:{chave}")
            _, contagem = pipe.execute()
        return int(contagem) <= maximo
    except RedisError:
        # Redis fora do ar nao derruba a API. Nas perguntas o limite protege o
        # custo do modelo; no login, o Argon2 continua deixando cada tentativa
        # lenta. Fica registrado no log para o alerta pegar.
        log.warning("Redis indisponivel; limite de chamadas suspenso")
        return True

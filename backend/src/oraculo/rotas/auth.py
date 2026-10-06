from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from redis import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from oraculo.dependencias import Config, IpCliente, SessaoBD, UsuarioAtual, obter_redis
from oraculo.esquemas import Cadastro, ConfirmacaoSenha, Login, UsuarioSaida
from oraculo.modelos import Usuario
from oraculo.seguranca import (
    conferir_senha,
    dentro_do_limite,
    encerrar_sessao,
    gerar_hash,
    iniciar_sessao,
)

router = APIRouter(prefix="/api/auth", tags=["autenticação"])

RedisDep = Annotated[Redis, Depends(obter_redis)]


def _muitas_tentativas() -> HTTPException:
    return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitas tentativas. Aguarde um pouco.")


@router.post("/cadastro", status_code=status.HTTP_201_CREATED)
def cadastrar(
    dados: Cadastro,
    resposta: Response,
    sessao: SessaoBD,
    config: Config,
    redis: RedisDep,
    ip: IpCliente,
) -> UsuarioSaida:
    if not dentro_do_limite(redis, f"cadastro:ip:{ip}", config.cadastros_por_ip_por_hora, 3600):
        raise _muitas_tentativas()
    usuario = Usuario(
        nome=dados.nome, email=dados.email.lower(), senha_hash=gerar_hash(dados.senha)
    )
    sessao.add(usuario)
    try:
        sessao.commit()
    except IntegrityError:
        # A restricao unique do banco decide, e nao um SELECT antes do INSERT:
        # dois cadastros simultaneos com o mesmo e-mail passariam no SELECT.
        sessao.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já tem cadastro.") from None
    iniciar_sessao(resposta, usuario.id, config)
    return UsuarioSaida.model_validate(usuario)


@router.post("/login")
def entrar(
    dados: Login,
    resposta: Response,
    sessao: SessaoBD,
    config: Config,
    redis: RedisDep,
    ip: IpCliente,
) -> UsuarioSaida:
    email = dados.email.lower()
    if not (
        dentro_do_limite(redis, f"login:{email}", config.tentativas_login_por_minuto)
        and dentro_do_limite(redis, f"login:ip:{ip}", config.tentativas_login_por_ip_por_minuto)
    ):
        raise _muitas_tentativas()
    usuario = sessao.scalar(select(Usuario).where(Usuario.email == email))
    senha_confere = conferir_senha(dados.senha, usuario.senha_hash if usuario else None)
    if usuario is None or not senha_confere:
        # Mesma mensagem para e-mail inexistente e senha errada.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    iniciar_sessao(resposta, usuario.id, config)
    return UsuarioSaida.model_validate(usuario)


@router.post("/sair", status_code=status.HTTP_204_NO_CONTENT)
def sair(resposta: Response, config: Config) -> None:
    encerrar_sessao(resposta, config)


@router.get("/eu")
def eu(usuario: UsuarioAtual) -> UsuarioSaida:
    return UsuarioSaida.model_validate(usuario)


@router.post("/excluir-conta", status_code=status.HTTP_204_NO_CONTENT)
def excluir_conta(
    dados: ConfirmacaoSenha,
    usuario: UsuarioAtual,
    resposta: Response,
    sessao: SessaoBD,
    config: Config,
    redis: RedisDep,
) -> None:
    """Apaga a conta, os documentos e os vetores (LGPD, art. 18, VI).

    Pede a senha de novo: com a sessao aberta num computador emprestado,
    outra pessoa nao apaga a conta com um clique.
    """
    if not dentro_do_limite(redis, f"excluir:{usuario.id}", config.tentativas_login_por_minuto):
        raise _muitas_tentativas()
    if not conferir_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Senha incorreta.")
    # Documentos e trechos saem junto pelo ON DELETE CASCADE do banco.
    sessao.delete(usuario)
    sessao.commit()
    encerrar_sessao(resposta, config)

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from oraculo.dependencias import SessaoBD, obter_redis

router = APIRouter(prefix="/api/saude", tags=["saúde"])


@router.get("")
def vivo() -> dict[str, str]:
    """Liveness: o processo responde. Se falhar, o Kubernetes reinicia o pod."""
    return {"status": "ok"}


@router.get("/pronto")
def pronto(sessao: SessaoBD, redis: Annotated[Redis, Depends(obter_redis)]) -> dict[str, str]:
    """Readiness: as dependencias respondem. Se falhar, o pod sai do balanceamento
    mas nao e reiniciado, porque reiniciar nao conserta um banco fora do ar."""
    try:
        sessao.execute(text("SELECT 1"))
        redis.ping()
    except (SQLAlchemyError, RedisError):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Dependência indisponível"
        ) from None
    return {"status": "pronto"}

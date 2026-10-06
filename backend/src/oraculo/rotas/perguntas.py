import json
import logging
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.language_models import BaseChatModel
from redis import Redis

from oraculo.dependencias import (
    Config,
    SessaoBD,
    UsuarioAtual,
    obter_chat,
    obter_redis,
    obter_vetorizador,
)
from oraculo.esquemas import FonteSaida, Pergunta, Resposta
from oraculo.ia import Vetorizador
from oraculo.rag import Fonte, buscar_trechos, responder, responder_em_partes
from oraculo.seguranca import dentro_do_limite

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/perguntas", tags=["perguntas"])

Chat = Annotated[BaseChatModel, Depends(obter_chat)]


@dataclass(frozen=True)
class Consulta:
    pergunta: str
    fontes: list[Fonte]


def _consultar(
    dados: Pergunta,
    usuario: UsuarioAtual,
    sessao: SessaoBD,
    config: Config,
    redis: Annotated[Redis, Depends(obter_redis)],
    vetorizador: Annotated[Vetorizador, Depends(obter_vetorizador)],
) -> Consulta:
    """Parte comum as duas rotas: limite de uso e busca dos trechos."""
    # Cada pergunta custa uma chamada ao modelo; o limite evita que um
    # usuario (ou um script) ocupe o modelo de todos.
    if not dentro_do_limite(redis, f"perguntas:{usuario.id}", config.perguntas_por_minuto):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Você atingiu o limite de perguntas por minuto. Aguarde um pouco.",
        )
    fontes = buscar_trechos(
        sessao,
        vetorizador,
        usuario.id,
        dados.pergunta,
        dados.documento_ids,
        config.trechos_por_pergunta,
        config.similaridade_minima,
    )
    # Encerra a transacao de leitura: a conexao volta ao pool agora, e nao
    # so quando o modelo terminar de escrever, que pode levar dezenas de segundos.
    sessao.rollback()
    return Consulta(pergunta=dados.pergunta, fontes=fontes)


ConsultaFeita = Annotated[Consulta, Depends(_consultar)]


@router.post("")
def perguntar(consulta: ConsultaFeita, chat: Chat) -> Resposta:
    return Resposta(
        resposta=responder(chat, consulta.pergunta, consulta.fontes),
        fontes=[FonteSaida.model_validate(f) for f in consulta.fontes],
    )


def _evento(nome: str, dados: object) -> str:
    return f"event: {nome}\ndata: {json.dumps(dados, ensure_ascii=False, default=str)}\n\n"


@router.post("/stream")
def perguntar_em_tempo_real(consulta: ConsultaFeita, chat: Chat) -> StreamingResponse:
    """Server-Sent Events: primeiro as fontes, depois a resposta aos pedacos.

    A busca no banco acontece antes do stream comecar. Assim a conexao com o
    banco ja foi devolvida quando o modelo comeca a escrever, que e a parte lenta.
    """

    def eventos() -> Iterator[str]:
        yield _evento("fontes", [asdict(f) for f in consulta.fontes])
        try:
            for parte in responder_em_partes(chat, consulta.pergunta, consulta.fontes):
                yield _evento("token", {"texto": parte})
        except Exception as erro:
            # So o tipo do erro: a mensagem pode repetir o prompt, que tem a
            # pergunta do usuario e trechos dos documentos dele.
            log.error("Falha ao gerar a resposta: %s", type(erro).__name__)
            yield _evento("erro", {"mensagem": "O modelo de IA não respondeu. Tente de novo."})
            return
        yield _evento("fim", {})

    return StreamingResponse(
        eventos(),
        media_type="text/event-stream",
        # X-Accel-Buffering: diz ao nginx para repassar cada pedaco na hora,
        # em vez de juntar a resposta inteira antes de entregar.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

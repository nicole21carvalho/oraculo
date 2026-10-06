import uuid
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from oraculo.dependencias import (
    Config,
    SessaoBD,
    UsuarioAtual,
    obter_fabrica_sessao,
    obter_vetorizador,
)
from oraculo.esquemas import DocumentoSaida
from oraculo.ia import Vetorizador
from oraculo.ingestao import processar_documento
from oraculo.modelos import Documento

router = APIRouter(prefix="/api/documentos", tags=["documentos"])


def _do_usuario(sessao: SessaoBD, documento_id: uuid.UUID, usuario_id: int) -> Documento:
    documento = sessao.get(Documento, documento_id)
    # 404 tambem para documento de outro usuario: 403 confirmaria que o id existe.
    if documento is None or documento.usuario_id != usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento não encontrado.")
    return documento


def _nome_seguro(nome: str | None) -> str:
    """Tira caminho ("../../etc/passwd" vira "passwd") e caracteres de controle."""
    nome = PurePosixPath((nome or "").replace("\\", "/")).name
    nome = "".join(c for c in nome if c.isprintable()).strip()
    return nome[:255] or "documento.pdf"


# Rota sincrona (def, e nao async def) de proposito: o banco e acessado de
# forma sincrona, e numa rota async cada consulta travaria o servidor inteiro
# ate o banco responder. Rota sincrona o FastAPI roda numa thread separada.
@router.post("", status_code=status.HTTP_202_ACCEPTED)
def enviar(
    arquivo: UploadFile,
    usuario: UsuarioAtual,
    sessao: SessaoBD,
    config: Config,
    tarefas: BackgroundTasks,
    fabrica_sessao: Annotated[sessionmaker[Session], Depends(obter_fabrica_sessao)],
    vetorizador: Annotated[Vetorizador, Depends(obter_vetorizador)],
) -> DocumentoSaida:
    total = sessao.scalar(
        select(func.count()).select_from(Documento).where(Documento.usuario_id == usuario.id)
    )
    if (total or 0) >= config.documentos_por_usuario:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Você chegou ao limite de {config.documentos_por_usuario} documentos. "
            "Apague algum para enviar outro.",
        )

    limite = config.tamanho_maximo_pdf_mb * 1024 * 1024
    # O limite que segura o tamanho de verdade e o client_max_body_size do
    # nginx: quando a rota roda, o arquivo ja chegou. Esta e a segunda camada,
    # para a API nao depender do proxy. Le um byte a mais para saber se passou.
    conteudo = arquivo.file.read(limite + 1)
    if len(conteudo) > limite:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"O arquivo passa de {config.tamanho_maximo_pdf_mb} MB.",
        )
    # Confere a assinatura do arquivo, e nao a extensao ou o Content-Type,
    # que o cliente escolhe como quiser.
    if not conteudo.startswith(b"%PDF-"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Envie um arquivo PDF.")

    documento = Documento(
        usuario_id=usuario.id,
        nome_arquivo=_nome_seguro(arquivo.filename),
        tamanho_bytes=len(conteudo),
    )
    sessao.add(documento)
    sessao.commit()

    # 202 Accepted: o documento foi recebido, mas ler e vetorizar um PDF
    # grande leva tempo. A interface consulta o status ate ficar "pronto".
    tarefas.add_task(
        processar_documento,
        documento.id,
        conteudo,
        fabrica_sessao,
        vetorizador,
        config.tamanho_trecho,
        config.sobreposicao_trecho,
        config.paginas_maximas_pdf,
    )
    return DocumentoSaida.model_validate(documento)


@router.get("")
def listar(usuario: UsuarioAtual, sessao: SessaoBD) -> list[DocumentoSaida]:
    documentos = sessao.scalars(
        select(Documento)
        .where(Documento.usuario_id == usuario.id)
        .order_by(Documento.criado_em.desc())
    )
    return [DocumentoSaida.model_validate(d) for d in documentos]


@router.get("/{documento_id}")
def detalhar(documento_id: uuid.UUID, usuario: UsuarioAtual, sessao: SessaoBD) -> DocumentoSaida:
    return DocumentoSaida.model_validate(_do_usuario(sessao, documento_id, usuario.id))


@router.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar(documento_id: uuid.UUID, usuario: UsuarioAtual, sessao: SessaoBD) -> None:
    # Os trechos e vetores saem junto, pelo ON DELETE CASCADE do banco.
    sessao.delete(_do_usuario(sessao, documento_id, usuario.id))
    sessao.commit()

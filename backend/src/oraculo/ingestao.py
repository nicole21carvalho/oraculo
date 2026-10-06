"""Leitura do PDF, divisao em trechos e gravacao dos vetores."""

import io
import logging
import uuid
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy.orm import Session, sessionmaker

from oraculo.ia import Vetorizador
from oraculo.metricas import DOCUMENTOS_PROCESSADOS
from oraculo.modelos import Documento, StatusDocumento, Trecho

log = logging.getLogger(__name__)

# Quantos trechos vao por chamada ao modelo de embeddings. Um por vez e lento;
# o documento inteiro de uma vez pode estourar a memoria do Ollama.
LOTE_EMBEDDINGS = 32


class PdfRecusadoError(Exception):
    """PDF que nao da para processar, com a mensagem que o usuario vai ver."""

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class PdfSemTextoError(PdfRecusadoError):
    def __init__(self) -> None:
        super().__init__(
            "Não encontrei texto no PDF. Ele pode ser digitalizado (imagem), "
            "e o Oráculo ainda não faz OCR."
        )


@dataclass(frozen=True)
class TrechoExtraido:
    pagina: int
    ordem: int
    texto: str


def extrair_trechos(
    conteudo: bytes, tamanho: int, sobreposicao: int, paginas_maximas: int = 500
) -> tuple[int, list[TrechoExtraido]]:
    """Devolve o numero de paginas e os trechos, cada um com sua pagina.

    A divisao e feita pagina por pagina, e nao no texto inteiro: assim cada
    trecho pertence a uma pagina so, e a citacao "p. 3" fica exata.
    """
    leitor = PdfReader(io.BytesIO(conteudo))
    if leitor.is_encrypted:
        raise PdfRecusadoError("O PDF está protegido por senha. Envie uma versão sem senha.")
    # Conta as paginas antes de extrair qualquer texto: um PDF pequeno em bytes
    # pode declarar dezenas de milhares de paginas e ocupar a CPU por horas.
    if len(leitor.pages) > paginas_maximas:
        raise PdfRecusadoError(f"O PDF tem mais de {paginas_maximas} páginas. Divida o arquivo.")
    divisor = RecursiveCharacterTextSplitter(chunk_size=tamanho, chunk_overlap=sobreposicao)

    trechos: list[TrechoExtraido] = []
    for numero, pagina in enumerate(leitor.pages, start=1):
        # O Postgres recusa o caractere NUL em colunas de texto, e alguns PDFs
        # trazem esse caractere no meio do texto extraido.
        texto = (pagina.extract_text() or "").replace("\x00", "").strip()
        for pedaco in divisor.split_text(texto):
            trechos.append(TrechoExtraido(pagina=numero, ordem=len(trechos), texto=pedaco))

    if not trechos:
        raise PdfSemTextoError
    return len(leitor.pages), trechos


def processar_documento(
    documento_id: uuid.UUID,
    conteudo: bytes,
    fabrica_sessao: sessionmaker[Session],
    vetorizador: Vetorizador,
    tamanho_trecho: int,
    sobreposicao_trecho: int,
    paginas_maximas: int,
) -> None:
    """Roda em segundo plano, depois que o upload ja respondeu 202."""
    with fabrica_sessao() as sessao:
        documento = sessao.get(Documento, documento_id)
        if documento is None:  # apagado antes de terminar o processamento
            return
        try:
            paginas, extraidos = extrair_trechos(
                conteudo, tamanho_trecho, sobreposicao_trecho, paginas_maximas
            )
            for inicio in range(0, len(extraidos), LOTE_EMBEDDINGS):
                lote = extraidos[inicio : inicio + LOTE_EMBEDDINGS]
                vetores = vetorizador.vetorizar_trechos([t.texto for t in lote])
                sessao.add_all(
                    Trecho(
                        documento_id=documento_id,
                        pagina=t.pagina,
                        ordem=t.ordem,
                        texto=t.texto,
                        embedding=v,
                    )
                    for t, v in zip(lote, vetores, strict=True)
                )
            documento.paginas = paginas
            documento.status = StatusDocumento.PRONTO
        except PdfRecusadoError as recusa:
            sessao.rollback()
            documento.status = StatusDocumento.ERRO
            documento.erro = recusa.mensagem
        except Exception as erro:
            # Para o usuario, mensagem generica: a da excecao pode trazer
            # caminho interno ou URL do Ollama. No log vai so o tipo do erro,
            # sem a mensagem nem o traceback, que podem trazer texto do PDF.
            log.error("Falha ao processar o documento %s: %s", documento_id, type(erro).__name__)
            sessao.rollback()
            documento.status = StatusDocumento.ERRO
            documento.erro = "Não foi possível processar o arquivo. Tente enviá-lo novamente."
        DOCUMENTOS_PROCESSADOS.labels(status=documento.status.value).inc()
        sessao.commit()

import pytest

from oraculo.ingestao import PdfSemTextoError, extrair_trechos
from tests.conftest import gerar_pdf


def test_trecho_grande_e_dividido_sem_misturar_paginas() -> None:
    longa = "\n".join(f"Linha numero {i} do documento de teste." for i in range(60))
    pdf = gerar_pdf([longa, "Pagina curta."])

    paginas, trechos = extrair_trechos(pdf, tamanho=300, sobreposicao=50)

    assert paginas == 2
    assert len([t for t in trechos if t.pagina == 1]) > 1
    assert trechos[-1].pagina == 2
    assert all(len(t.texto) <= 300 for t in trechos)
    assert [t.ordem for t in trechos] == list(range(len(trechos)))


def test_pdf_sem_texto_levanta_erro_proprio() -> None:
    with pytest.raises(PdfSemTextoError):
        extrair_trechos(gerar_pdf(["", ""]), tamanho=300, sobreposicao=50)

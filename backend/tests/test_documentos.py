from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from oraculo.modelos import Documento, Trecho
from oraculo.rotas.documentos import _nome_seguro
from tests.conftest import cadastrar, enviar_pdf, gerar_pdf


def test_pdf_enviado_fica_pronto_com_um_trecho_por_pagina(
    cliente: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    cadastrar(cliente)

    enviado = enviar_pdf(cliente)
    # O TestClient roda a tarefa em segundo plano antes de devolver a resposta.
    detalhe = cliente.get(f"/api/documentos/{enviado['id']}").json()

    assert enviado["status"] == "processando"
    assert detalhe["status"] == "pronto"
    assert detalhe["paginas"] == 3
    with fabrica_sessao() as sessao:
        paginas = sessao.scalars(select(Trecho.pagina).order_by(Trecho.ordem)).all()
    assert paginas == [1, 2, 3]


def test_envio_exige_sessao(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/api/documentos", files={"arquivo": ("a.pdf", gerar_pdf(["x"]), "application/pdf")}
    )

    assert resposta.status_code == 401


def test_arquivo_que_nao_e_pdf_e_recusado_mesmo_com_extensao_pdf(cliente: TestClient) -> None:
    cadastrar(cliente)

    resposta = cliente.post(
        "/api/documentos",
        files={"arquivo": ("falso.pdf", b"MZ\x90\x00 executavel", "application/pdf")},
    )

    assert resposta.status_code == 415


def test_nome_do_arquivo_enviado_perde_o_caminho(cliente: TestClient) -> None:
    cadastrar(cliente)

    enviado = enviar_pdf(cliente, nome="..\\..\\pasta/segredo.pdf")

    assert enviado["nome_arquivo"] == "segredo.pdf"


def test_nome_seguro_tira_caracteres_de_controle_e_nunca_fica_vazio() -> None:
    # Navegadores costumam codificar esses caracteres antes de enviar, mas um
    # cliente feito a mao pode manda-los crus.
    assert _nome_seguro("segredo\x07\n.pdf") == "segredo.pdf"
    assert _nome_seguro("../\x00\x1b") == "documento.pdf"
    assert _nome_seguro(None) == "documento.pdf"
    assert len(_nome_seguro("a" * 400 + ".pdf")) == 255


def test_pdf_sem_texto_fica_com_erro_explicado(cliente: TestClient) -> None:
    cadastrar(cliente)

    enviado = enviar_pdf(cliente, paginas=[""])
    detalhe = cliente.get(f"/api/documentos/{enviado['id']}").json()

    assert detalhe["status"] == "erro"
    assert "OCR" in detalhe["erro"]


def test_pdf_com_paginas_demais_e_recusado(cliente: TestClient) -> None:
    cadastrar(cliente)

    # O config de teste permite 10 paginas.
    enviado = enviar_pdf(cliente, paginas=["texto"] * 11)
    detalhe = cliente.get(f"/api/documentos/{enviado['id']}").json()

    assert detalhe["status"] == "erro"
    assert "10 páginas" in detalhe["erro"]


def test_arquivo_acima_do_limite_e_recusado(cliente: TestClient) -> None:
    cadastrar(cliente)
    grande = gerar_pdf(["x"]) + b"0" * (20 * 1024 * 1024)

    resposta = cliente.post(
        "/api/documentos", files={"arquivo": ("grande.pdf", grande, "application/pdf")}
    )

    assert resposta.status_code == 413


def test_limite_de_documentos_por_usuario(cliente: TestClient) -> None:
    cadastrar(cliente)
    for _ in range(3):  # o config de teste permite 3
        enviar_pdf(cliente)

    resposta = cliente.post(
        "/api/documentos", files={"arquivo": ("a.pdf", gerar_pdf(["x"]), "application/pdf")}
    )

    assert resposta.status_code == 409


def test_usuario_nao_ve_nem_apaga_documento_de_outro(
    cliente: TestClient, outro_cliente: TestClient
) -> None:
    cadastrar(cliente, "dono@exemplo.com")
    cadastrar(outro_cliente, "intruso@exemplo.com")
    documento = enviar_pdf(cliente)

    assert outro_cliente.get("/api/documentos").json() == []
    assert outro_cliente.get(f"/api/documentos/{documento['id']}").status_code == 404
    assert outro_cliente.delete(f"/api/documentos/{documento['id']}").status_code == 404
    assert cliente.get(f"/api/documentos/{documento['id']}").status_code == 200


def test_apagar_documento_remove_os_trechos(
    cliente: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    cadastrar(cliente)
    documento = enviar_pdf(cliente)

    resposta = cliente.delete(f"/api/documentos/{documento['id']}")

    assert resposta.status_code == 204
    with fabrica_sessao() as sessao:
        assert sessao.scalar(select(func.count()).select_from(Trecho)) == 0
        assert sessao.scalar(select(func.count()).select_from(Documento)) == 0

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from oraculo.modelos import Documento, Trecho, Usuario
from oraculo.seguranca import NOME_COOKIE
from tests.conftest import SENHA, cadastrar, enviar_pdf


def test_cadastro_abre_sessao_por_cookie_protegido(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/api/auth/cadastro", json={"nome": "Ana", "email": "ana@exemplo.com", "senha": SENHA}
    )

    cookie = resposta.headers["set-cookie"].lower()
    assert resposta.status_code == 201
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api" in cookie
    # O token nunca aparece no corpo: o JavaScript da pagina nao tem como le-lo.
    assert "token" not in resposta.json()
    assert cliente.get("/api/auth/eu").json()["email"] == "ana@exemplo.com"


def test_cookie_e_marcado_secure_na_configuracao_padrao() -> None:
    from oraculo.config import Configuracoes

    assert Configuracoes(jwt_secret="x" * 40).cookie_segura is True


def test_email_repetido_e_recusado_sem_diferenciar_maiusculas(cliente: TestClient) -> None:
    cadastrar(cliente, "ana@exemplo.com")

    resposta = cliente.post(
        "/api/auth/cadastro",
        json={"nome": "Outra Ana", "email": "ANA@exemplo.com", "senha": "outra-senha-123"},
    )

    assert resposta.status_code == 409


def test_login_com_senha_certa_e_errada(cliente: TestClient, outro_cliente: TestClient) -> None:
    cadastrar(cliente)

    certo = outro_cliente.post("/api/auth/login", json={"email": "ana@exemplo.com", "senha": SENHA})
    errado = outro_cliente.post(
        "/api/auth/login", json={"email": "ana@exemplo.com", "senha": "errada"}
    )

    assert certo.status_code == 200
    assert errado.status_code == 401


def test_email_inexistente_tem_a_mesma_resposta_que_senha_errada(cliente: TestClient) -> None:
    cadastrar(cliente)

    inexistente = cliente.post(
        "/api/auth/login", json={"email": "ninguem@exemplo.com", "senha": "qualquer"}
    )
    senha_errada = cliente.post(
        "/api/auth/login", json={"email": "ana@exemplo.com", "senha": "qualquer"}
    )

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json() == senha_errada.json()


def test_login_bloqueia_depois_de_muitas_tentativas(cliente: TestClient) -> None:
    cadastrar(cliente)
    dados = {"email": "ana@exemplo.com", "senha": "errada"}

    codigos = [cliente.post("/api/auth/login", json=dados).status_code for _ in range(6)]

    assert codigos[:5] == [401] * 5
    assert codigos[5] == 429


def test_cadastro_limitado_por_ip(cliente: TestClient) -> None:
    ip = {"X-Real-IP": "203.0.113.7"}
    codigos = [
        cliente.post(
            "/api/auth/cadastro",
            headers=ip,
            json={"nome": "Robo", "email": f"robo{i}@exemplo.com", "senha": SENHA},
        ).status_code
        for i in range(11)
    ]

    assert codigos[:10] == [201] * 10
    assert codigos[10] == 429
    # Outro IP nao e afetado.
    outro = cliente.post(
        "/api/auth/cadastro",
        headers={"X-Real-IP": "198.51.100.9"},
        json={"nome": "Ana", "email": "ana@exemplo.com", "senha": SENHA},
    )
    assert outro.status_code == 201


def test_rota_protegida_recusa_sem_cookie_ou_com_cookie_adulterado(cliente: TestClient) -> None:
    cadastrar(cliente)
    token = cliente.cookies[NOME_COOKIE]

    sem_sessao = TestClient(cliente.app)
    adulterado = TestClient(cliente.app, cookies={NOME_COOKIE: token[:-3] + "abc"})

    assert sem_sessao.get("/api/auth/eu").status_code == 401
    assert adulterado.get("/api/auth/eu").status_code == 401


def test_sair_apaga_o_cookie(cliente: TestClient) -> None:
    cadastrar(cliente)

    resposta = cliente.post("/api/auth/sair")

    assert resposta.status_code == 204
    assert cliente.get("/api/auth/eu").status_code == 401


def test_erro_de_validacao_nao_devolve_a_senha_digitada(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/api/auth/cadastro",
        json={"nome": "Ana", "email": "ana@exemplo.com", "senha": "curta7"},
    )

    assert resposta.status_code == 422
    assert "curta7" not in resposta.text


def test_excluir_conta_apaga_usuario_documentos_e_vetores(
    cliente: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    cadastrar(cliente)
    enviar_pdf(cliente)

    senha_errada = cliente.post("/api/auth/excluir-conta", json={"senha": "nao-e-essa"})
    resposta = cliente.post("/api/auth/excluir-conta", json={"senha": SENHA})

    assert senha_errada.status_code == 403
    assert resposta.status_code == 204
    assert cliente.get("/api/auth/eu").status_code == 401
    with fabrica_sessao() as sessao:
        for tabela in (Usuario, Documento, Trecho):
            assert sessao.scalar(select(func.count()).select_from(tabela)) == 0

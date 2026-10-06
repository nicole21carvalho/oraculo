from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    """Tudo vem de variavel de ambiente com prefixo ORACULO_ (ou do .env)."""

    model_config = SettingsConfigDict(env_prefix="ORACULO_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://oraculo:oraculo@localhost:5432/oraculo"
    redis_url: str = "redis://localhost:6379/0"

    # Sem valor padrao de proposito: um padrao no codigo seria uma chave
    # publica, e com ela qualquer pessoa assinaria tokens validos.
    jwt_secret: SecretStr
    jwt_expiracao_minutos: int = 120
    # Cookie so por HTTPS. Os navegadores tratam http://localhost como seguro,
    # entao funciona no docker compose local; os testes desligam (http://testserver).
    cookie_segura: bool = True

    ollama_url: str = "http://localhost:11434"
    modelo_chat: str = "llama3.2:3b"
    modelo_embeddings: str = "nomic-embed-text"

    # Valores medidos com backend/avaliacao/avaliar_busca.py (12 perguntas de
    # resposta conhecida). Trecho de 300 caracteres achou a pagina certa em 1o
    # lugar em 11 de 12; com 1000, em 9 de 12, porque cada pagina virava um
    # trecho so, misturando assuntos. A sobreposicao evita cortar uma frase ao meio.
    tamanho_trecho: int = 300
    sobreposicao_trecho: int = 50
    # 4 trechos de 300 caracteres: prompt curto, que o modelo em CPU le rapido.
    trechos_por_pergunta: int = Field(default=4, ge=1, le=20)
    # Descarta trecho claramente sem relacao. Na avaliacao, o trecho certo nunca
    # ficou abaixo de 0,609, mas perguntas sem relacao chegaram a 0,615: nenhum
    # limite fixo separa os dois grupos. Por isso a decisao final de responder
    # "nao encontrei" fica com o modelo, instruido no prompt. Se nenhum trecho
    # passar daqui, a API responde sozinha, sem chamar o modelo.
    similaridade_minima: float = Field(default=0.55, ge=0, le=1)

    # Limites contra abuso: sem eles, um PDF de 50 mil paginas ou milhares de
    # envios ocupariam CPU, memoria e disco de todos os usuarios.
    tamanho_maximo_pdf_mb: int = 20
    paginas_maximas_pdf: int = 500
    documentos_por_usuario: int = 100

    perguntas_por_minuto: int = 10
    tentativas_login_por_minuto: int = 5
    # Por IP, alem do limite por e-mail: pega quem testa uma senha em muitas
    # contas (credential stuffing), que o limite por e-mail nao ve.
    tentativas_login_por_ip_por_minuto: int = 30
    cadastros_por_ip_por_hora: int = 10

    cors_origens: list[str] = ["http://localhost:3000"]

    @field_validator("jwt_secret")
    @classmethod
    def segredo_forte(cls, valor: SecretStr) -> SecretStr:
        # HS256 com chave curta pode ser quebrada por forca bruta offline.
        if len(valor.get_secret_value().encode()) < 32:
            raise ValueError("ORACULO_JWT_SECRET precisa de pelo menos 32 bytes")
        return valor


@lru_cache
def carregar_configuracoes() -> Configuracoes:
    return Configuracoes()

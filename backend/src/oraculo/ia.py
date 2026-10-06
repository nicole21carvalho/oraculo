"""Acesso aos modelos de IA, sempre pelas interfaces do LangChain.

A API so conhece `Embeddings` e `BaseChatModel`. Trocar o Ollama por OpenAI,
Anthropic ou outro provedor e trocar a fabrica abaixo, sem mexer no RAG.
"""

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama, OllamaEmbeddings

from oraculo.config import Configuracoes


class Vetorizador:
    """Transforma texto em vetor para a busca por similaridade.

    O nomic-embed-text foi treinado com prefixos que dizem se o texto e um
    documento ou uma pergunta. Sem eles a busca piora, porque pergunta e
    resposta raramente usam as mesmas palavras.
    """

    def __init__(self, embeddings: Embeddings, usar_prefixos: bool) -> None:
        self._embeddings = embeddings
        self._usar_prefixos = usar_prefixos

    def vetorizar_trechos(self, textos: list[str]) -> list[list[float]]:
        if self._usar_prefixos:
            textos = [f"search_document: {t}" for t in textos]
        return self._embeddings.embed_documents(textos)

    def vetorizar_pergunta(self, pergunta: str) -> list[float]:
        if self._usar_prefixos:
            pergunta = f"search_query: {pergunta}"
        return self._embeddings.embed_query(pergunta)


def criar_vetorizador(config: Configuracoes) -> Vetorizador:
    embeddings = OllamaEmbeddings(model=config.modelo_embeddings, base_url=config.ollama_url)
    return Vetorizador(embeddings, usar_prefixos=config.modelo_embeddings.startswith("nomic-embed"))


def criar_chat(config: Configuracoes) -> BaseChatModel:
    # Temperatura baixa: a resposta deve sair do texto do documento, e nao
    # da criatividade do modelo.
    return ChatOllama(model=config.modelo_chat, base_url=config.ollama_url, temperature=0.1)

"""Contratos de entrada e saida da API (validados pelo Pydantic)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from oraculo.modelos import StatusDocumento


class Cadastro(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    # Limite superior: o Argon2 processa a senha inteira, e uma senha de
    # megabytes faria cada login custar caro (negacao de servico).
    senha: str = Field(min_length=8, max_length=128)


class Login(BaseModel):
    email: EmailStr
    senha: str = Field(max_length=128)


class ConfirmacaoSenha(BaseModel):
    senha: str = Field(max_length=128)


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str


class DocumentoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome_arquivo: str
    tamanho_bytes: int
    paginas: int | None
    status: StatusDocumento
    erro: str | None
    criado_em: datetime


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=1000)
    # Vazio: pesquisa em todos os documentos do usuario.
    documento_ids: list[uuid.UUID] | None = Field(default=None, max_length=50)


class FonteSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    indice: int
    documento_id: uuid.UUID
    nome_arquivo: str
    pagina: int
    texto: str
    similaridade: float


class Resposta(BaseModel):
    resposta: str
    fontes: list[FonteSaida]

# Build em dois estagios: o uv e o cache de download ficam no primeiro; a
# imagem final leva so o ambiente virtual pronto e o codigo.

FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
WORKDIR /app
# Compila para bytecode no build, e nao na primeira requisicao.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# So o pyproject e o lock primeiro: se as dependencias nao mudaram, o Docker
# reaproveita esta camada e o build pula a instalacao inteira.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

FROM python:3.14-slim
WORKDIR /app
# Usuario sem privilegio: se alguem escapar da aplicacao, nao e root.
RUN useradd --system --uid 1001 oraculo
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
COPY alembic.ini ./
COPY migracoes ./migracoes
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER oraculo
EXPOSE 8000
# As migracoes rodam antes da API subir. Se falharem, o container para e a
# API nunca atende com o schema desatualizado.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn oraculo.main:app_padrao --factory --host 0.0.0.0 --port 8000"]

"""Avalia a busca do RAG com perguntas de resposta conhecida.

Para cada tamanho de trecho, mede se a pagina certa aparece em 1o lugar
(acerto@1) ou entre as 3 primeiras (acerto@3), e compara a nota das
perguntas do edital com a das perguntas sem relacao com ele. Os valores
padrao de config.py sairam desta avaliacao.

Roda dentro da imagem da API, usando o Ollama do docker compose:

    docker compose run --rm -T --no-deps -v ./docs:/docs:ro \\
        --entrypoint python api - < backend/avaliacao/avaliar_busca.py
"""

import math
import os
from pathlib import Path

from langchain_ollama import OllamaEmbeddings

from oraculo.ia import Vetorizador
from oraculo.ingestao import extrair_trechos

PDF = Path("/docs/exemplos/edital-exemplo.pdf")

# (pergunta, pagina onde esta a resposta)
PERGUNTAS = [
    ("Qual o prazo de inscrição?", 2),
    ("Quanto ganha um Analista de Sistemas?", 1),
    ("Quantas vagas há para Técnico em Informática?", 1),
    ("O trabalho pode ser remoto?", 1),
    ("Qual o valor da taxa de inscrição para técnico?", 2),
    ("Quem tem direito à isenção da taxa?", 2),
    ("Quando será a prova objetiva?", 3),
    ("Quantas questões tem a prova?", 3),
    ("Qual a nota mínima para não ser eliminado?", 3),
    ("Quando sai o resultado final?", 4),
    ("Por quanto tempo o concurso é válido?", 4),
    ("Qual o prazo para recorrer do gabarito?", 4),
]

SEM_RELACAO = [
    "Qual a receita de bolo de cenoura?",
    "Quem ganhou a Copa do Mundo de 2002?",
    "Como trocar o óleo do carro?",
    "Qual a capital da Austrália?",
]

CONFIGURACOES = [(1000, 150), (500, 80), (400, 60), (300, 50)]

Ranking = list[tuple[float, int]]  # (similaridade, pagina), da maior para a menor


def cosseno(a: list[float], b: list[float]) -> float:
    produto = sum(x * y for x, y in zip(a, b, strict=True))
    return produto / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def destaque(ranking: Ranking) -> float:
    """Quanto o melhor trecho se separa da media de todos."""
    return ranking[0][0] - sum(s for s, _ in ranking) / len(ranking)


def avaliar(vetorizador: Vetorizador, conteudo: bytes, tamanho: int, sobreposicao: int) -> None:
    _, trechos = extrair_trechos(conteudo, tamanho, sobreposicao)
    vetores = vetorizador.vetorizar_trechos([t.texto for t in trechos])
    paginas = [t.pagina for t in trechos]

    def ranking(pergunta: str) -> Ranking:
        q = vetorizador.vetorizar_pergunta(pergunta)
        return sorted(
            ((cosseno(q, v), p) for v, p in zip(vetores, paginas, strict=True)), reverse=True
        )

    acerto1 = acerto3 = 0
    notas_certas: list[float] = []
    destaques_certos: list[float] = []
    for pergunta, pagina in PERGUNTAS:
        r = ranking(pergunta)
        acerto1 += r[0][1] == pagina
        acerto3 += pagina in [p for _, p in r[:3]]
        notas_certas.append(next(s for s, p in r if p == pagina))
        destaques_certos.append(destaque(r))
    rankings_fora = [ranking(p) for p in SEM_RELACAO]
    notas_fora = [r[0][0] for r in rankings_fora]
    destaques_fora = [destaque(r) for r in rankings_fora]

    total = len(PERGUNTAS)
    media = sum(notas_certas) / total
    print(f"\n=== trecho {tamanho} / sobreposicao {sobreposicao}: {len(trechos)} trechos ===")
    print(f"acerto@1: {acerto1}/{total}   acerto@3: {acerto3}/{total}")
    print(f"nota do trecho certo: min {min(notas_certas):.3f}  media {media:.3f}")
    print(f"maior nota sem relacao: {max(notas_fora):.3f}")
    print(f"distancia (min certo - max sem relacao): {min(notas_certas) - max(notas_fora):+.3f}")
    print(
        f"destaque: edital min {min(destaques_certos):.3f} | sem relacao max "
        f"{max(destaques_fora):.3f} -> distancia {min(destaques_certos) - max(destaques_fora):+.3f}"
    )


def main() -> None:
    url = os.environ.get("ORACULO_OLLAMA_URL", "http://ollama:11434")
    embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=url)
    vetorizador = Vetorizador(embeddings, usar_prefixos=True)
    conteudo = PDF.read_bytes()
    for tamanho, sobreposicao in CONFIGURACOES:
        avaliar(vetorizador, conteudo, tamanho, sobreposicao)


main()

"""Metricas de negocio expostas em /metrics para o Prometheus.

As metricas HTTP (latencia e status por rota) vem do instrumentator no
main.py; aqui ficam as que so a aplicacao sabe contar.
"""

from prometheus_client import Counter, Histogram

PERGUNTAS = Counter(
    "oraculo_perguntas_total",
    "Perguntas recebidas, por resultado",
    ["resultado"],
)

TEMPO_RESPOSTA_IA = Histogram(
    "oraculo_tempo_resposta_ia_segundos",
    "Tempo do modelo de linguagem para gerar a resposta completa",
    # Em CPU de notebook a resposta leva de 30 s a 3 min; com GPU, segundos.
    # Os intervalos cobrem os dois casos para o p95 nao ficar estourado no ultimo.
    buckets=(1, 2, 5, 10, 20, 40, 60, 90, 120, 180, 300),
)

DOCUMENTOS_PROCESSADOS = Counter(
    "oraculo_documentos_processados_total",
    "Documentos processados, por status final",
    ["status"],
)

# Cria cada serie com valor 0 ao subir a API. Sem isto, uma serie so passa a
# existir no primeiro evento: o painel mostra "No data" para o que ainda nao
# aconteceu, e o increase() ignora esse primeiro evento, porque nao tem uma
# medicao anterior para comparar.
for _resultado in ("respondida", "sem_contexto", "erro"):
    PERGUNTAS.labels(resultado=_resultado)
for _status in ("pronto", "erro"):
    DOCUMENTOS_PROCESSADOS.labels(status=_status)

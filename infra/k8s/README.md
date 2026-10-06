# Kubernetes

Manifestos para rodar o Oráculo num cluster (Docker Desktop, kind, minikube ou nuvem), organizados com **Kustomize**.

| Arquivo | O que sobe |
|---|---|
| `postgres.yaml` | Postgres + pgvector (StatefulSet com volume próprio) |
| `redis.yaml` | Redis para o limite de uso |
| `ollama.yaml` | Ollama; um initContainer baixa os modelos antes de atender |
| `api.yaml` | API (2 réplicas), autoscaling por CPU (HPA) e PodDisruptionBudget |
| `web.yaml` | nginx com a interface (2 réplicas) |
| `ingress.yaml` | Entrada pelo ingress-nginx em `oraculo.local` |
| `network-policies.yaml` | Tudo bloqueado por padrão; só os caminhos necessários liberados |

Todos os pods rodam **sem root**, com o disco do container **somente leitura** quando a imagem permite, e sem privilégios extras (`capabilities: drop ALL`). O namespace aplica o perfil `restricted` do Pod Security Standards, que recusa pods fora dessas regras.

## Subindo

```bash
# 1. Namespace e segredos (os segredos nunca vão para o repositório)
kubectl create namespace oraculo
kubectl -n oraculo create secret generic oraculo-segredos \
  --from-literal=DB_PASSWORD="$(openssl rand -hex 24)" \
  --from-literal=ORACULO_JWT_SECRET="$(openssl rand -base64 48)"

# 2. Todo o resto
kubectl apply -k infra/k8s

# 3. Acompanhar (o Ollama demora na primeira vez: baixa ~2,3 GB de modelos)
kubectl -n oraculo get pods -w
```

Para abrir no navegador, aponte `oraculo.local` para o IP do Ingress no arquivo `hosts`. Sem Ingress instalado, use `kubectl -n oraculo port-forward svc/web 8080:8080` e abra http://localhost:8080.

## Antes de expor na internet

- **HTTPS é obrigatório.** O cookie de sessão é `Secure` e só viaja por HTTPS. O `ingress.yaml` já pede o certificado ao [cert-manager](https://cert-manager.io); sem ele, crie o Secret `oraculo-tls` com o seu certificado.
- **IP real do cliente.** Atrás do Ingress, o nginx do pod `web` vê o IP do controlador, e não o do usuário. Os limites por IP (login e cadastro) passariam a valer para todos juntos. Configure `set_real_ip_from` com a faixa de IPs do controlador no `nginx.conf` para o nginx usar o `X-Forwarded-For` que vem dele.
- **Controlador de Ingress mantido.** O ingress-nginx foi aposentado em 2026 e não recebe mais correções de segurança (veja o comentário em `ingress.yaml`).

## Conferindo os manifestos sem cluster

```bash
kubectl kustomize infra/k8s
```

O CI faz isso e ainda valida cada recurso contra o schema oficial do Kubernetes com o [kubeconform](https://github.com/yannh/kubeconform).

# Segurança

## Como relatar uma vulnerabilidade

**Não abra uma issue pública.** Use o relato privado do GitHub: aba **Security** do repositório → **Report a vulnerability**. Só os mantenedores veem o relato até a correção sair.

Inclua, se puder: o que encontrou, os passos para reproduzir e o impacto. Você recebe uma resposta assim que o relato for analisado.

## O que o projeto já faz

| Área | Proteção |
|---|---|
| Senhas | Argon2id; login com tempo constante, sem revelar quais e-mails têm conta |
| Sessão | JWT em cookie `httpOnly` + `Secure` + `SameSite=Strict`, restrito a `/api`; o JavaScript da página não lê o token |
| Força bruta | Limite por e-mail e por IP no login, por IP no cadastro (Redis) e no nginx |
| Dados de outros usuários | Filtro por usuário dentro da própria consulta vetorial; documento alheio responde 404 |
| Upload | Assinatura `%PDF-` conferida, tamanho, páginas e quantidade de documentos limitados, nome do arquivo sem caminho |
| Prompt injection | Trechos dos documentos vão como dado na mensagem de sistema, separados da pergunta |
| Vazamento em erro e log | 422 sem o valor digitado (a senha não volta na resposta); log sem texto de documento nem pergunta |
| LGPD | O usuário exclui a própria conta, com todos os documentos e vetores (art. 18, VI); a IA roda localmente e nada sai da máquina |
| Navegador | CSP, `nosniff`, `frame-ancestors 'none'`, `Permissions-Policy`, `Referrer-Policy` |
| Containers | Sem root, `no-new-privileges`, `cap_drop: ALL`, disco somente leitura; só a interface publica porta, e só em `127.0.0.1` |
| Kubernetes | Pod Security `restricted`, NetworkPolicy com tudo bloqueado por padrão, TLS no Ingress |
| Cadeia de suprimentos | Actions fixadas por SHA, token do CI com permissão mínima, osv-scanner bloqueando o merge, Dependabot semanal, lockfiles (`uv.lock`, `package-lock.json`) |
| Segredos | Só por variável de ambiente; `.env` no `.gitignore` e no `.dockerignore`; sem valor padrão no código |

## Limites conhecidos

- O token JWT não pode ser revogado antes de expirar (2 horas). "Sair" apaga o cookie do navegador, mas um token copiado antes continuaria válido até expirar.
- A CSP permite `'unsafe-inline'` em scripts, exigência do export estático do Next.js. O impacto de um XSS fica reduzido porque a sessão está num cookie `httpOnly`.
- O Redis da rede interna não tem senha: só a API alcança ele (rede do compose e NetworkPolicy no Kubernetes).

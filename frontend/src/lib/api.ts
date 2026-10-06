import { criarLeitorSSE } from "./sse";
import type { Documento, Fonte, Usuario } from "./tipos";

// Vazio em producao: o nginx serve a interface e a API no mesmo endereco.
// Em desenvolvimento, .env.development aponta para o uvicorn local.
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// A sessao fica num cookie httpOnly que este codigo nao consegue ler, de
// proposito: um script injetado na pagina tambem nao conseguiria. O navegador
// envia o cookie sozinho; "include" e para o desenvolvimento, em que a API
// esta em outra porta.
const CREDENCIAIS: RequestCredentials = "include";

// Nestas rotas, 401 quer dizer "senha errada", e nao "sessao expirou".
const ROTAS_DE_ENTRADA = ["/api/auth/login", "/api/auth/cadastro"];

export class ErroApi extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

function irParaEntrada() {
  // Recarga completa de proposito, e nao router.push: descarta da memoria
  // as conversas e documentos da sessao que acabou. Tambem e chamada fora
  // de componente (no 401 de requisitar), onde nao ha router.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign("/entrar");
}

export async function sair() {
  try {
    // So o servidor apaga um cookie httpOnly.
    await fetch(`${BASE}/api/auth/sair`, { method: "POST", credentials: CREDENCIAIS });
  } finally {
    irParaEntrada();
  }
}

async function mensagemDeErro(resposta: Response): Promise<string> {
  try {
    const corpo = await resposta.json();
    // 422 do FastAPI traz uma lista de erros de validacao; o resto, um texto.
    if (Array.isArray(corpo.detail)) return corpo.detail[0]?.msg ?? "Dados inválidos.";
    if (typeof corpo.detail === "string") return corpo.detail;
  } catch {
    // corpo nao era JSON (ex.: erro do nginx)
  }
  return "Algo deu errado. Tente de novo em instantes.";
}

async function requisitar(caminho: string, opcoes: RequestInit = {}): Promise<Response> {
  const resposta = await fetch(BASE + caminho, { ...opcoes, credentials: CREDENCIAIS });
  if (resposta.status === 401 && !ROTAS_DE_ENTRADA.includes(caminho)) {
    // Sessao expirada: volta para o login em vez de deixar a tela quebrada.
    irParaEntrada();
  }
  if (!resposta.ok) throw new ErroApi(resposta.status, await mensagemDeErro(resposta));
  return resposta;
}

function json(corpo: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  };
}

export async function cadastrar(nome: string, email: string, senha: string): Promise<Usuario> {
  return (await requisitar("/api/auth/cadastro", json({ nome, email, senha }))).json();
}

export async function entrar(email: string, senha: string): Promise<Usuario> {
  return (await requisitar("/api/auth/login", json({ email, senha }))).json();
}

export async function buscarUsuario(): Promise<Usuario> {
  return (await requisitar("/api/auth/eu")).json();
}

/** Apaga a conta, os documentos e os vetores. Pede a senha de novo. */
export async function excluirConta(senha: string) {
  await requisitar("/api/auth/excluir-conta", json({ senha }));
  irParaEntrada();
}

export async function listarDocumentos(): Promise<Documento[]> {
  return (await requisitar("/api/documentos")).json();
}

export async function enviarDocumento(arquivo: File): Promise<Documento> {
  const formulario = new FormData();
  formulario.append("arquivo", arquivo);
  return (await requisitar("/api/documentos", { method: "POST", body: formulario })).json();
}

export async function apagarDocumento(id: string) {
  await requisitar(`/api/documentos/${id}`, { method: "DELETE" });
}

type AoResponder = {
  aoReceberFontes: (fontes: Fonte[]) => void;
  aoReceberTexto: (texto: string) => void;
};

/** Faz a pergunta e entrega a resposta aos pedacos, conforme o modelo escreve. */
export async function perguntar(
  pergunta: string,
  documentoIds: string[],
  { aoReceberFontes, aoReceberTexto }: AoResponder,
  sinal: AbortSignal,
) {
  const resposta = await requisitar("/api/perguntas/stream", {
    ...json({ pergunta, documento_ids: documentoIds.length > 0 ? documentoIds : null }),
    signal: sinal,
  });
  if (!resposta.body) throw new ErroApi(500, "O navegador não recebeu a resposta.");

  let erro: string | null = null;
  const ler = criarLeitorSSE(({ evento, dados }) => {
    if (evento === "fontes") aoReceberFontes(JSON.parse(dados));
    else if (evento === "token") aoReceberTexto(JSON.parse(dados).texto);
    else if (evento === "erro") erro = JSON.parse(dados).mensagem;
  });

  const leitor = resposta.body.pipeThrough(new TextDecoderStream()).getReader();
  for (;;) {
    const { value, done } = await leitor.read();
    if (done) break;
    ler(value);
  }
  if (erro) throw new ErroApi(502, erro);
}

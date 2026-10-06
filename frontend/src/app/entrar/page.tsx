"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Logo } from "@/components/Logo";
import { cadastrar, entrar } from "@/lib/api";

export default function PaginaEntrar() {
  const router = useRouter();
  const [modo, setModo] = useState<"entrar" | "cadastrar">("entrar");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const dados = new FormData(evento.currentTarget);
    const email = String(dados.get("email"));
    const senha = String(dados.get("senha"));
    setErro(null);
    setEnviando(true);
    try {
      if (modo === "entrar") await entrar(email, senha);
      else await cadastrar(String(dados.get("nome")), email, senha);
      router.replace("/");
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível entrar.");
      setEnviando(false);
    }
  }

  const campo =
    "w-full rounded-lg border border-borda bg-fundo px-3 py-2.5 text-sm outline-none " +
    "placeholder:text-suave/60 focus:border-destaque focus:ring-2 focus:ring-destaque/30";

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <Logo tamanho={48} />
          <h1 className="text-2xl font-semibold tracking-tight">Oráculo</h1>
          <p className="text-sm text-suave">
            Envie seus PDFs e pergunte. A IA responde citando o documento e a página.
          </p>
        </div>

        <form onSubmit={enviar} className="space-y-4 rounded-2xl border border-borda bg-painel p-6">
          {modo === "cadastrar" && (
            <label className="block space-y-1.5">
              <span className="text-sm text-suave">Nome</span>
              <input name="nome" required minLength={2} maxLength={100} className={campo} />
            </label>
          )}
          <label className="block space-y-1.5">
            <span className="text-sm text-suave">E-mail</span>
            <input name="email" type="email" required autoComplete="email" className={campo} />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm text-suave">Senha</span>
            <input
              name="senha"
              type="password"
              required
              minLength={modo === "cadastrar" ? 8 : undefined}
              maxLength={128}
              autoComplete={modo === "entrar" ? "current-password" : "new-password"}
              className={campo}
            />
          </label>

          {erro && (
            <p role="alert" className="rounded-lg bg-perigo/10 px-3 py-2 text-sm text-perigo">
              {erro}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="w-full rounded-lg bg-destaque-forte py-2.5 text-sm font-medium transition hover:bg-destaque-forte/85 disabled:opacity-60"
          >
            {enviando ? "Aguarde…" : modo === "entrar" ? "Entrar" : "Criar conta"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-suave">
          {modo === "entrar" ? "Ainda não tem conta?" : "Já tem conta?"}{" "}
          <button
            type="button"
            onClick={() => {
              setModo(modo === "entrar" ? "cadastrar" : "entrar");
              setErro(null);
            }}
            className="font-medium text-destaque hover:underline"
          >
            {modo === "entrar" ? "Criar conta" : "Entrar"}
          </button>
        </p>
      </div>
    </main>
  );
}

"use client";

import { type FormEvent, useRef, useState } from "react";

import { excluirConta, sair } from "@/lib/api";
import type { Usuario } from "@/lib/tipos";

export function MenuConta({ usuario }: { usuario: Usuario }) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [excluindo, setExcluindo] = useState(false);

  async function confirmarExclusao(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro(null);
    setExcluindo(true);
    try {
      await excluirConta(String(new FormData(evento.currentTarget).get("senha")));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível excluir a conta.");
      setExcluindo(false);
    }
  }

  return (
    <div className="flex items-center gap-4 text-sm">
      <span className="hidden text-suave sm:inline">{usuario.nome}</span>
      <button
        type="button"
        onClick={() => dialogo.current?.showModal()}
        className="text-suave hover:text-perigo"
      >
        Excluir conta
      </button>
      <button type="button" onClick={() => void sair()} className="text-suave hover:text-texto">
        Sair
      </button>

      <dialog
        ref={dialogo}
        aria-labelledby="titulo-excluir"
        className="m-auto w-full max-w-sm rounded-2xl border border-borda bg-painel p-6 text-texto backdrop:bg-black/60"
      >
        <form onSubmit={confirmarExclusao} className="space-y-4">
          <h2 id="titulo-excluir" className="text-lg font-semibold">
            Excluir sua conta?
          </h2>
          <p className="text-sm text-suave">
            Sua conta, seus documentos e tudo o que foi extraído deles serão apagados de vez. Isso
            não pode ser desfeito.
          </p>
          <label className="block space-y-1.5">
            <span className="text-sm text-suave">Digite sua senha para confirmar</span>
            <input
              name="senha"
              type="password"
              required
              maxLength={128}
              autoComplete="current-password"
              className="w-full rounded-lg border border-borda bg-fundo px-3 py-2.5 text-sm outline-none focus:border-perigo focus:ring-2 focus:ring-perigo/30"
            />
          </label>
          {erro && (
            <p role="alert" className="rounded-lg bg-perigo/10 px-3 py-2 text-sm text-perigo">
              {erro}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => dialogo.current?.close()}
              className="rounded-lg border border-borda px-4 py-2 text-sm hover:bg-cartao"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={excluindo}
              className="rounded-lg bg-perigo px-4 py-2 text-sm font-medium text-fundo hover:bg-perigo/85 disabled:opacity-60"
            >
              {excluindo ? "Excluindo…" : "Excluir de vez"}
            </button>
          </div>
        </form>
      </dialog>
    </div>
  );
}

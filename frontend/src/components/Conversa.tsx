"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { perguntar } from "@/lib/api";
import type { Mensagem } from "@/lib/tipos";

import { RespostaComFontes } from "./RespostaComFontes";

const SUGESTOES = [
  "Resuma os pontos principais do documento.",
  "Quais são os prazos e datas importantes?",
  "Quais valores aparecem no documento?",
];

type Props = { documentoIds: string[]; temDocumentoPronto: boolean };

export function Conversa({ documentoIds, temDocumentoPronto }: Props) {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [texto, setTexto] = useState("");
  const [cancelar, setCancelar] = useState<AbortController | null>(null);
  const fimDaLista = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fimDaLista.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensagens]);

  function atualizarResposta(id: string, mudar: (m: Extract<Mensagem, { autor: "oraculo" }>) => Mensagem) {
    setMensagens((atuais) =>
      atuais.map((m) => (m.id === id && m.autor === "oraculo" ? mudar(m) : m)),
    );
  }

  async function enviar(pergunta: string) {
    pergunta = pergunta.trim();
    if (pergunta.length < 3 || cancelar) return;

    const idResposta = crypto.randomUUID();
    setMensagens((atuais) => [
      ...atuais,
      { id: crypto.randomUUID(), autor: "usuario", texto: pergunta },
      { id: idResposta, autor: "oraculo", texto: "", fontes: [], estado: "escrevendo" },
    ]);
    setTexto("");

    const controle = new AbortController();
    setCancelar(controle);
    try {
      await perguntar(
        pergunta,
        documentoIds,
        {
          aoReceberFontes: (fontes) => atualizarResposta(idResposta, (m) => ({ ...m, fontes })),
          aoReceberTexto: (parte) =>
            atualizarResposta(idResposta, (m) => ({ ...m, texto: m.texto + parte })),
        },
        controle.signal,
      );
      atualizarResposta(idResposta, (m) => ({ ...m, estado: "pronta" }));
    } catch (e) {
      const parado = e instanceof DOMException && e.name === "AbortError";
      atualizarResposta(idResposta, (m) => ({
        ...m,
        estado: parado ? "pronta" : "erro",
        texto: parado
          ? m.texto + (m.texto ? " …" : "Resposta interrompida.")
          : e instanceof Error
            ? e.message
            : "Não foi possível responder.",
      }));
    } finally {
      setCancelar(null);
    }
  }

  function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    void enviar(texto);
  }

  return (
    <section aria-label="Conversa" className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-8">
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {mensagens.length === 0 && (
            <div className="mt-10 text-center md:mt-20">
              <h2 className="text-xl font-semibold">O que você quer saber?</h2>
              <p className="mt-2 text-sm text-suave">
                {temDocumentoPronto
                  ? "As respostas citam o documento e a página de onde vieram."
                  : "Comece enviando um PDF no painel ao lado."}
              </p>
              {temDocumentoPronto && (
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {SUGESTOES.map((sugestao) => (
                    <button
                      key={sugestao}
                      type="button"
                      onClick={() => void enviar(sugestao)}
                      className="rounded-full border border-borda bg-cartao px-3 py-1.5 text-sm text-suave transition hover:border-destaque/60 hover:text-texto"
                    >
                      {sugestao}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {mensagens.map((mensagem) =>
            mensagem.autor === "usuario" ? (
              <div
                key={mensagem.id}
                className="max-w-[85%] self-end rounded-2xl rounded-br-sm bg-destaque-forte/90 px-4 py-2.5"
              >
                {mensagem.texto}
              </div>
            ) : (
              <div
                key={mensagem.id}
                className="rounded-2xl rounded-bl-sm border border-borda bg-painel px-4 py-3"
              >
                <RespostaComFontes mensagem={mensagem} />
              </div>
            ),
          )}
          <div ref={fimDaLista} />
        </div>
      </div>

      <form onSubmit={aoEnviar} className="border-t border-borda bg-painel/60 px-4 py-4 md:px-8">
        <div className="mx-auto flex max-w-3xl gap-2">
          <label htmlFor="pergunta" className="sr-only">
            Sua pergunta
          </label>
          <input
            id="pergunta"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder={
              documentoIds.length > 0
                ? `Pergunte sobre ${documentoIds.length} documento(s) selecionado(s)…`
                : "Pergunte sobre seus documentos…"
            }
            maxLength={1000}
            disabled={!temDocumentoPronto}
            className="min-w-0 flex-1 rounded-xl border border-borda bg-fundo px-4 py-3 text-sm outline-none placeholder:text-suave/60 focus:border-destaque focus:ring-2 focus:ring-destaque/30 disabled:opacity-50"
          />
          {cancelar ? (
            <button
              type="button"
              onClick={() => cancelar.abort()}
              className="rounded-xl border border-borda px-4 text-sm font-medium hover:bg-cartao"
            >
              Parar
            </button>
          ) : (
            <button
              type="submit"
              disabled={texto.trim().length < 3}
              className="rounded-xl bg-destaque-forte px-5 text-sm font-medium transition hover:bg-destaque-forte/85 disabled:opacity-40"
            >
              Perguntar
            </button>
          )}
        </div>
      </form>
    </section>
  );
}

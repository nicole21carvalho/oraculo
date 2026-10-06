"use client";

import { useState } from "react";

import { separarCitacoes } from "@/lib/citacoes";
import type { Fonte, Mensagem } from "@/lib/tipos";

type Props = { mensagem: Extract<Mensagem, { autor: "oraculo" }> };

export function RespostaComFontes({ mensagem }: Props) {
  const [aberta, setAberta] = useState<number | null>(null);
  const segmentos = separarCitacoes(mensagem.texto, mensagem.fontes.length);

  return (
    <div className="space-y-3">
      <p
        className={`whitespace-pre-wrap leading-relaxed ${
          mensagem.estado === "escrevendo" ? "cursor-escrevendo" : ""
        } ${mensagem.estado === "erro" ? "text-perigo" : ""}`}
      >
        {segmentos.map((segmento, i) =>
          segmento.tipo === "texto" ? (
            <span key={i}>{segmento.valor}</span>
          ) : (
            <button
              key={i}
              type="button"
              onClick={() => setAberta(aberta === segmento.indice ? null : segmento.indice)}
              aria-label={`Ver fonte ${segmento.indice}`}
              className="mx-0.5 inline-flex h-5 min-w-5 -translate-y-0.5 items-center justify-center rounded bg-destaque/20 px-1 align-middle text-[11px] font-semibold text-destaque transition hover:bg-destaque/35"
            >
              {segmento.indice}
            </button>
          ),
        )}
      </p>

      {mensagem.fontes.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {mensagem.fontes.map((fonte) => (
            <CartaoFonte
              key={fonte.indice}
              fonte={fonte}
              aberta={aberta === fonte.indice}
              aoAlternar={() => setAberta(aberta === fonte.indice ? null : fonte.indice)}
            />
          ))}
        </div>
      )}
      {aberta !== null && (
        <blockquote className="rounded-lg border-l-2 border-destaque bg-fundo/60 px-4 py-3 text-sm text-suave">
          <p className="mb-1 text-xs font-medium text-destaque">
            [{aberta}] {mensagem.fontes[aberta - 1].nome_arquivo}, página{" "}
            {mensagem.fontes[aberta - 1].pagina}
          </p>
          <p className="whitespace-pre-wrap">{mensagem.fontes[aberta - 1].texto}</p>
        </blockquote>
      )}
    </div>
  );
}

function CartaoFonte({
  fonte,
  aberta,
  aoAlternar,
}: {
  fonte: Fonte;
  aberta: boolean;
  aoAlternar: () => void;
}) {
  return (
    <button
      type="button"
      onClick={aoAlternar}
      aria-expanded={aberta}
      className={`flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs transition ${
        aberta ? "border-destaque bg-destaque/10" : "border-borda bg-cartao hover:border-destaque/50"
      }`}
    >
      <span className="font-semibold text-destaque">[{fonte.indice}]</span>
      <span className="max-w-40 truncate">{fonte.nome_arquivo}</span>
      <span className="text-suave">p. {fonte.pagina}</span>
      <span className="text-suave/70" title="Similaridade com a pergunta">
        {Math.round(fonte.similaridade * 100)}%
      </span>
    </button>
  );
}

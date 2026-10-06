"use client";

import { type DragEvent, useRef, useState } from "react";

import { apagarDocumento, enviarDocumento } from "@/lib/api";
import type { Documento } from "@/lib/tipos";

type Props = {
  documentos: Documento[];
  selecionados: Set<string>;
  aoAlternar: (id: string) => void;
  aoMudar: () => void;
};

const ROTULO_STATUS = {
  processando: { texto: "Lendo…", cor: "text-alerta bg-alerta/10" },
  pronto: { texto: "Pronto", cor: "text-sucesso bg-sucesso/10" },
  erro: { texto: "Erro", cor: "text-perigo bg-perigo/10" },
} as const;

function tamanhoLegivel(bytes: number) {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function PainelDocumentos({ documentos, selecionados, aoAlternar, aoMudar }: Props) {
  const entrada = useRef<HTMLInputElement>(null);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(0);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(arquivos: FileList | null) {
    if (!arquivos?.length) return;
    setErro(null);
    for (const arquivo of Array.from(arquivos)) {
      setEnviando((n) => n + 1);
      try {
        await enviarDocumento(arquivo);
      } catch (e) {
        setErro(`${arquivo.name}: ${e instanceof Error ? e.message : "falha no envio"}`);
      } finally {
        setEnviando((n) => n - 1);
        aoMudar();
      }
    }
  }

  function soltar(evento: DragEvent) {
    evento.preventDefault();
    setArrastando(false);
    void enviar(evento.dataTransfer.files);
  }

  async function apagar(documento: Documento) {
    if (!window.confirm(`Apagar "${documento.nome_arquivo}"? As respostas deixam de usá-lo.`)) {
      return;
    }
    await apagarDocumento(documento.id);
    aoMudar();
  }

  return (
    <section aria-labelledby="titulo-documentos" className="flex min-h-0 flex-col gap-4">
      <div className="flex items-baseline justify-between">
        <h2 id="titulo-documentos" className="text-sm font-semibold uppercase tracking-wide text-suave">
          Documentos
        </h2>
        {selecionados.size > 0 && (
          <span className="text-xs text-destaque">{selecionados.size} selecionado(s)</span>
        )}
      </div>

      <button
        type="button"
        onClick={() => entrada.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setArrastando(true);
        }}
        onDragLeave={() => setArrastando(false)}
        onDrop={soltar}
        className={`rounded-xl border-2 border-dashed px-4 py-6 text-center transition ${
          arrastando
            ? "border-destaque bg-destaque/10"
            : "border-borda hover:border-destaque/60 hover:bg-cartao"
        }`}
      >
        <span className="block text-sm font-medium">
          {enviando > 0 ? "Enviando…" : "Arraste PDFs aqui"}
        </span>
        <span className="mt-1 block text-xs text-suave">ou clique para escolher (até 20 MB)</span>
      </button>
      <input
        ref={entrada}
        type="file"
        accept="application/pdf"
        multiple
        hidden
        onChange={(e) => {
          void enviar(e.target.files);
          e.target.value = "";
        }}
      />

      {erro && (
        <p role="alert" className="rounded-lg bg-perigo/10 px-3 py-2 text-xs text-perigo">
          {erro}
        </p>
      )}

      <ul className="-mx-1 flex min-h-0 flex-col gap-1 overflow-y-auto px-1">
        {documentos.length === 0 && (
          <li className="py-4 text-center text-sm text-suave">Nenhum documento ainda.</li>
        )}
        {documentos.map((documento) => {
          const status = ROTULO_STATUS[documento.status];
          const pronto = documento.status === "pronto";
          return (
            <li
              key={documento.id}
              className="group flex items-start gap-3 rounded-lg px-2 py-2 hover:bg-cartao"
            >
              <input
                type="checkbox"
                aria-label={`Perguntar só sobre ${documento.nome_arquivo}`}
                disabled={!pronto}
                checked={selecionados.has(documento.id)}
                onChange={() => aoAlternar(documento.id)}
                className="mt-1 accent-destaque-forte"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm" title={documento.nome_arquivo}>
                  {documento.nome_arquivo}
                </p>
                <p className="mt-0.5 flex items-center gap-2 text-xs text-suave">
                  <span className={`rounded px-1.5 py-0.5 font-medium ${status.cor}`}>
                    {status.texto}
                  </span>
                  {documento.paginas && <span>{documento.paginas} pág.</span>}
                  <span>{tamanhoLegivel(documento.tamanho_bytes)}</span>
                </p>
                {documento.erro && <p className="mt-1 text-xs text-perigo">{documento.erro}</p>}
              </div>
              <button
                type="button"
                onClick={() => void apagar(documento)}
                aria-label={`Apagar ${documento.nome_arquivo}`}
                className="rounded p-1 text-suave opacity-0 transition hover:text-perigo focus:opacity-100 group-hover:opacity-100"
              >
                ✕
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

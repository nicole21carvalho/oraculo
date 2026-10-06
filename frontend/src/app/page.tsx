"use client";

import { useCallback, useEffect, useState } from "react";

import { Conversa } from "@/components/Conversa";
import { Logo } from "@/components/Logo";
import { MenuConta } from "@/components/MenuConta";
import { PainelDocumentos } from "@/components/PainelDocumentos";
import { buscarUsuario, listarDocumentos } from "@/lib/api";
import type { Documento, Usuario } from "@/lib/tipos";

export default function PaginaInicial() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [documentos, setDocumentos] = useState<Documento[]>([]);
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set());

  const recarregar = useCallback(async () => {
    setDocumentos(await listarDocumentos());
  }, []);

  useEffect(() => {
    // Sem sessao, a API responde 401 e requisitar() leva para /entrar.
    buscarUsuario()
      .then((u) => {
        setUsuario(u);
        return listarDocumentos();
      })
      .then(setDocumentos)
      .catch(() => {});
  }, []);

  // Enquanto algum PDF estiver sendo lido, consulta o status a cada 2 s.
  const processando = documentos.some((d) => d.status === "processando");
  useEffect(() => {
    if (!processando) return;
    const intervalo = setInterval(() => void recarregar(), 2000);
    return () => clearInterval(intervalo);
  }, [processando, recarregar]);

  function alternar(id: string) {
    setSelecionados((atuais) => {
      const novos = new Set(atuais);
      if (novos.has(id)) novos.delete(id);
      else novos.add(id);
      return novos;
    });
  }

  if (!usuario) {
    return <div className="flex min-h-screen items-center justify-center text-suave">Carregando…</div>;
  }

  const prontos = new Set(documentos.filter((d) => d.status === "pronto").map((d) => d.id));

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-borda px-4 py-3 md:px-6">
        <div className="flex items-center gap-2.5">
          <Logo />
          <span className="text-lg font-semibold tracking-tight">Oráculo</span>
        </div>
        <MenuConta usuario={usuario} />
      </header>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <aside className="max-h-[40vh] border-b border-borda bg-painel p-4 md:max-h-none md:w-80 md:shrink-0 md:border-r md:border-b-0">
          <PainelDocumentos
            documentos={documentos}
            selecionados={selecionados}
            aoAlternar={alternar}
            aoMudar={() => void recarregar()}
          />
        </aside>
        <Conversa
          // Documento apagado sai da selecao sem precisar desmarcar.
          documentoIds={[...selecionados].filter((id) => prontos.has(id))}
          temDocumentoPronto={prontos.size > 0}
        />
      </div>
    </div>
  );
}

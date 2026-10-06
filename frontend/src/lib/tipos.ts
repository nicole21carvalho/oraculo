export type Usuario = { id: number; nome: string; email: string };

export type StatusDocumento = "processando" | "pronto" | "erro";

export type Documento = {
  id: string;
  nome_arquivo: string;
  tamanho_bytes: number;
  paginas: number | null;
  status: StatusDocumento;
  erro: string | null;
  criado_em: string;
};

export type Fonte = {
  indice: number;
  documento_id: string;
  nome_arquivo: string;
  pagina: number;
  texto: string;
  similaridade: number;
};

export type Mensagem =
  | { id: string; autor: "usuario"; texto: string }
  | {
      id: string;
      autor: "oraculo";
      texto: string;
      fontes: Fonte[];
      estado: "escrevendo" | "pronta" | "erro";
    };

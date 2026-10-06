import { describe, expect, it } from "vitest";

import { criarLeitorSSE, type EventoSSE } from "./sse";

function ler(pedacos: string[]) {
  const eventos: EventoSSE[] = [];
  const leitor = criarLeitorSSE((e) => eventos.push(e));
  pedacos.forEach(leitor);
  return eventos;
}

describe("criarLeitorSSE", () => {
  it("le varios eventos que chegam no mesmo pedaco", () => {
    const eventos = ler(['event: token\ndata: {"texto":"Ol"}\n\nevent: token\ndata: {"texto":"á"}\n\n']);

    expect(eventos).toEqual([
      { evento: "token", dados: '{"texto":"Ol"}' },
      { evento: "token", dados: '{"texto":"á"}' },
    ]);
  });

  it("junta um evento que chegou quebrado entre dois pedacos", () => {
    const eventos = ler(["event: fon", 'tes\ndata: [{"pag', 'ina":2}]\n', "\n"]);

    expect(eventos).toEqual([{ evento: "fontes", dados: '[{"pagina":2}]' }]);
  });

  it("nao entrega bloco incompleto", () => {
    expect(ler(["event: fim\ndata: {}\n"])).toEqual([]);
  });

  it("usa 'message' quando o evento nao tem nome", () => {
    expect(ler(["data: oi\n\n"])).toEqual([{ evento: "message", dados: "oi" }]);
  });
});

import { describe, expect, it } from "vitest";

import { separarCitacoes } from "./citacoes";

describe("separarCitacoes", () => {
  it("separa texto e citacoes, inclusive seguidas", () => {
    expect(separarCitacoes("O prazo e 5/12 [1][2].", 2)).toEqual([
      { tipo: "texto", valor: "O prazo e 5/12 " },
      { tipo: "citacao", indice: 1 },
      { tipo: "citacao", indice: 2 },
      { tipo: "texto", valor: "." },
    ]);
  });

  it("mantem como texto a citacao de uma fonte que nao existe", () => {
    expect(separarCitacoes("Valor de 10 [7].", 3)).toEqual([
      { tipo: "texto", valor: "Valor de 10 [7]." },
    ]);
  });

  it("devolve vazio para texto vazio", () => {
    expect(separarCitacoes("", 0)).toEqual([]);
  });
});

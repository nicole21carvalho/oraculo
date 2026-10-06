import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { RespostaComFontes } from "./RespostaComFontes";

const fonte = {
  indice: 1,
  documento_id: "d1",
  nome_arquivo: "edital.pdf",
  pagina: 2,
  texto: "O prazo de inscricao vai ate 5 de dezembro.",
  similaridade: 0.83,
};

describe("RespostaComFontes", () => {
  it("mostra o trecho original ao clicar na citacao", async () => {
    render(
      <RespostaComFontes
        mensagem={{
          id: "1",
          autor: "oraculo",
          texto: "Termina em 5 de dezembro [1].",
          fontes: [fonte],
          estado: "pronta",
        }}
      />,
    );

    expect(screen.queryByText(fonte.texto)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Ver fonte 1" }));

    expect(screen.getByText(fonte.texto)).toBeTruthy();
    expect(screen.getByText(/edital\.pdf, página 2/)).toBeTruthy();
  });
});

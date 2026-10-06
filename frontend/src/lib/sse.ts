export type EventoSSE = { evento: string; dados: string };

/**
 * Le Server-Sent Events a partir de pedacos de texto.
 *
 * O EventSource do navegador so faz GET e nao aceita cabecalho de
 * autorizacao, entao a resposta vem por fetch e e lida aqui. Um evento pode
 * chegar quebrado entre dois pedacos da rede: o que sobra fica guardado ate
 * o proximo pedaco completar o bloco.
 */
export function criarLeitorSSE(aoReceber: (evento: EventoSSE) => void) {
  let resto = "";

  return (pedaco: string) => {
    resto += pedaco;
    let fim = resto.indexOf("\n\n");
    while (fim !== -1) {
      const bloco = resto.slice(0, fim);
      resto = resto.slice(fim + 2);

      let evento = "message";
      const linhas: string[] = [];
      for (const linha of bloco.split("\n")) {
        if (linha.startsWith("event:")) evento = linha.slice(6).trim();
        else if (linha.startsWith("data:")) linhas.push(linha.slice(5).replace(/^ /, ""));
      }
      if (linhas.length > 0) aoReceber({ evento, dados: linhas.join("\n") });

      fim = resto.indexOf("\n\n");
    }
  };
}

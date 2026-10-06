export type Segmento = { tipo: "texto"; valor: string } | { tipo: "citacao"; indice: number };

/**
 * Separa a resposta do modelo em texto e marcas de citacao ([1], [2]...).
 *
 * So vira citacao o numero que corresponde a uma fonte de verdade: se o
 * modelo inventar um [7] com cinco fontes, ele aparece como texto comum, e
 * nao como um link para uma fonte que nao existe.
 */
export function separarCitacoes(texto: string, totalFontes: number): Segmento[] {
  const segmentos: Segmento[] = [];
  let ultimo = 0;

  for (const marca of texto.matchAll(/\[(\d{1,2})\]/g)) {
    const indice = Number(marca[1]);
    if (indice < 1 || indice > totalFontes) continue;
    if (marca.index > ultimo) {
      segmentos.push({ tipo: "texto", valor: texto.slice(ultimo, marca.index) });
    }
    segmentos.push({ tipo: "citacao", indice });
    ultimo = marca.index + marca[0].length;
  }
  if (ultimo < texto.length) segmentos.push({ tipo: "texto", valor: texto.slice(ultimo) });
  return segmentos;
}

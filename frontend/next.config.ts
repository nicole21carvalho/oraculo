import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A interface roda inteira no navegador, entao vira arquivos estaticos que
  // o nginx serve. Em producao nao ha servidor Node: menos memoria, menos
  // coisa para atualizar e nenhuma superficie de ataque do lado do servidor.
  output: "export",
  trailingSlash: true,
};

export default nextConfig;

/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Os testes simulam um usuário em Brasília, qualquer que seja o fuso da máquina (o CI do GitHub roda em UTC).
// Definido aqui, antes de o Vitest criar os processos de teste, para que eles herdem o fuso.
process.env.TZ = "America/Sao_Paulo";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  test: { env: { TZ: "America/Sao_Paulo" } },
});

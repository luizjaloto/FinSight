import { describe, expect, it } from "vitest";
// @ts-expect-error script ESM sem arquivo de declaração dedicado
import { verificarContrastes } from "../scripts/contraste.mjs";

describe("contraste WCAG 2.1 AA", () => {
  it("mantém todos os pares de cores acima do mínimo exigido", () => {
    const resultados = verificarContrastes() as { alvo: string; razao: number; min: number; aprovado: boolean }[];
    const reprovados = resultados.filter((r) => !r.aprovado);
    expect(reprovados).toEqual([]);
  });
});

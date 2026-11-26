import { describe, expect, it } from "vitest";
import { compareText, parseBR, pct } from "./format";

describe("formatação", () => {
  it("lê números no formato brasileiro", () => {
    expect(parseBR("1.234,56")).toBe(1234.56);
    expect(parseBR("105")).toBe(105);
    expect(parseBR("1,05")).toBe(1.05);
    expect(Number.isNaN(parseBR(""))).toBe(true);
  });

  // P0-1: ponto sem vírgula é milhar quando segue o padrão de milhar, senão é decimal.
  it.each([
    ["5.000", 5000],
    ["1.500", 1500],
    ["10.000", 10000],
    ["12.345.678", 12345678],
    ["5.000,00", 5000],
    ["0.5", 0.5],
    ["12.5", 12.5],
    ["1500", 1500],
  ])("lê \"%s\" como %s", (entrada, esperado) => {
    expect(parseBR(entrada)).toBe(esperado);
  });

  it("formata porcentagem com vírgula", () => {
    expect(pct(14.12)).toBe("14,12%");
  });

  it("explica a comparação com o CDI em linguagem simples", () => {
    expect(compareText(16, 14, "CDI")).toContain("a mais que o CDI");
    expect(compareText(10, 14, "CDI")).toContain("a menos que o CDI");
    expect(compareText(14.01, 14, "CDI")).toContain("praticamente o mesmo");
  });
});

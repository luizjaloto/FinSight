import { describe, expect, it } from "vitest";
import { bytesUtf8, forcaSenha, iniciais, semAcento } from "./format";

describe("ajudas da interface", () => {
  it("gera as iniciais do avatar", () => {
    expect(iniciais("Roberto Souza")).toBe("RS");
    expect(iniciais("Roberto (demonstração)")).toBe("RD");
    expect(iniciais("Ana")).toBe("AN");
    expect(iniciais("   ")).toBe("?");
  });

  it("busca sem diferenciar acentos", () => {
    expect(semAcento("Patrimônio")).toBe("patrimonio");
    expect(semAcento("Ações")).toBe("acoes");
  });

  it("mede a força da senha", () => {
    expect(forcaSenha("").nivel).toBe(0);
    expect(forcaSenha("curta").texto).toContain("8 caracteres");
    expect(forcaSenha("Senha-Forte-2026").nivel).toBe(4);
  });

  it("conta bytes como o servidor (acentos ocupam 2)", () => {
    expect(bytesUtf8("abc")).toBe(3);
    expect(bytesUtf8("é")).toBe(2);
  });
});

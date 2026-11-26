import { describe, expect, it } from "vitest";
import { traduzirErro } from "./api";

describe("mensagens de erro do servidor", () => {
  it("traduz os erros de validação mais comuns", () => {
    expect(traduzirErro("value is not a valid email address: The part after the @-sign is not valid.")).toBe(
      "E-mail inválido. Confira o endereço.",
    );
    expect(traduzirErro("String should have at least 2 characters")).toBe("Texto curto demais. Use pelo menos 2 caracteres.");
    expect(traduzirErro("Field required")).toBe("Preencha este campo.");
  });

  it("traduz a senha longa", () => {
    expect(traduzirErro("A senha pode ter no máximo 72 bytes: cerca de 72 letras sem acento.")).toBe(
      "Senha longa demais. Use até 72 caracteres (acentos e emojis contam mais).",
    );
  });

  it("mantém as mensagens que já estão em português", () => {
    expect(traduzirErro("E-mail ou senha incorretos.")).toBe("E-mail ou senha incorretos.");
  });
});

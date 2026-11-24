// Formatação no padrão brasileiro
export const brl = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const pct = (v: number, digits = 2) =>
  `${v.toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;

/** Converte "1.234,56" ou "1234.56" em número. Retorna NaN se não for número. */
export function parseBR(raw: string): number {
  const s = raw.trim().replace(/\s|R\$/g, "");
  if (!s) return NaN;
  return Number(s.includes(",") ? s.replace(/\./g, "").replace(",", ".") : s);
}

/** Frase simples comparando a carteira com uma referência. */
export function compareText(carteira: number, referencia: number, nome: string): string {
  const diff = carteira - referencia;
  if (Math.abs(diff) < 0.05) return `Sua carteira rendeu praticamente o mesmo que o ${nome}.`;
  return diff > 0
    ? `Sua carteira rendeu ${pct(diff)} a mais que o ${nome} no mesmo período.`
    : `Sua carteira rendeu ${pct(-diff)} a menos que o ${nome} no mesmo período.`;
}

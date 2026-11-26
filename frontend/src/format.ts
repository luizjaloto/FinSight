// Formatação no padrão brasileiro
export const brl = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const pct = (v: number, digits = 2) =>
  `${v.toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;

const MILHAR_SEM_VIRGULA = /^[1-9]\d{0,2}(\.\d{3})+$/;

/** Indica se o texto usa ponto de milhar sem vírgula decimal (ex.: "1.500", "10.000"). */
export function usaMilharSemVirgula(raw: string): boolean {
  const s = raw.trim().replace(/\s|R\$/g, "");
  return !s.includes(",") && MILHAR_SEM_VIRGULA.test(s);
}

/** Converte "1.234,56", "5.000" ou "0.5" em número. Retorna NaN se não for número. */
export function parseBR(raw: string): number {
  const s = raw.trim().replace(/\s|R\$/g, "");
  if (!s) return NaN;
  if (s.includes(",")) return Number(s.replace(/\./g, "").replace(",", "."));
  if (MILHAR_SEM_VIRGULA.test(s)) return Number(s.replace(/\./g, ""));
  return Number(s);
}

/** Diferença entre duas taxas é em pontos percentuais: "1,50 ponto percentual". */
const pontosPercentuais = (v: number) =>
  `${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ponto percentual`;

/** Frase simples comparando a carteira com uma referência. */
export function compareText(carteira: number, referencia: number, nome: string): string {
  const diff = carteira - referencia;
  if (Math.abs(diff) < 0.05) return `Sua carteira rendeu praticamente o mesmo que o ${nome}.`;
  return diff > 0
    ? `Sua carteira rendeu ${pontosPercentuais(diff)} a mais que o ${nome} no mesmo período.`
    : `Sua carteira rendeu ${pontosPercentuais(-diff)} a menos que o ${nome} no mesmo período.`;
}

/** Número com a palavra certa no singular ou no plural: "1 aplicação", "3 aplicações". */
export function plural(n: number, singular: string, plural: string): string {
  return `${n.toLocaleString("pt-BR")} ${n === 1 ? singular : plural}`;
}

/**
 * Data de hoje no fuso do usuário, no formato AAAA-MM-DD (B9).
 * Não usar toISOString(): ele converte para UTC e, depois das 21h em Brasília, devolve o dia seguinte.
 */
export function hojeLocal(agora: Date = new Date()): string {
  const d = String(agora.getDate()).padStart(2, "0");
  const m = String(agora.getMonth() + 1).padStart(2, "0");
  return `${agora.getFullYear()}-${m}-${d}`;
}

/** Iniciais para o avatar: "Roberto Souza" → "RS"; "Roberto (demonstração)" → "RD". */
export function iniciais(nome: string): string {
  const partes = nome.replace(/[()]/g, " ").trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "?";
  const letras = partes.length === 1 ? partes[0].slice(0, 2) : partes[0][0] + partes[partes.length - 1][0];
  return letras.toUpperCase();
}

/** Remove acentos para buscas: "Patrimônio" → "patrimonio". */
export function semAcento(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/** Força da senha de 0 a 4, para o medidor do cadastro (só orientação visual). */
export function forcaSenha(senha: string): { nivel: 0 | 1 | 2 | 3 | 4; texto: string } {
  if (!senha) return { nivel: 0, texto: "" };
  let pontos = 0;
  if (senha.length >= 8) pontos++;
  if (senha.length >= 12) pontos++;
  if (/[a-z]/.test(senha) && /[A-Z]/.test(senha)) pontos++;
  if (/\d/.test(senha) && /[^A-Za-z0-9]/.test(senha)) pontos++;
  const nivel = Math.min(pontos, 4) as 0 | 1 | 2 | 3 | 4;
  const textos = ["Muito fraca", "Fraca", "Razoável", "Boa", "Forte"];
  return { nivel, texto: senha.length < 8 ? "Use pelo menos 8 caracteres" : textos[nivel] };
}

/** Tamanho da senha em bytes (o servidor aceita até 72 bytes). */
export const bytesUtf8 = (s: string) => new TextEncoder().encode(s).length;

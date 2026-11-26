// Cliente da API do FinSight
const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export type AssetType = "renda_fixa" | "acao" | "fii";

export interface Asset {
  id: string;
  type: AssetType;
  name: string;
  ticker?: string | null;
  invested: number;
  start_date: string;
  indexer?: "cdi" | "ipca" | null;
  rate?: number | null;
  maturity?: string | null;
  quantity?: number | null;
  avg_price?: number | null;
}

export interface Alerta {
  kind: "concentracao" | "vencimento" | "vencido" | "cotacao" | "erro_calculo" | "indicadores";
  level: "atencao" | "info";
  title: string;
  text: string;
  why: string;
}

export interface Dashboard {
  patrimonio: number;
  investido: number;
  rentabilidade_pct: number;
  cdi_periodo_pct: number;
  ipca_periodo_pct: number;
  superou_cdi: boolean | null;
  superou_ipca: boolean | null;
  alocacao: { classe: string; valor: number; pct: number }[];
  ativos: (Asset & {
    current: number | null;
    return_pct: number | null;
    peso_pct: number | null;
    class_label: string;
    quote_missing: boolean;
    calc_error?: boolean; // B2: dados inválidos – fica fora dos totais
    status?: "ativo" | "vencido" | "erro"; // B4: renda fixa vencida para de render no vencimento
  })[];
  diversificacao: { score: number; band: string; text: string };
  alertas: Alerta[];
  indicadores_desatualizados?: boolean; // B3: CDI/IPCA vindos do cache porque o Banco Central não respondeu
  aviso: string;
}

export function getToken(): string | null {
  return localStorage.getItem("finsight_token");
}

export function setSession(token: string | null, name?: string) {
  if (token) {
    localStorage.setItem("finsight_token", token);
    if (name) localStorage.setItem("finsight_name", name);
  } else {
    localStorage.removeItem("finsight_token");
    localStorage.removeItem("finsight_name");
  }
}

/** Mensagens de validação do Pydantic chegam em inglês. Traduzimos as mais comuns; o resto segue como veio. */
const TRADUCOES: [RegExp, string | ((m: RegExpMatchArray) => string)][] = [
  [/72 bytes/, "Senha longa demais. Use até 72 caracteres (acentos e emojis contam mais)."],
  [/value is not a valid email address/i, "E-mail inválido. Confira o endereço."],
  [/string should have at least (\d+) characters?/i, (m) => `Texto curto demais. Use pelo menos ${m[1]} caracteres.`],
  [/string should have at most (\d+) characters?/i, (m) => `Texto longo demais. Use no máximo ${m[1]} caracteres.`],
  [/field required/i, "Preencha este campo."],
  [/input should be a valid (number|integer)|input should be a finite number/i, "Digite um número válido."],
  [/input should be a valid date/i, "Informe uma data válida."],
  [/input should be greater than 0/i, "O valor precisa ser maior que zero."],
];

export function traduzirErro(msg: string): string {
  for (const [padrao, texto] of TRADUCOES) {
    const m = msg.match(padrao);
    if (m) return typeof texto === "function" ? texto(m) : texto;
  }
  return msg;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.body && !(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new Error("Não conseguimos falar com o servidor. Confira sua internet e tente de novo.");
  }
  if (res.status === 401 && token) {
    setSession(null);
    window.location.href = "/login?expirou=1";
  }
  if (!res.ok) {
    let msg = "Algo deu errado. Tente novamente.";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") msg = traduzirErro(body.detail);
      else if (Array.isArray(body.detail))
        msg = body.detail.map((d: { msg: string }) => traduzirErro(d.msg.replace("Value error, ", ""))).join(" ");
    } catch {
      /* resposta sem corpo */
    }
    throw new Error(msg);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  register: (b: { name: string; email: string; password: string; accept_terms: boolean }) =>
    request<{ access_token: string; name: string }>("/auth/register", { method: "POST", body: JSON.stringify(b) }),
  login: (b: { email: string; password: string }) =>
    request<{ access_token: string; name: string }>("/auth/login", { method: "POST", body: JSON.stringify(b) }),
  deleteAccount: () => request<void>("/auth/me", { method: "DELETE" }),
  dashboard: () => request<Dashboard>("/dashboard"),
  portfolio: () => request<{ assets: Asset[] }>("/portfolio"),
  addAsset: (a: Omit<Asset, "id">) => request<Asset>("/portfolio/assets", { method: "POST", body: JSON.stringify(a) }),
  removeAsset: (id: string) => request<void>(`/portfolio/assets/${id}`, { method: "DELETE" }),
  importCsv: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ imported: number; rejected: { line: number | null; reason: string }[]; rate_pct: number }>("/portfolio/import-csv", {
      method: "POST",
      body: fd,
    });
  },
  glossary: () => request<{ termo: string; definicao: string }[]>("/glossario"),
  exportData: () => request<unknown>("/auth/me/export"),
};

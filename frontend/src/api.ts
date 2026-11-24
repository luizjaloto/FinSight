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
  kind: "concentracao" | "vencimento" | "cotacao";
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
  ativos: (Asset & { current: number; return_pct: number; peso_pct: number; class_label: string; quote_missing: boolean })[];
  diversificacao: { score: number; band: string; text: string };
  alertas: Alerta[];
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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.body && !(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (res.status === 401 && token) {
    setSession(null);
    window.location.href = "/login";
  }
  if (!res.ok) {
    let msg = "Algo deu errado. Tente novamente.";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") msg = body.detail;
      else if (Array.isArray(body.detail)) msg = body.detail.map((d: { msg: string }) => d.msg.replace("Value error, ", "")).join(" ");
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
};

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type AssetType, type Dashboard as D } from "../api";
import AlertCard from "../components/AlertCard";
import Help from "../components/Help";
import Icon, { type IconName } from "../components/Icon";
import { useToast } from "../components/Toast";
import { brl, compareText, pct } from "../format";

const CORES = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)"];
const ICONE_TIPO: Record<AssetType, IconName> = { renda_fixa: "predio", acao: "grafico", fii: "carteira" };
type Filtro = "todos" | AssetType;
const FILTROS: { id: Filtro; rotulo: string }[] = [
  { id: "todos", rotulo: "Todas" },
  { id: "renda_fixa", rotulo: "Renda fixa" },
  { id: "acao", rotulo: "Ações" },
  { id: "fii", rotulo: "FIIs" },
];

function Carregando() {
  return (
    <div className="grid" aria-busy="true" aria-label="Carregando o painel">
      <div className="skeleton span-12" style={{ minHeight: 220 }} />
      {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton span-3" />)}
      <div className="skeleton span-7" style={{ minHeight: 300 }} />
      <div className="skeleton span-5" style={{ minHeight: 300 }} />
    </div>
  );
}

function Vazio() {
  return (
    <div className="card empty">
      <span className="bubble b1"><Icon name="carteira" size={34} /></span>
      <h1>Sua carteira ainda está vazia</h1>
      <p className="muted">Cadastre suas aplicações ou importe o arquivo da B3 para ver quanto rendeu, comparado ao CDI e à inflação.</p>
      <div className="form-actions">
        <Link className="btn btn-primary" to="/carteira"><Icon name="mais" /> Cadastrar aplicação</Link>
        <Link className="btn btn-soft" to="/carteira?aba=importar"><Icon name="upload" /> Importar da B3</Link>
      </div>
    </div>
  );
}

function Stat({ icone, cor, rotulo, termo, valor, badge, texto, children }: {
  icone: IconName; cor: string; rotulo: string; termo: string; valor: string;
  badge?: { texto: string; tom: "good" | "bad" | "neutral" }; texto: string; children?: ReactNode;
}) {
  return (
    <section className="card stat span-3" aria-label={rotulo}>
      <div className="stat-top">
        <span>{rotulo} <Help termo={termo} /></span>
        <span className={`bubble ${cor}`}><Icon name={icone} /></span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <span className="stat-value">{valor}</span>
        {badge && <span className={`badge ${badge.tom}`}>{badge.texto}</span>}
      </div>
      {children}
      <span className="muted small">{texto}</span>
    </section>
  );
}

export default function Dashboard() {
  const [d, setD] = useState<D | null>(null);
  const [erro, setErro] = useState("");
  const [atualizando, setAtualizando] = useState(false);
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const [vista, setVista] = useState<"grafico" | "tabela">("grafico");
  const [ocultos, setOcultos] = useState<string[]>([]);
  const toast = useToast();
  const nome = (localStorage.getItem("finsight_name") ?? "").split(" ")[0];

  const carregar = useCallback(async (manual = false) => {
    setAtualizando(true);
    try {
      setD(await api.dashboard());
      setErro("");
      if (manual) toast("Painel atualizado com os dados mais recentes.");
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setAtualizando(false);
    }
  }, [toast]);

  useEffect(() => { carregar(); }, [carregar]);

  const ativos = useMemo(() => (d ? d.ativos.filter((a) => filtro === "todos" || a.type === filtro) : []), [d, filtro]);

  if (erro && !d)
    return (
      <div className="card empty" role="alert">
        <span className="bubble b2"><Icon name="alerta" size={34} /></span>
        <h1>Não foi possível carregar o painel</h1>
        <p className="muted">{erro}</p>
        <button className="btn btn-primary" onClick={() => carregar(true)}><Icon name="atualizar" /> Tentar de novo</button>
      </div>
    );
  if (!d) return <Carregando />;
  if (d.ativos.length === 0) return <Vazio />;

  const ganho = d.patrimonio - d.investido;
  const comparacao = [
    { nome: "Sua carteira", valor: d.rentabilidade_pct },
    { nome: "CDI", valor: d.cdi_periodo_pct },
    { nome: "Inflação (IPCA)", valor: d.ipca_periodo_pct },
  ];
  const alertas = d.alertas.filter((a) => !ocultos.includes(a.title));
  const vencendo = d.alertas.filter((a) => a.kind === "vencimento").length;

  return (
    <div className="grid">
      {/* destaque */}
      <section className="hero" aria-label="Resumo do patrimônio">
        <div>
          <p className="eyebrow"><Icon name="brilho" size={18} /> Olá{nome ? `, ${nome}` : ""}! Este é o resumo da sua carteira.</p>
          <h1>Patrimônio hoje</h1>
          <div className="hero-value">{brl(d.patrimonio)}</div>
          <div className="hero-sub">
            <span className="chip-hero">
              <Icon name={ganho >= 0 ? "sobe" : "desce"} size={16} /> {ganho >= 0 ? "+" : "−"}{brl(Math.abs(ganho))} ({pct(d.rentabilidade_pct)})
            </span>
            <span>sobre {brl(d.investido)} aplicados</span>
          </div>
        </div>
        <div className="hero-actions">
          <Link className="btn btn-white" to="/carteira"><Icon name="mais" /> Nova aplicação</Link>
          <Link className="btn btn-glass" to="/carteira?aba=importar"><Icon name="upload" /> Importar B3</Link>
          <button className="btn btn-glass" onClick={() => carregar(true)} disabled={atualizando}>
            <Icon name="atualizar" className={atualizando ? "spin" : ""} /> {atualizando ? "Atualizando…" : "Atualizar"}
          </button>
          <Link className="btn btn-glass" to="/glossario"><Icon name="livro" /> Glossário</Link>
        </div>
      </section>

      {/* indicadores */}
      <Stat icone="moeda" cor="b1" rotulo="Rendeu mais que o CDI?" termo="CDI" valor={d.superou_cdi ? "Sim" : "Não"}
            badge={{ texto: `${pct(d.rentabilidade_pct)} × ${pct(d.cdi_periodo_pct)}`, tom: d.superou_cdi ? "good" : "bad" }}
            texto={compareText(d.rentabilidade_pct, d.cdi_periodo_pct, "CDI")} />
      <Stat icone="escudo" cor="b3" rotulo="Ganhou da inflação?" termo="Inflação" valor={d.superou_ipca ? "Sim" : "Não"}
            badge={{ texto: `${pct(d.rentabilidade_pct)} × ${pct(d.ipca_periodo_pct)}`, tom: d.superou_ipca ? "good" : "bad" }}
            texto={compareText(d.rentabilidade_pct, d.ipca_periodo_pct, "IPCA")} />
      <Stat icone="pizza" cor="b4" rotulo="Diversificação" termo="Diversificação" valor={d.diversificacao.band}
            badge={{ texto: `${d.diversificacao.score}/100`, tom: "neutral" }} texto={d.diversificacao.text}>
        <div className="meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={d.diversificacao.score}
             aria-label="Índice de diversificação">
          <span style={{ width: `${d.diversificacao.score}%` }} />
        </div>
      </Stat>
      <Stat icone="carteira" cor="b2" rotulo="Aplicações" termo="Alocação" valor={String(d.ativos.length)}
            badge={vencendo ? { texto: `${vencendo} vencendo`, tom: "bad" } : undefined}
            texto={`Divididas em ${d.alocacao.length} tipo(s) de investimento.`} />

      {/* avisos */}
      {d.alertas.length > 0 && (
        <section className="card span-12" aria-labelledby="t-avisos">
          <div className="card-head">
            <h2 id="t-avisos"><Icon name="info" /> Avisos <span className="badge neutral">{alertas.length}</span></h2>
            {ocultos.length > 0 && (
              <button className="btn btn-ghost btn-sm" onClick={() => setOcultos([])}>Mostrar todos ({d.alertas.length})</button>
            )}
          </div>
          {alertas.length === 0 && <p className="muted">Você já leu todos os avisos.</p>}
          {alertas.map((a) => <AlertCard key={a.title} a={a} onOcultar={() => setOcultos((o) => [...o, a.title])} />)}
        </section>
      )}

      {/* comparação */}
      <section className="card span-7" aria-labelledby="t-rent">
        <div className="card-head">
          <h2 id="t-rent"><Icon name="grafico" /> Rentabilidade no período <Help termo="Rentabilidade" /></h2>
          <div className="segmented" role="group" aria-label="Forma de exibição">
            <button aria-pressed={vista === "grafico"} onClick={() => setVista("grafico")}><Icon name="grafico" size={16} /> Gráfico</button>
            <button aria-pressed={vista === "tabela"} onClick={() => setVista("tabela")}><Icon name="tabela" size={16} /> Tabela</button>
          </div>
        </div>
        {vista === "grafico" ? (
          <div role="img" aria-label={comparacao.map((c) => `${c.nome}: ${pct(c.valor)}`).join("; ")}>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={comparacao} margin={{ left: 0, right: 8, top: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--borda)" />
                <XAxis dataKey="nome" tick={{ fontSize: 14, fill: "var(--suave)" }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 13, fill: "var(--suave)" }} width={48} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v: number) => pct(v)} cursor={{ fill: "var(--primaria-suave)" }}
                         contentStyle={{ borderRadius: 12, border: "1px solid var(--borda)", background: "var(--cartao)", color: "var(--texto)" }} />
                <Bar dataKey="valor" radius={[10, 10, 0, 0]} maxBarSize={90}>
                  {comparacao.map((_, i) => <Cell key={i} fill={CORES[i]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <caption>Rentabilidade no período de cada aplicação</caption>
              <thead><tr><th scope="col">Referência</th><th scope="col">Rendimento</th></tr></thead>
              <tbody>{comparacao.map((c) => <tr key={c.nome}><th scope="row">{c.nome}</th><td>{pct(c.valor)}</td></tr>)}</tbody>
            </table>
          </div>
        )}
        <p className="muted small">Comparação no mesmo período de cada aplicação, ponderada pelo valor aplicado. Valores brutos, antes de impostos.</p>
      </section>

      {/* alocação */}
      <section className="card span-5" aria-labelledby="t-aloc">
        <div className="card-head"><h2 id="t-aloc"><Icon name="pizza" /> Onde está seu dinheiro <Help termo="Alocação" /></h2></div>
        <div className="donut-wrap" role="img" aria-label={d.alocacao.map((a) => `${a.classe}: ${pct(a.pct, 1)}`).join("; ")}>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={d.alocacao} dataKey="valor" nameKey="classe" innerRadius={68} outerRadius={98} paddingAngle={3} stroke="none">
                {d.alocacao.map((_, i) => <Cell key={i} fill={CORES[i % CORES.length]} />)}
              </Pie>
              <Tooltip formatter={(v: number) => brl(v)}
                       contentStyle={{ borderRadius: 12, border: "1px solid var(--borda)", background: "var(--cartao)", color: "var(--texto)" }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="donut-center"><div><small className="muted">Total</small><strong>{brl(d.patrimonio)}</strong></div></div>
        </div>
        <ul className="legend">
          {d.alocacao.map((a, i) => (
            <li key={a.classe}><span className="dot" style={{ background: CORES[i % CORES.length] }} />{a.classe}<span className="val">{pct(a.pct, 1)}</span></li>
          ))}
        </ul>
      </section>

      {/* aplicações */}
      <section className="card span-12" aria-labelledby="t-ativos">
        <div className="card-head">
          <h2 id="t-ativos"><Icon name="carteira" /> Suas aplicações</h2>
          <div className="chips" role="group" aria-label="Filtrar por tipo">
            {FILTROS.map((f) => (
              <button key={f.id} className="chip" aria-pressed={filtro === f.id} onClick={() => setFiltro(f.id)}>{f.rotulo}</button>
            ))}
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <caption>{ativos.length} aplicação(ões) {filtro === "todos" ? "" : `do tipo selecionado`}</caption>
            <thead>
              <tr><th scope="col">Aplicação</th><th scope="col">Tipo</th><th scope="col">Aplicado</th><th scope="col">Hoje</th>
                <th scope="col">Rendimento</th><th scope="col">Peso na carteira</th></tr>
            </thead>
            <tbody>
              {ativos.map((a) => (
                <tr key={a.id}>
                  <th scope="row">
                    <span className="ativo-nome">
                      <span className="bubble b1" style={{ width: 38, height: 38 }}><Icon name={ICONE_TIPO[a.type] ?? "carteira"} size={18} /></span>
                      <span>
                        {a.ticker ?? a.name}{a.quote_missing && " *"}
                        <small>{a.ticker ? a.name : a.status === "vencido" ? "Vencido – não rende mais" : "Renda fixa"}</small>
                      </span>
                    </span>
                  </th>
                  <td><span className={`tag tag-${a.type}`}>{a.class_label}</span></td>
                  {a.calc_error || a.current == null || a.return_pct == null || a.peso_pct == null ? (
                    <td colSpan={4} className="neg">Erro de cálculo: confira os dados desta aplicação (fora dos totais)</td>
                  ) : (
                    <>
                      <td>{brl(a.invested)}</td>
                      <td><strong>{brl(a.current)}</strong></td>
                      <td className={a.return_pct >= 0 ? "pos" : "neg"}>{a.return_pct >= 0 ? "▲" : "▼"} {pct(a.return_pct)}</td>
                      <td>
                        <span className="peso">
                          <span className="meter"><span style={{ width: `${Math.min(a.peso_pct, 100)}%` }} /></span>
                          {pct(a.peso_pct, 1)}
                        </span>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="form-actions" style={{ marginTop: 14 }}>
          <Link className="btn btn-soft btn-sm" to="/carteira"><Icon name="mais" size={16} /> Adicionar aplicação</Link>
          <Link className="btn btn-ghost btn-sm" to="/carteira"><Icon name="carteira" size={16} /> Gerenciar carteira</Link>
        </div>
      </section>

      <p className="aviso-legal"><Icon name="escudo" size={18} /> {d.aviso}</p>
    </div>
  );
}

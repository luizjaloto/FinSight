import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type Dashboard as D } from "../api";
import AlertCard from "../components/AlertCard";
import Help from "../components/Help";
import { brl, compareText, pct } from "../format";

const CORES = ["#1F4E78", "#C65911", "#4A555C", "#2E7D32"];

export default function Dashboard() {
  const [d, setD] = useState<D | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api.dashboard().then(setD).catch((e) => setErro(e.message));
  }, []);

  if (erro) return <p className="error">{erro}</p>;
  if (!d) return <p className="muted">Carregando seu painel...</p>;
  if (d.ativos.length === 0)
    return (
      <div className="card empty">
        <h2>Sua carteira está vazia</h2>
        <p>Cadastre suas aplicações ou importe o arquivo da B3 para ver o painel.</p>
        <Link className="button" to="/carteira">Cadastrar aplicações</Link>
      </div>
    );

  const comparacao = [
    { nome: "Sua carteira", valor: d.rentabilidade_pct },
    { nome: "CDI", valor: d.cdi_periodo_pct },
    { nome: "Inflação (IPCA)", valor: d.ipca_periodo_pct },
  ];

  return (
    <div className="grid">
      <section className="card kpi">
        <span className="label">Patrimônio <Help termo="Patrimônio" /></span>
        <strong className="big">{brl(d.patrimonio)}</strong>
        <span className="muted">Aplicado: {brl(d.investido)}</span>
      </section>

      <section className={`card kpi ${d.superou_cdi ? "good" : "bad"}`}>
        <span className="label">Rendeu mais que o CDI? <Help termo="CDI" /></span>
        <strong className="big">{d.superou_cdi ? "Sim" : "Não"}</strong>
        <span>{compareText(d.rentabilidade_pct, d.cdi_periodo_pct, "CDI")}</span>
      </section>

      <section className={`card kpi ${d.superou_ipca ? "good" : "bad"}`}>
        <span className="label">Ganhou da inflação? <Help termo="Inflação" /></span>
        <strong className="big">{d.superou_ipca ? "Sim" : "Não"}</strong>
        <span>{compareText(d.rentabilidade_pct, d.ipca_periodo_pct, "IPCA")}</span>
      </section>

      <section className="card kpi">
        <span className="label">Diversificação <Help termo="Diversificação" /></span>
        <strong className={`big band-${d.diversificacao.band.replace("é", "e")}`}>{d.diversificacao.band}</strong>
        <span>{d.diversificacao.text}</span>
      </section>

      {d.alertas.length > 0 && (
        <section className="card wide">
          <h2>Avisos</h2>
          {d.alertas.map((a, i) => <AlertCard key={i} a={a} />)}
        </section>
      )}

      <section className="card half">
        <h2>Rentabilidade no período <Help termo="Rentabilidade" /></h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={comparacao} margin={{ left: 0, right: 10 }}>
            <XAxis dataKey="nome" tick={{ fontSize: 14 }} />
            <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 14 }} width={48} />
            <Tooltip formatter={(v: number) => pct(v)} />
            <Bar dataKey="valor" radius={[6, 6, 0, 0]}>
              {comparacao.map((_, i) => <Cell key={i} fill={CORES[i]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="muted small">Comparação feita no mesmo período de cada aplicação, ponderada pelo valor aplicado.</p>
      </section>

      <section className="card half">
        <h2>Onde está seu dinheiro <Help termo="Alocação" /></h2>
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie data={d.alocacao} dataKey="valor" nameKey="classe" innerRadius={55} outerRadius={90}>
              {d.alocacao.map((_, i) => <Cell key={i} fill={CORES[i % CORES.length]} />)}
            </Pie>
            <Tooltip formatter={(v: number) => brl(v)} />
            <Legend verticalAlign="bottom" wrapperStyle={{ fontSize: 14 }} />
          </PieChart>
        </ResponsiveContainer>
      </section>

      <section className="card wide">
        <h2>Suas aplicações</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Aplicação</th><th>Tipo</th><th>Aplicado</th><th>Hoje</th><th>Rendimento</th><th>Peso</th></tr>
            </thead>
            <tbody>
              {d.ativos.map((a) => (
                <tr key={a.id}>
                  <td>{a.ticker ?? a.name}{a.quote_missing && " *"}</td>
                  <td>{a.class_label}</td>
                  <td>{brl(a.invested)}</td>
                  <td>{brl(a.current)}</td>
                  <td className={a.return_pct >= 0 ? "pos" : "neg"}>{pct(a.return_pct)}</td>
                  <td>{pct(a.peso_pct, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <p className="aviso wide">{d.aviso}</p>
    </div>
  );
}

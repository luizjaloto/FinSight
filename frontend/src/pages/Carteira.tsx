import { FormEvent, useEffect, useState } from "react";
import { api, type Asset, type AssetType } from "../api";
import Help from "../components/Help";
import { brl, parseBR } from "../format";

const hoje = () => new Date().toISOString().slice(0, 10);
const vazio = { type: "renda_fixa" as AssetType, name: "", ticker: "", invested: "", start_date: hoje(), indexer: "cdi", rate: "", maturity: "", quantity: "", avg_price: "" };

export default function Carteira() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [f, setF] = useState({ ...vazio });
  const [msg, setMsg] = useState("");
  const [erro, setErro] = useState("");

  const carregar = () => api.portfolio().then((r) => setAssets(r.assets)).catch((e) => setErro(e.message));
  useEffect(() => { carregar(); }, []);

  const rf = f.type === "renda_fixa";

  const salvar = async (e: FormEvent) => {
    e.preventDefault();
    setErro(""); setMsg("");
    const qty = parseBR(f.quantity), price = parseBR(f.avg_price);
    const body = rf
      ? { type: f.type, name: f.name, invested: parseBR(f.invested), start_date: f.start_date, indexer: f.indexer as "cdi" | "ipca",
          rate: parseBR(f.rate), maturity: f.maturity || null }
      : { type: f.type, name: f.name || f.ticker.toUpperCase(), ticker: f.ticker, quantity: qty, avg_price: price,
          invested: qty * price, start_date: f.start_date };
    try {
      await api.addAsset(body);
      setMsg("Aplicação cadastrada.");
      setF({ ...vazio, type: f.type });
      carregar();
    } catch (err) {
      setErro((err as Error).message);
    }
  };

  const importar = async (file: File | undefined) => {
    if (!file) return;
    setErro(""); setMsg("");
    try {
      const r = await api.importCsv(file);
      const recusadas = r.rejected.map((x) => `linha ${x.line ?? "?"}: ${x.reason}`).join("; ");
      setMsg(`${r.imported} aplicação(ões) importada(s).${recusadas ? ` Recusadas – ${recusadas}` : ""}`);
      carregar();
    } catch (err) {
      setErro((err as Error).message);
    }
  };

  const remover = async (id: string) => {
    await api.removeAsset(id);
    carregar();
  };

  return (
    <div className="grid">
      <form className="card half" onSubmit={salvar}>
        <h2>Cadastrar aplicação</h2>
        <label>
          Tipo
          <select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value as AssetType })}>
            <option value="renda_fixa">Renda fixa (RDC, CDB, LCA, Tesouro)</option>
            <option value="acao">Ação</option>
            <option value="fii">Fundo imobiliário (FII)</option>
          </select>
        </label>

        {rf ? (
          <>
            <label>Nome<input placeholder="Ex.: RDC CrediAlta" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required /></label>
            <label>Valor aplicado (R$)<input inputMode="decimal" placeholder="Ex.: 5.000,00" value={f.invested} onChange={(e) => setF({ ...f, invested: e.target.value })} required /></label>
            <label>
              Rende pelo
              <select value={f.indexer} onChange={(e) => setF({ ...f, indexer: e.target.value })}>
                <option value="cdi">% do CDI</option>
                <option value="ipca">IPCA + taxa</option>
              </select>
            </label>
            <label>
              {f.indexer === "cdi" ? <>Quanto do CDI (%) <Help termo="% do CDI" /></> : <>Taxa acima da inflação (% ao ano) <Help termo="IPCA+" /></>}
              <input inputMode="decimal" placeholder={f.indexer === "cdi" ? "Ex.: 105 (para 105% do CDI)" : "Ex.: 6,2"} value={f.rate}
                     onChange={(e) => setF({ ...f, rate: e.target.value })} required />
            </label>
            <label>Vencimento (opcional)<input type="date" value={f.maturity} onChange={(e) => setF({ ...f, maturity: e.target.value })} /></label>
          </>
        ) : (
          <>
            <label>Código de negociação<input placeholder={f.type === "fii" ? "Ex.: HGLG11" : "Ex.: PETR4"} value={f.ticker} onChange={(e) => setF({ ...f, ticker: e.target.value })} required /></label>
            <label>Quantidade<input inputMode="decimal" value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value })} required /></label>
            <label>Preço médio pago (R$)<input inputMode="decimal" value={f.avg_price} onChange={(e) => setF({ ...f, avg_price: e.target.value })} required /></label>
          </>
        )}
        <label>Data da aplicação<input type="date" value={f.start_date} max={hoje()} onChange={(e) => setF({ ...f, start_date: e.target.value })} required /></label>
        {erro && <p className="error">{erro}</p>}
        {msg && <p className="ok">{msg}</p>}
        <button type="submit">Salvar</button>
      </form>

      <section className="card half">
        <h2>Importar da B3</h2>
        <p>
          Na Área do Investidor da B3, exporte a sua posição em CSV e envie o arquivo aqui. Ações e FIIs são importados com a quantidade e o
          preço de fechamento.
        </p>
        <input type="file" accept=".csv,text/csv" onChange={(e) => importar(e.target.files?.[0])} aria-label="Arquivo CSV da B3" />

        <h2 className="mt">Aplicações cadastradas</h2>
        {assets.length === 0 && <p className="muted">Nenhuma aplicação ainda.</p>}
        <ul className="list">
          {assets.map((a) => (
            <li key={a.id}>
              <span>
                <strong>{a.ticker ?? a.name}</strong> – {brl(a.invested)}
                {a.type === "renda_fixa" && a.rate != null && ` · ${a.indexer === "cdi" ? `${a.rate}% do CDI` : `IPCA + ${a.rate}%`}`}
              </span>
              <button className="link danger" onClick={() => remover(a.id)}>Remover</button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

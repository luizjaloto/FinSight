import { type DragEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type Asset, type AssetType } from "../api";
import Help from "../components/Help";
import Icon, { type IconName } from "../components/Icon";
import { useToast } from "../components/Toast";
import { brl, hojeLocal, parseBR, plural, usaMilharSemVirgula } from "../format";

const vazio = () => ({ name: "", ticker: "", invested: "", start_date: hojeLocal(), indexer: "cdi", rate: "", maturity: "", quantity: "", avg_price: "" });

const TIPOS: { id: AssetType; titulo: string; desc: string; icone: IconName }[] = [
  { id: "renda_fixa", titulo: "Renda fixa", desc: "RDC, CDB, LCA, Tesouro", icone: "predio" },
  { id: "acao", titulo: "Ação", desc: "Ex.: PETR4, ITUB4", icone: "grafico" },
  { id: "fii", titulo: "Fundo imobiliário", desc: "Ex.: HGLG11", icone: "carteira" },
];
const ICONE: Record<AssetType, IconName> = { renda_fixa: "predio", acao: "grafico", fii: "carteira" };

function Cadastro({ onSalvo }: { onSalvo: () => void }) {
  const [tipo, setTipo] = useState<AssetType>("renda_fixa");
  const [f, setF] = useState(vazio);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [confirmacao, setConfirmacao] = useState<{ texto: string; campoId: string } | null>(null);
  const toast = useToast();
  const rf = tipo === "renda_fixa";
  const campo = (k: keyof ReturnType<typeof vazio>) => ({
    value: f[k],
    onChange: (e: { target: { value: string } }) => {
      setF({ ...f, [k]: e.target.value });
      setConfirmacao(null);
    },
  });

  const gravar = async () => {
    setErro("");
    setConfirmacao(null);
    setEnviando(true);
    const qty = parseBR(f.quantity), price = parseBR(f.avg_price);
    const body = rf
      ? { type: tipo, name: f.name, invested: parseBR(f.invested), start_date: f.start_date, indexer: f.indexer as "cdi" | "ipca",
          rate: parseBR(f.rate), maturity: f.maturity || null }
      : { type: tipo, name: f.name || f.ticker.toUpperCase(), ticker: f.ticker, quantity: qty, avg_price: price, invested: qty * price,
          start_date: f.start_date };
    try {
      await api.addAsset(body);
      toast(`${rf ? f.name : f.ticker.toUpperCase()} cadastrada na sua carteira.`);
      setF(vazio());
      onSalvo();
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setEnviando(false);
    }
  };

  const salvar = async (e: FormEvent) => {
    e.preventDefault();
    setErro("");
    if (!confirmacao) {
      const moeda = (v: number) => brl(v).replace(/\u00a0/g, " ");
      if (rf && usaMilharSemVirgula(f.invested)) {
        setConfirmacao({ texto: `Você digitou ${moeda(parseBR(f.invested))}. Está certo?`, campoId: "campo-invested" });
        return;
      }
      if (rf && usaMilharSemVirgula(f.rate)) {
        setConfirmacao({ texto: `Você digitou ${parseBR(f.rate).toLocaleString("pt-BR")}%. Está certo?`, campoId: "campo-rate" });
        return;
      }
      if (!rf && usaMilharSemVirgula(f.avg_price)) {
        setConfirmacao({ texto: `Você digitou ${moeda(parseBR(f.avg_price))}. Está certo?`, campoId: "campo-avg-price" });
        return;
      }
      if (!rf && usaMilharSemVirgula(f.quantity)) {
        setConfirmacao({ texto: `Você digitou ${parseBR(f.quantity).toLocaleString("pt-BR")} na quantidade. Está certo?`, campoId: "campo-quantity" });
        return;
      }
    }
    await gravar();
  };

  return (
    <form onSubmit={salvar} noValidate={false}>
      <div className="tipo-cards" role="group" aria-label="Tipo de aplicação">
        {TIPOS.map((t) => (
          <button type="button" key={t.id} className="tipo-card" aria-pressed={tipo === t.id} onClick={() => { setTipo(t.id); setErro(""); setConfirmacao(null); }}>
            <span className="bubble b1"><Icon name={t.icone} /></span>
            <strong>{t.titulo}</strong>
            <small>{t.desc}</small>
          </button>
        ))}
      </div>

      <div className="form-grid">
        {rf ? (
          <>
            <div className="full" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label htmlFor="campo-name">Nome da aplicação</label>
              <input id="campo-name" placeholder="Ex.: RDC CrediAlta" required {...campo("name")} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label htmlFor="campo-invested">Valor aplicado (R$)</label>
              <input id="campo-invested" inputMode="decimal" placeholder="Ex.: 5.000,00" required {...campo("invested")} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label htmlFor="campo-indexer">Rende pelo</label>
              <select id="campo-indexer" {...campo("indexer")}>
                <option value="cdi">% do CDI</option>
                <option value="ipca">IPCA + taxa</option>
              </select>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <label htmlFor="campo-rate">{f.indexer === "cdi" ? "Quanto do CDI (%)" : "Taxa acima da inflação (% ao ano)"}</label>
                <Help termo={f.indexer === "cdi" ? "% do CDI" : "IPCA+"} />
              </div>
              <input id="campo-rate" inputMode="decimal" aria-describedby="dica-rate" placeholder={f.indexer === "cdi" ? "Ex.: 105 (para 105% do CDI)" : "Ex.: 6,2"} required {...campo("rate")} />
              <span id="dica-rate" className="dica">{f.indexer === "cdi" ? "Pode digitar 105 ou 1,05: os dois significam 105% do CDI." : "Entre -10% e 50% ao ano."}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label htmlFor="campo-maturity">Vencimento (opcional)</label>
              <input id="campo-maturity" type="date" min={f.start_date} {...campo("maturity")} />
            </div>
          </>
        ) : (
          <>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label htmlFor="campo-ticker">Código de negociação</label>
              <input id="campo-ticker" placeholder={tipo === "fii" ? "Ex.: HGLG11" : "Ex.: PETR4"} required {...campo("ticker")} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label htmlFor="campo-name-rv">Nome (opcional)</label>
              <input id="campo-name-rv" placeholder={tipo === "fii" ? "Ex.: CSHG Logística" : "Ex.: Petrobras PN"} {...campo("name")} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label htmlFor="campo-quantity">Quantidade</label>
              <input id="campo-quantity" inputMode="decimal" required {...campo("quantity")} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label htmlFor="campo-avg-price">Preço médio pago (R$)</label>
              <input id="campo-avg-price" inputMode="decimal" required {...campo("avg_price")} />
            </div>
          </>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="campo-start-date">Data da aplicação</label>
          <input id="campo-start-date" type="date" max={hojeLocal()} required {...campo("start_date")} />
        </div>
      </div>

      {confirmacao && (
        <div className="alert atencao" role="alert" style={{ marginTop: 14 }}>
          <span className="bubble"><Icon name="alerta" /></span>
          <div>
            <strong>Confira o valor digitado</strong>
            <p>{confirmacao.texto}</p>
            <div className="form-actions">
              <button type="button" className="btn btn-primary btn-sm" disabled={enviando} onClick={() => void gravar()}>
                Sim, salvar
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => {
                  const id = confirmacao.campoId;
                  setConfirmacao(null);
                  window.requestAnimationFrame(() => document.getElementById(id)?.focus());
                }}
              >
                Corrigir
              </button>
            </div>
          </div>
          <span />
        </div>
      )}
      {erro && <p className="error" role="alert" style={{ marginTop: 14 }}>{erro}</p>}
      <div className="form-actions" style={{ marginTop: 18 }}>
        <button type="submit" className="btn btn-primary" disabled={enviando}>
          <Icon name={enviando ? "atualizar" : "ok"} className={enviando ? "spin" : ""} /> {enviando ? "Salvando…" : "Salvar aplicação"}
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => { setF(vazio()); setErro(""); setConfirmacao(null); }}>Limpar campos</button>
      </div>
    </form>
  );
}

function Importacao({ onImportado }: { onImportado: () => void }) {
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<{ imported: number; rejected: { line: number | null; reason: string }[] } | null>(null);
  const [erro, setErro] = useState("");
  const toast = useToast();

  const enviar = async (file: File | undefined) => {
    if (!file) return;
    if (!/\.csv$/i.test(file.name)) return setErro("Envie um arquivo .csv exportado da Área do Investidor da B3.");
    setErro(""); setResultado(null); setEnviando(true);
    try {
      const r = await api.importCsv(file);
      setResultado(r);
      toast(`${plural(r.imported, "aplicação importada", "aplicações importadas")}.`, r.rejected.length ? "info" : "ok");
      onImportado();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  };

  const soltar = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setArrastando(false);
    enviar(e.dataTransfer.files?.[0]);
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <label className={`dropzone ${arrastando ? "ativa" : ""}`} onDragOver={(e) => { e.preventDefault(); setArrastando(true); }}
             onDragLeave={() => setArrastando(false)} onDrop={soltar}>
        <span className="bubble b1" style={{ width: 60, height: 60 }}><Icon name={enviando ? "atualizar" : "upload"} size={28} className={enviando ? "spin" : ""} /></span>
        <strong>{enviando ? "Importando…" : "Arraste o arquivo CSV aqui ou clique para escolher"}</strong>
        <span className="muted small">Na Área do Investidor da B3, exporte a sua posição em CSV. Máximo de 1 MB.</span>
        <input type="file" accept=".csv,text/csv" onChange={(e) => enviar(e.target.files?.[0])} aria-label="Arquivo CSV da B3" />
      </label>
      <div className="form-actions">
        <a className="btn btn-soft" href="/modelo_posicao_b3.csv" download><Icon name="download" /> Baixar modelo de CSV</a>
        <Link className="btn btn-ghost" to="/glossario#B3"><Icon name="ajuda" /> O que é a B3?</Link>
      </div>
      {erro && <p className="error" role="alert">{erro}</p>}
      {resultado && (
        <div className={`alert ${resultado.rejected.length ? "atencao" : "info"}`} role="status">
          <span className="bubble"><Icon name={resultado.rejected.length ? "alerta" : "ok"} /></span>
          <div>
            <strong>{plural(resultado.imported, "aplicação importada", "aplicações importadas")}</strong>
            {resultado.rejected.length > 0 && (
              <ul className="small" style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                {resultado.rejected.map((x, i) => <li key={i}>Linha {x.line ?? "?"}: {x.reason}</li>)}
              </ul>
            )}
          </div>
          <span />
        </div>
      )}
    </div>
  );
}

export default function Carteira() {
  const [params, setParams] = useSearchParams();
  const aba = params.get("aba") === "importar" ? "importar" : "cadastrar";
  const [assets, setAssets] = useState<Asset[]>([]);
  const [confirmando, setConfirmando] = useState<string | null>(null);
  const [erro, setErro] = useState("");
  const removerBtnRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  const carregar = () => api.portfolio().then((r) => { setAssets(r.assets); setErro(""); }).catch((e) => setErro(e.message));
  useEffect(() => { carregar(); }, []);
  useEffect(() => {
    if (confirmando) removerBtnRef.current?.focus();
  }, [confirmando]);

  const remover = async (a: Asset) => {
    try {
      await api.removeAsset(a.id);
      toast(`${a.ticker ?? a.name} removida da carteira.`);
      setConfirmando(null);
      carregar();
    } catch (e) {
      toast((e as Error).message, "erro");
    }
  };

  const total = assets.reduce((s, a) => s + a.invested, 0);

  return (
    <>
      <div className="page-head">
        <div>
          <h1 tabIndex={-1}>Sua carteira</h1>
          <p>Cadastre suas aplicações uma a uma ou importe tudo de uma vez pelo arquivo da B3.</p>
        </div>
        <Link className="btn btn-soft" to="/"><Icon name="painel" /> Ver painel</Link>
      </div>

      <div className="grid grid-topo">
        <section className="card span-7" aria-labelledby="t-form">
          <div className="card-head">
            <h2 id="t-form">{aba === "cadastrar" ? <><Icon name="mais" /> Nova aplicação</> : <><Icon name="upload" /> Importar da B3</>}</h2>
            <div className="segmented" role="group" aria-label="Forma de cadastro">
              <button type="button" aria-current={aba === "cadastrar" ? "true" : undefined} onClick={() => setParams({})}><Icon name="mais" size={16} /> Cadastrar</button>
              <button type="button" aria-current={aba === "importar" ? "true" : undefined} onClick={() => setParams({ aba: "importar" })}><Icon name="upload" size={16} /> Importar</button>
            </div>
          </div>
          {aba === "cadastrar" ? <Cadastro onSalvo={carregar} /> : <Importacao onImportado={carregar} />}
        </section>

        <section className="card span-5" aria-labelledby="t-lista">
          <div className="card-head">
            <h2 id="t-lista"><Icon name="carteira" /> Cadastradas <span className="badge neutral">{assets.length}</span></h2>
            {assets.length > 0 && <span className="muted small">Aplicado: <strong>{brl(total)}</strong></span>}
          </div>
          {erro && <p className="error" role="alert">{erro}</p>}
          {assets.length === 0 && !erro && (
            <div className="empty" style={{ padding: 24 }}>
              <span className="bubble b1"><Icon name="carteira" size={30} /></span>
              <p className="muted">Nenhuma aplicação ainda. Comece pelo formulário ao lado.</p>
            </div>
          )}
          <ul className="lista">
            {assets.map((a) => (
              <li key={a.id} className="item">
                <span className="bubble b1"><Icon name={ICONE[a.type] ?? "carteira"} /></span>
                <div className="info">
                  <strong>{a.ticker ?? a.name}</strong>
                  <span>
                    {brl(a.invested)}
                    {a.type === "renda_fixa" && a.rate != null && ` · ${a.indexer === "cdi" ? `${a.rate}% do CDI` : `IPCA + ${a.rate}%`}`}
                    {a.maturity && ` · vence ${new Date(a.maturity + "T12:00:00").toLocaleDateString("pt-BR")}`}
                  </span>
                </div>
                {confirmando === a.id ? (
                  <span className="form-actions" style={{ marginTop: 0 }}>
                    <button ref={removerBtnRef} type="button" className="btn btn-danger btn-sm" onClick={() => remover(a)}>Remover</button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => {
                        const id = `lixeira-${a.id}`;
                        setConfirmando(null);
                        window.requestAnimationFrame(() => document.getElementById(id)?.focus());
                      }}
                    >
                      Cancelar
                    </button>
                  </span>
                ) : (
                  <button id={`lixeira-${a.id}`} type="button" className="icon-btn" onClick={() => setConfirmando(a.id)} aria-label={`Remover ${a.ticker ?? a.name}`} title="Remover">
                    <Icon name="lixeira" size={18} />
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}

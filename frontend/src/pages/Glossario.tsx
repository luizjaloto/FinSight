import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api";
import Icon from "../components/Icon";
import { semAcento } from "../format";

function slugTermo(termo: string): string {
  const base = semAcento(termo)
    .replace(/%/g, "pct")
    .replace(/\+/g, "mais")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `t-${base || "termo"}`;
}

export default function Glossario() {
  const [termos, setTermos] = useState<{ termo: string; definicao: string }[]>([]);
  const [busca, setBusca] = useState("");
  const [letra, setLetra] = useState<string | null>(null);
  const [erro, setErro] = useState("");
  const { hash } = useLocation();
  const alvo = decodeURIComponent(hash.replace("#", ""));

  useEffect(() => {
    api.glossary().then(setTermos).catch((e) => setErro(e.message));
  }, []);

  useEffect(() => {
    if (alvo && termos.length) {
      const id = alvo.startsWith("t-") ? alvo : slugTermo(alvo);
      const reduzido = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      document.getElementById(id)?.scrollIntoView({ behavior: reduzido ? "auto" : "smooth", block: "center" });
    }
  }, [alvo, termos]);

  const letras = useMemo(() => [...new Set(termos.map((t) => semAcento(t.termo[0] === "%" ? "C" : t.termo[0]).toUpperCase()))].sort(), [termos]);
  const lista = termos.filter((t) => {
    const okBusca = semAcento(t.termo + " " + t.definicao).includes(semAcento(busca));
    const inicial = semAcento(t.termo[0] === "%" ? "C" : t.termo[0]).toUpperCase();
    return okBusca && (!letra || inicial === letra);
  });

  return (
    <>
      <div className="page-head">
        <div>
          <h1 tabIndex={-1}>Glossário</h1>
          <p>Os termos do mundo dos investimentos, explicados sem “economês”.</p>
        </div>
        <span className="badge neutral"><Icon name="livro" size={16} /> {termos.length} termos</span>
      </div>

      <div className="card">
        <div className="input-icon">
          <Icon name="busca" />
          <input placeholder="Buscar termo (ex.: IPCA+, liquidez, patrimonio)" value={busca} onChange={(e) => setBusca(e.target.value)}
                 aria-label="Buscar termo" />
        </div>
        <div className="letras" role="group" aria-label="Filtrar pela letra inicial">
          <button className="chip" aria-pressed={letra === null} onClick={() => setLetra(null)}>Todas</button>
          {letras.map((l) => (
            <button key={l} className="chip" aria-pressed={letra === l} onClick={() => setLetra(letra === l ? null : l)}>{l}</button>
          ))}
        </div>
        <p className="muted small" aria-live="polite" style={{ margin: "0 0 12px" }}>
          {lista.length === 1 ? "1 termo encontrado" : `${lista.length} termos encontrados`}
        </p>
        {erro && <p className="error" role="alert">{erro}</p>}
        {lista.length === 0 && !erro && (
          <div className="empty" style={{ padding: 24 }}>
            <p className="muted">Nenhum termo encontrado.</p>
            <button className="btn btn-soft" onClick={() => { setBusca(""); setLetra(null); }}>Limpar busca</button>
          </div>
        )}
        <div className="termos">
          {lista.map((t) => {
            const id = slugTermo(t.termo);
            return (
              <article key={t.termo} id={id} className={`termo ${t.termo === alvo || id === alvo ? "destaque" : ""}`}>
                <h3>{t.termo}</h3>
                <p>{t.definicao}</p>
              </article>
            );
          })}
        </div>
      </div>
    </>
  );
}

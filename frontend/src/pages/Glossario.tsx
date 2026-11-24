import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api";

export default function Glossario() {
  const [termos, setTermos] = useState<{ termo: string; definicao: string }[]>([]);
  const [busca, setBusca] = useState("");
  const { hash } = useLocation();
  const alvo = decodeURIComponent(hash.replace("#", ""));

  useEffect(() => {
    api.glossary().then(setTermos);
  }, []);

  useEffect(() => {
    if (alvo && termos.length) document.getElementById(`t-${alvo}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [alvo, termos]);

  const lista = termos.filter((t) => (t.termo + t.definicao).toLowerCase().includes(busca.toLowerCase()));

  return (
    <section className="card wide">
      <h2>Glossário</h2>
      <input placeholder="Buscar termo (ex.: IPCA+)" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label="Buscar termo" />
      <dl className="glossary">
        {lista.map((t) => (
          <div key={t.termo} id={`t-${t.termo}`} className={t.termo === alvo ? "highlight" : ""}>
            <dt>{t.termo}</dt>
            <dd>{t.definicao}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

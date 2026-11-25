import { useState } from "react";
import type { Alerta } from "../api";
import Icon, { type IconName } from "./Icon";

const ICONES: Record<Alerta["kind"], IconName> = {
  concentracao: "pizza",
  vencimento: "calendario",
  vencido: "calendario",
  cotacao: "info",
  erro_calculo: "alerta",
  indicadores: "atualizar",
};

/** Aviso educativo: explica, não recomenda. O usuário pode abrir a explicação ou ocultar o aviso. */
export default function AlertCard({ a, onOcultar }: { a: Alerta; onOcultar?: () => void }) {
  const [aberto, setAberto] = useState(false);
  return (
    <div className={`alert ${a.level}`}>
      <span className="bubble"><Icon name={ICONES[a.kind] ?? "info"} /></span>
      <div>
        <strong>{a.title}</strong>
        <p>{a.text}</p>
        {aberto && <p className="why">{a.why}</p>}
        <div className="alert-actions">
          <button className="link-btn" onClick={() => setAberto(!aberto)} aria-expanded={aberto}>
            {aberto ? "Fechar explicação" : "Por que isso importa?"}
          </button>
        </div>
      </div>
      {onOcultar && (
        <button className="btn btn-ghost btn-sm" onClick={onOcultar} aria-label={`Ocultar o aviso: ${a.title}`}>
          Entendi
        </button>
      )}
    </div>
  );
}

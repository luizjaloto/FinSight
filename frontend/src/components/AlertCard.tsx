import { useState } from "react";
import type { Alerta } from "../api";

export default function AlertCard({ a }: { a: Alerta }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`alert ${a.level}`} role="status">
      <strong>{a.title}</strong>
      <p>{a.text}</p>
      <button className="link" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? "Fechar explicação" : "Por que isso importa?"}
      </button>
      {open && <p className="why">{a.why}</p>}
    </div>
  );
}

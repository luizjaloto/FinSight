import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import Icon from "./Icon";

type Tipo = "ok" | "erro" | "info";
interface Aviso {
  id: number;
  tipo: Tipo;
  texto: string;
}

const TEMPO_SUCESSO_MS = 7000;
const Ctx = createContext<(texto: string, tipo?: Tipo) => void>(() => {});

function ItemToast({ a, onFechar }: { a: Aviso; onFechar: (id: number) => void }) {
  const [pausado, setPausado] = useState(false);
  const restante = useRef(TEMPO_SUCESSO_MS);
  const inicio = useRef(Date.now());

  useEffect(() => {
    if (a.tipo === "erro" || pausado) return;
    inicio.current = Date.now();
    const timer = window.setTimeout(() => onFechar(a.id), restante.current);
    return () => {
      window.clearTimeout(timer);
      const decorrido = Date.now() - inicio.current;
      restante.current = Math.max(1000, restante.current - decorrido);
    };
  }, [a.id, a.tipo, onFechar, pausado]);

  return (
    <div
      className={`toast toast-${a.tipo}`}
      onMouseEnter={() => setPausado(true)}
      onMouseLeave={() => setPausado(false)}
      onFocusCapture={() => setPausado(true)}
      onBlurCapture={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setPausado(false);
      }}
    >
      <Icon name={a.tipo === "ok" ? "ok" : a.tipo === "erro" ? "alerta" : "info"} />
      <span>{a.texto}</span>
      <button type="button" className="icon-btn" onClick={() => onFechar(a.id)} aria-label="Fechar aviso">
        <Icon name="fechar" size={16} />
      </button>
    </div>
  );
}

/** Notificações no canto da tela: erros ficam até fechar; demais avisos somem em 7 s com pausa em hover/foco. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);

  const fechar = useCallback((id: number) => setAvisos((a) => a.filter((x) => x.id !== id)), []);
  const mostrar = useCallback((texto: string, tipo: Tipo = "ok") => {
    const id = Date.now() + Math.random();
    setAvisos((a) => [...a, { id, tipo, texto }]);
  }, []);

  return (
    <Ctx.Provider value={mostrar}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {avisos.map((a) => (
          <ItemToast key={a.id} a={a} onFechar={fechar} />
        ))}
      </div>
    </Ctx.Provider>
  );
}

export const useToast = () => useContext(Ctx);

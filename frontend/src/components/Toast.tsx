import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import Icon from "./Icon";

type Tipo = "ok" | "erro" | "info";
interface Aviso {
  id: number;
  tipo: Tipo;
  texto: string;
}

const Ctx = createContext<(texto: string, tipo?: Tipo) => void>(() => {});

/** Notificações rápidas no canto da tela (somem sozinhas em 4 segundos). */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);

  const fechar = (id: number) => setAvisos((a) => a.filter((x) => x.id !== id));
  const mostrar = useCallback((texto: string, tipo: Tipo = "ok") => {
    const id = Date.now() + Math.random();
    setAvisos((a) => [...a, { id, tipo, texto }]);
    window.setTimeout(() => fechar(id), 4000);
  }, []);

  return (
    <Ctx.Provider value={mostrar}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {avisos.map((a) => (
          <div key={a.id} className={`toast toast-${a.tipo}`}>
            <Icon name={a.tipo === "ok" ? "ok" : a.tipo === "erro" ? "alerta" : "info"} />
            <span>{a.texto}</span>
            <button className="icon-btn" onClick={() => fechar(a.id)} aria-label="Fechar aviso">
              <Icon name="fechar" size={16} />
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export const useToast = () => useContext(Ctx);

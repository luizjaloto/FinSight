import type { ReactNode } from "react";
import Icon from "./Icon";
import { Logo } from "./Layout";

const PONTOS = [
  "Veja todo o seu patrimônio em um só lugar",
  "Compare o rendimento com o CDI e a inflação",
  "Entenda a diversificação com avisos em linguagem simples",
];

/** Moldura das telas de entrada: painel colorido à esquerda e formulário à direita. */
export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="auth">
      <aside className="auth-side">
        <div>
          <span className="brand"><Logo /> FinSight</span>
          <h1>Entenda sua carteira em poucos minutos.</h1>
          <ul>
            {PONTOS.map((p) => (
              <li key={p}><Icon name="ok" /> <span>{p}</span></li>
            ))}
          </ul>
        </div>
        <p className="rodape small" style={{ opacity: 0.9, position: "relative" }}>
          Ferramenta educativa: mede e explica, não recomenda investimentos. Projeto Integrador III – Fatec Pompeia.
        </p>
      </aside>
      <main className="auth-main">{children}</main>
    </div>
  );
}

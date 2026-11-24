import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api, setSession } from "../api";

export default function Layout() {
  const nav = useNavigate();
  const name = localStorage.getItem("finsight_name") ?? "";

  const sair = () => {
    setSession(null);
    nav("/login");
  };

  const excluir = async () => {
    if (!window.confirm("Excluir sua conta apaga todos os seus dados do FinSight. Deseja continuar?")) return;
    await api.deleteAccount();
    sair();
  };

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">FinSight</span>
        <nav>
          <NavLink to="/" end>Painel</NavLink>
          <NavLink to="/carteira">Carteira</NavLink>
          <NavLink to="/glossario">Glossário</NavLink>
        </nav>
        <div className="user">
          <span>{name}</span>
          <button className="link" onClick={sair}>Sair</button>
          <button className="link danger" onClick={excluir}>Excluir conta</button>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
      <footer>
        FinSight é uma ferramenta educativa e não faz recomendação de investimento. Dados: Banco Central do Brasil (SGS) e
        cotações com até 15 minutos de atraso. Projeto Integrador III – Fatec Pompeia, Equipe 04.
      </footer>
    </div>
  );
}

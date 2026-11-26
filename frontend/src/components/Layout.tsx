import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { api, setSession } from "../api";
import { iniciais } from "../format";
import { useTema } from "../theme";
import Icon, { type IconName } from "./Icon";
import { useToast } from "./Toast";

const LINKS: { to: string; rotulo: string; icone: IconName }[] = [
  { to: "/", rotulo: "Painel", icone: "painel" },
  { to: "/carteira", rotulo: "Carteira", icone: "carteira" },
  { to: "/glossario", rotulo: "Glossário", icone: "livro" },
];

export function Logo() {
  return (
    <span className="logo" aria-hidden="true">
      <Icon name="sobe" size={20} />
    </span>
  );
}

function MenuUsuario({ nome }: { nome: string }) {
  const [aberto, setAberto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const botaoRef = useRef<HTMLButtonElement>(null);
  const primeiroItemRef = useRef<HTMLButtonElement>(null);
  const nav = useNavigate();
  const toast = useToast();

  useEffect(() => {
    if (!aberto) return;
    primeiroItemRef.current?.focus();
    const fora = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setAberto(false);
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setAberto(false);
        botaoRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("keydown", esc);
    };
  }, [aberto]);

  const sair = () => {
    setSession(null);
    nav("/login");
  };

  const exportar = async () => {
    setAberto(false);
    try {
      const dados = await api.exportData();
      const url = URL.createObjectURL(new Blob([JSON.stringify(dados, null, 2)], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "finsight-meus-dados.json";
      a.click();
      URL.revokeObjectURL(url);
      toast("Seus dados foram baixados.");
    } catch (e) {
      toast((e as Error).message, "erro");
    }
  };

  const excluir = async () => {
    setAberto(false);
    if (!window.confirm("Excluir sua conta apaga todos os seus dados do FinSight, sem volta. Deseja continuar?")) return;
    try {
      await api.deleteAccount();
      sair();
    } catch (e) {
      toast((e as Error).message, "erro");
    }
  };

  return (
    <div className="user-menu" ref={ref}>
      <button ref={botaoRef} type="button" className="user-btn" onClick={() => setAberto(!aberto)} aria-expanded={aberto}>
        <span className="avatar">{iniciais(nome)}</span>
        <span className="nome">{nome.split(" ")[0]}</span>
        <Icon name="seta" size={16} />
      </button>
      {aberto && (
        <div className="menu">
          <div className="menu-head">
            <strong>{nome}</strong>
            <br />
            <small>Seus dados ficam só na sua conta.</small>
          </div>
          <button ref={primeiroItemRef} type="button" onClick={exportar}><Icon name="download" /> Baixar meus dados</button>
          <button type="button" onClick={sair}><Icon name="sair" /> Sair</button>
          <button type="button" className="perigo" onClick={excluir}><Icon name="lixeira" /> Excluir minha conta</button>
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const nome = localStorage.getItem("finsight_name") ?? "Usuário";
  const [tema, alternarTema] = useTema();

  return (
    <div className="app">
      <a className="skip" href="#conteudo">Pular para o conteúdo</a>
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="brand" aria-label="FinSight – ir para o painel">
            <Logo /> FinSight
          </Link>
          <nav className="nav" aria-label="Principal">
            {LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.to === "/"}>
                <Icon name={l.icone} size={18} /> {l.rotulo}
              </NavLink>
            ))}
          </nav>
          <div className="top-actions">
            <button className="icon-btn" onClick={alternarTema} aria-label={tema === "claro" ? "Ativar tema escuro" : "Ativar tema claro"}
                    title={tema === "claro" ? "Tema escuro" : "Tema claro"}>
              <Icon name={tema === "claro" ? "lua" : "sol"} />
            </button>
            <MenuUsuario nome={nome} />
          </div>
        </div>
      </header>

      <main id="conteudo">
        <Outlet />
      </main>

      <nav className="bottom-nav" aria-label="Principal (celular)">
        {LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.to === "/"}>
            <Icon name={l.icone} /> {l.rotulo}
          </NavLink>
        ))}
      </nav>

      <footer>
        FinSight é uma ferramenta educativa e não faz recomendação de investimento. Dados: Banco Central do Brasil (SGS) e cotações com
        até 15 minutos de atraso. Projeto Integrador III – Fatec Pompeia, Equipe 04.
      </footer>
    </div>
  );
}

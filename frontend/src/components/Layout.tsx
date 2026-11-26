import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
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
  const [confirmaExclusao, setConfirmaExclusao] = useState(false);
  const [excluindo, setExcluindo] = useState(false);
  const nav = useNavigate();
  const toast = useToast();

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setAberto(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setAberto(false);
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("keydown", esc);
    };
  }, [aberto]);

  useEffect(() => {
    if (!confirmaExclusao) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setConfirmaExclusao(false);
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [confirmaExclusao]);

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

  const pedirExclusao = () => {
    setAberto(false);
    setConfirmaExclusao(true);
  };

  const excluirConta = async () => {
    setExcluindo(true);
    try {
      await api.deleteAccount();
      setConfirmaExclusao(false);
      toast("Sua conta foi excluída.");
      sair();
    } catch (e) {
      toast((e as Error).message, "erro");
    } finally {
      setExcluindo(false);
    }
  };

  return (
    <div className="user-menu" ref={ref}>
      <button className="user-btn" onClick={() => setAberto(!aberto)} aria-expanded={aberto} aria-haspopup="menu">
        <span className="avatar">{iniciais(nome)}</span>
        <span className="nome">{nome.split(" ")[0]}</span>
        <Icon name="seta" size={16} />
      </button>
      {aberto && (
        <div className="menu" role="menu">
          <div className="menu-head">
            <strong>{nome}</strong>
            <br />
            <small>Seus dados ficam só na sua conta.</small>
          </div>
          <button role="menuitem" onClick={exportar}><Icon name="download" /> Baixar meus dados</button>
          <button role="menuitem" onClick={sair}><Icon name="sair" /> Sair</button>
          <button role="menuitem" className="perigo" onClick={pedirExclusao}><Icon name="lixeira" /> Excluir minha conta</button>
        </div>
      )}
      {confirmaExclusao && createPortal(
        <div className="modal-fundo">
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="titulo-exclusao" aria-describedby="texto-exclusao">
            <h2 id="titulo-exclusao">Excluir sua conta?</h2>
            <p id="texto-exclusao">Seus dados serão apagados e isso não pode ser desfeito. Quer baixar uma cópia antes?</p>
            <div className="modal-acoes">
              <button className="btn btn-ghost" onClick={exportar} disabled={excluindo}>Baixar meus dados</button>
              <button className="btn btn-danger" onClick={excluirConta} disabled={excluindo}>Excluir conta</button>
              <button className="btn btn-primary" onClick={() => setConfirmaExclusao(false)} autoFocus>Manter minha conta</button>
            </div>
          </div>
        </div>,
        document.body,
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

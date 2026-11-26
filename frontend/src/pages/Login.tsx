import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, setSession } from "../api";
import AuthShell from "../components/AuthShell";
import Icon from "../components/Icon";

export default function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [ver, setVer] = useState(false);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setErro("");
    setLoading(true);
    try {
      const r = await api.login({ email, password });
      setSession(r.access_token, r.name);
      nav("/");
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell>
      <form className="auth-card" onSubmit={enviar}>
        <div>
          <h2>Bem-vindo de volta</h2>
          <p className="muted">Entre para ver o painel da sua carteira.</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="login-email">E-mail</label>
          <span className="input-icon">
            <Icon name="usuario" />
            <input id="login-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="login-senha">Senha</label>
          <span className="input-action">
            <input id="login-senha" type={ver ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
            <button type="button" className="icon-btn" onClick={() => setVer(!ver)} aria-label={ver ? "Esconder senha" : "Mostrar senha"}>
              <Icon name={ver ? "olhoFechado" : "olho"} size={18} />
            </button>
          </span>
        </div>
        {erro && <p className="error" role="alert">{erro}</p>}
        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          <Icon name={loading ? "atualizar" : "sair"} className={loading ? "spin" : ""} /> {loading ? "Entrando…" : "Entrar"}
        </button>
        {import.meta.env.VITE_DEMO === "1" && (
          <button type="button" className="btn btn-ghost btn-block" onClick={() => setEmail("demo@finsight.app")}>
            <Icon name="brilho" /> Usar o e-mail da conta de demonstração
          </button>
        )}
        <p className="muted" style={{ textAlign: "center", margin: 0 }}>Ainda não tem conta? <Link to="/cadastro">Criar conta grátis</Link></p>
        <p className="muted small" style={{ textAlign: "center", margin: 0 }}>O primeiro acesso pode levar alguns segundos enquanto o servidor inicia.</p>
      </form>
    </AuthShell>
  );
}

import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, setSession } from "../api";

export default function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
    <div className="auth">
      <form className="card" onSubmit={enviar}>
        <h1>FinSight</h1>
        <p className="muted">Entenda sua carteira em poucos minutos.</p>
        <label>E-mail<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" /></label>
        <label>Senha<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></label>
        {erro && <p className="error">{erro}</p>}
        <button type="submit" disabled={loading}>{loading ? "Entrando..." : "Entrar"}</button>
        <p>Não tem conta? <Link to="/cadastro">Criar conta</Link></p>
        <p className="muted small">O primeiro acesso pode levar até 30 segundos enquanto o servidor inicia.</p>
      </form>
    </div>
  );
}

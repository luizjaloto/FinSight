import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, setSession } from "../api";

export default function Register() {
  const nav = useNavigate();
  const [f, setF] = useState({ name: "", email: "", password: "", accept_terms: false });
  const [erro, setErro] = useState("");

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setErro("");
    if (f.password.length < 8) return setErro("A senha precisa ter pelo menos 8 caracteres.");
    if (!f.accept_terms) return setErro("É preciso aceitar o termo de privacidade.");
    try {
      const r = await api.register(f);
      setSession(r.access_token, r.name);
      nav("/carteira");
    } catch (err) {
      setErro((err as Error).message);
    }
  };

  return (
    <div className="auth">
      <form className="card" onSubmit={enviar}>
        <h1>Criar conta</h1>
        <label>Nome<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required /></label>
        <label>E-mail<input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required /></label>
        <label>
          Senha (mínimo 8 caracteres)
          <input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} required autoComplete="new-password" />
        </label>
        <div className="terms">
          <strong>Termo de privacidade</strong>
          <p>
            Guardamos apenas seu nome, e-mail e as aplicações que você cadastrar. Não pedimos senha de banco, CPF ou número de conta.
            Você pode excluir sua conta e todos os dados a qualquer momento. O FinSight é educativo e não recomenda investimentos.
          </p>
          <label className="check">
            <input type="checkbox" checked={f.accept_terms} onChange={(e) => setF({ ...f, accept_terms: e.target.checked })} />
            Li e aceito o termo de privacidade
          </label>
        </div>
        {erro && <p className="error">{erro}</p>}
        <button type="submit">Criar conta</button>
        <p>Já tem conta? <Link to="/login">Entrar</Link></p>
      </form>
    </div>
  );
}

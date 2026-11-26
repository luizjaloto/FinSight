import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, setSession } from "../api";
import AuthShell from "../components/AuthShell";
import Icon from "../components/Icon";
import { bytesUtf8, forcaSenha } from "../format";

export default function Register() {
  const nav = useNavigate();
  const [f, setF] = useState({ name: "", email: "", password: "", accept_terms: false });
  const [ver, setVer] = useState(false);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const forca = forcaSenha(f.password);
  const bytes = bytesUtf8(f.password);

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setErro("");
    if (f.password.length < 8) return setErro("A senha precisa ter pelo menos 8 caracteres.");
    if (bytes > 72) return setErro("A senha pode ter no máximo 72 bytes (cerca de 72 letras sem acento).");
    if (!f.accept_terms) return setErro("É preciso aceitar o termo de privacidade.");
    setEnviando(true);
    try {
      const r = await api.register(f);
      setSession(r.access_token, r.name);
      nav("/carteira");
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <AuthShell>
      <form className="auth-card" onSubmit={enviar}>
        <div>
          <h2>Crie sua conta</h2>
          <p className="muted">Leva menos de um minuto. Não pedimos dados bancários.</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="cad-nome">Nome</label>
          <span className="input-icon">
            <Icon name="usuario" />
            <input id="cad-nome" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required autoComplete="name" />
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="cad-email">E-mail</label>
          <input id="cad-email" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required autoComplete="email" />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="cad-senha">Senha</label>
          <span className="input-action">
            <input id="cad-senha" type={ver ? "text" : "password"} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} required
                   autoComplete="new-password" aria-describedby="forca-senha" />
            <button type="button" className="icon-btn" onClick={() => setVer(!ver)} aria-label={ver ? "Esconder senha" : "Mostrar senha"}>
              <Icon name={ver ? "olhoFechado" : "olho"} size={18} />
            </button>
          </span>
          <span className="forca" data-nivel={forca.nivel} aria-hidden="true"><span /><span /><span /><span /></span>
          <span id="forca-senha" className="dica">{forca.texto}{bytes > 72 && " · passou do limite de 72 bytes"}</span>
        </div>
        <div className="termos-box">
          <strong><Icon name="escudo" size={16} /> Termo de privacidade</strong>
          <p>
            Guardamos apenas seu nome, e-mail e as aplicações que você cadastrar. Não pedimos senha de banco, CPF ou número de conta. Você pode
            baixar ou excluir todos os seus dados a qualquer momento. O FinSight é educativo e não recomenda investimentos.
          </p>
          <div className="check" style={{ display: "flex" }}>
            <input id="cad-termos" type="checkbox" checked={f.accept_terms} onChange={(e) => setF({ ...f, accept_terms: e.target.checked })} />
            <label htmlFor="cad-termos" style={{ fontWeight: 500 }}>Li e aceito o termo de privacidade</label>
          </div>
        </div>
        {erro && <p className="error" role="alert">{erro}</p>}
        <button type="submit" className="btn btn-primary btn-block" disabled={enviando}>
          <Icon name={enviando ? "atualizar" : "brilho"} className={enviando ? "spin" : ""} /> {enviando ? "Criando conta…" : "Criar minha conta"}
        </button>
        <p className="muted" style={{ textAlign: "center", margin: 0 }}>Já tem conta? <Link to="/login">Entrar</Link></p>
      </form>
    </AuthShell>
  );
}

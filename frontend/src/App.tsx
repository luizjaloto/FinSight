import { useEffect, useRef } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { getToken } from "./api";
import Layout from "./components/Layout";
import Carteira from "./pages/Carteira";
import Dashboard from "./pages/Dashboard";
import Glossario from "./pages/Glossario";
import Login from "./pages/Login";
import Register from "./pages/Register";

const TITULOS: Record<string, string> = {
  "/": "Painel – FinSight",
  "/carteira": "Sua carteira – FinSight",
  "/glossario": "Glossário – FinSight",
  "/login": "Entrar – FinSight",
  "/cadastro": "Criar conta – FinSight",
};

function GerenciadorRota() {
  const { pathname } = useLocation();
  const rotaAnterior = useRef(pathname);

  useEffect(() => {
    document.title = TITULOS[pathname] ?? "FinSight";
    if (rotaAnterior.current === pathname) return;
    rotaAnterior.current = pathname;

    const focarH1 = () => {
      const h1 = document.querySelector<HTMLElement>("main h1") ?? document.querySelector<HTMLElement>("h1");
      if (!h1) return false;
      if (!h1.hasAttribute("tabindex")) h1.setAttribute("tabindex", "-1");
      h1.focus({ preventScroll: true });
      return true;
    };

    if (focarH1()) return;
    const obs = new MutationObserver(() => {
      if (focarH1()) obs.disconnect();
    });
    obs.observe(document.body, { childList: true, subtree: true });
    return () => obs.disconnect();
  }, [pathname]);

  return null;
}

function Private({ children }: { children: JSX.Element }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <>
      <GerenciadorRota />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/cadastro" element={<Register />} />
        <Route element={<Private><Layout /></Private>}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/carteira" element={<Carteira />} />
          <Route path="/glossario" element={<Glossario />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

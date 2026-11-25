import { useEffect, useState } from "react";

export type Tema = "claro" | "escuro";
const CHAVE = "finsight_tema";

function inicial(): Tema {
  try {
    const salvo = localStorage.getItem(CHAVE);
    if (salvo === "claro" || salvo === "escuro") return salvo;
  } catch {
    /* navegador sem localStorage: segue a preferência do sistema */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "escuro" : "claro";
}

/** Tema claro/escuro, lembrado no navegador do usuário. */
export function useTema(): [Tema, () => void] {
  const [tema, setTema] = useState<Tema>(inicial);
  useEffect(() => {
    document.documentElement.dataset.theme = tema === "escuro" ? "dark" : "light";
    try {
      localStorage.setItem(CHAVE, tema);
    } catch {
      /* ignora: o tema só não fica salvo */
    }
  }, [tema]);
  return [tema, () => setTema((t) => (t === "claro" ? "escuro" : "claro"))];
}

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { ToastProvider } from "./components/Toast";
import "./styles.css";

// Aplica o tema salvo antes da primeira pintura, para não piscar
try {
  const tema = localStorage.getItem("finsight_tema");
  const escuro = tema ? tema === "escuro" : window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = escuro ? "dark" : "light";
} catch {
  /* sem localStorage: fica o tema claro */
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <App />
      </ToastProvider>
    </BrowserRouter>
  </React.StrictMode>,
);

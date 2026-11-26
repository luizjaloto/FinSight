// Verificador automático de contraste WCAG 2.1 AA para os tokens de styles.css
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CSS_PATH = resolve(__dirname, "../src/styles.css");

export function hexParaRgb(hex) {
  const limpo = hex.trim().replace("#", "");
  const valor = limpo.length === 3
    ? limpo.split("").map((c) => parseInt(c + c, 16))
    : [parseInt(limpo.slice(0, 2), 16), parseInt(limpo.slice(2, 4), 16), parseInt(limpo.slice(4, 6), 16)];
  return valor;
}

export function misturarSobre(fgRgb, bgRgb, alpha) {
  return fgRgb.map((c, i) => Math.round(c * alpha + bgRgb[i] * (1 - alpha)));
}

export function luminancia([r, g, b]) {
  const canal = (v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b);
}

export function razaoContraste(corA, corB) {
  const a = Array.isArray(corA) ? corA : hexParaRgb(corA);
  const b = Array.isArray(corB) ? corB : hexParaRgb(corB);
  const l1 = luminancia(a);
  const l2 = luminancia(b);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

export function extrairTokens(css) {
  const blocoClaro = css.match(/:root\s*\{([^}]+)\}/)?.[1] ?? "";
  const blocoEscuro = css.match(/:root\[data-theme="dark"\]\s*\{([^}]+)\}/)?.[1] ?? "";
  const ler = (bloco) => {
    const mapa = {};
    for (const m of bloco.matchAll(/--([a-z0-9-]+)\s*:\s*([^;]+);/gi)) {
      mapa[m[1]] = m[2].trim();
    }
    return mapa;
  };
  return { claro: ler(blocoClaro), escuro: ler(blocoEscuro) };
}

export function verificarContrastes(css = readFileSync(CSS_PATH, "utf8")) {
  const { claro, escuro } = extrairTokens(css);
  const fimGrad = [...(claro.grad?.matchAll(/#[0-9a-f]{6}/gi) ?? [])].pop()?.[0] ?? claro.rosa;
  const fundoGlass = misturarSobre([255, 255, 255], hexParaRgb(fimGrad), 0.16);

  const pares = [
    // Tema claro — textos (mínimo 4,5:1) e interface/ícones (mínimo 3:1)
    { alvo: "Texto principal / fundo (claro)", fg: claro.texto, bg: claro.fundo, min: 4.5 },
    { alvo: "Texto principal / cartão (claro)", fg: claro.texto, bg: claro.cartao, min: 4.5 },
    { alvo: "Texto suave / fundo (claro)", fg: claro.suave, bg: claro.fundo, min: 4.5 },
    { alvo: "Texto suave / cartão (claro)", fg: claro.suave, bg: claro.cartao, min: 4.5 },
    { alvo: "Primária / cartão (claro)", fg: claro.primaria, bg: claro.cartao, min: 4.5 },
    { alvo: "Primária / primária-suave (claro)", fg: claro.primaria, bg: claro["primaria-suave"], min: 4.5 },
    { alvo: ".tag-acao (claro)", fg: claro.acento, bg: claro["vermelho-suave"], min: 4.5 },
    { alvo: "Ícone .bubble.b2 (claro)", fg: claro.acento, bg: claro["vermelho-suave"], min: 3.0 },
    { alvo: "Ícone .bubble.b4 (claro)", fg: claro.acento, bg: claro["ambar-suave"], min: 3.0 },
    { alvo: ".tag-fii (claro)", fg: claro.teal, bg: claro["verde-suave"], min: 4.5 },
    { alvo: "Verde / verde-suave (claro)", fg: claro.verde, bg: claro["verde-suave"], min: 4.5 },
    { alvo: "Vermelho / vermelho-suave (claro)", fg: claro.vermelho, bg: claro["vermelho-suave"], min: 4.5 },
    { alvo: "Borda de campos / cartão (claro)", fg: claro["borda-campo"], bg: claro.cartao, min: 3.0 },
    { alvo: "Chip ativo e .help:hover (claro)", fg: claro["sobre-primaria"], bg: claro.primaria, min: 4.5 },
    { alvo: "Texto do hero sobre ponta rosa", fg: "#ffffff", bg: fimGrad, min: 4.5 },
    { alvo: ".btn-glass sobre ponta rosa", fg: "#ffffff", bg: fundoGlass, min: 4.5 },

    // Tema escuro — textos (mínimo 4,5:1) e interface/ícones (mínimo 3:1)
    { alvo: "Texto principal / fundo (escuro)", fg: escuro.texto, bg: escuro.fundo, min: 4.5 },
    { alvo: "Texto principal / cartão (escuro)", fg: escuro.texto, bg: escuro.cartao, min: 4.5 },
    { alvo: "Texto suave / fundo (escuro)", fg: escuro.suave, bg: escuro.fundo, min: 4.5 },
    { alvo: "Texto suave / cartão (escuro)", fg: escuro.suave, bg: escuro.cartao, min: 4.5 },
    { alvo: "Primária / cartão (escuro)", fg: escuro.primaria, bg: escuro.cartao, min: 4.5 },
    { alvo: "Primária / primária-suave (escuro)", fg: escuro.primaria, bg: escuro["primaria-suave"], min: 4.5 },
    { alvo: ".tag-acao (escuro)", fg: escuro.acento, bg: escuro["vermelho-suave"], min: 4.5 },
    { alvo: "Ícone .bubble.b4 (escuro)", fg: escuro.acento, bg: escuro["ambar-suave"], min: 3.0 },
    { alvo: ".tag-fii (escuro)", fg: escuro.teal, bg: escuro["verde-suave"], min: 4.5 },
    { alvo: "Verde / verde-suave (escuro)", fg: escuro.verde, bg: escuro["verde-suave"], min: 4.5 },
    { alvo: "Vermelho / vermelho-suave (escuro)", fg: escuro.vermelho, bg: escuro["vermelho-suave"], min: 4.5 },
    { alvo: "Borda de campos / cartão (escuro)", fg: escuro["borda-campo"], bg: escuro.cartao, min: 3.0 },
    { alvo: "Chip ativo e .help:hover (escuro)", fg: escuro["sobre-primaria"], bg: escuro.primaria, min: 4.5 },
  ];

  return pares.map((p) => {
    const razao = razaoContraste(p.fg, p.bg);
    return { ...p, razao, aprovado: razao >= p.min };
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const resultados = verificarContrastes();
  let falhas = 0;
  for (const r of resultados) {
    const status = r.aprovado ? "OK  " : "FALHA";
    if (!r.aprovado) falhas++;
    console.log(`${status}  ${r.razao.toFixed(2)}:1 (mín. ${r.min.toFixed(1)}:1) — ${r.alvo}`);
  }
  if (falhas > 0) process.exit(1);
}

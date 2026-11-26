# FinSight

**Painel inteligente de carteira e educação financeira para pequenos investidores.**

Projeto Integrador de Sistemas Inteligentes III – CST em Sistemas Inteligentes, Fatec “Shunji Nishimura” – Pompeia (2026/2).
Organização parceira: Cooperativa de Crédito Alta Paulista – CrediAlta, agência Pompeia/SP.

O FinSight reúne em um só lugar as aplicações do associado (renda fixa, ações e fundos imobiliários), mostra quanto a carteira
rendeu comparado ao **CDI** e à **inflação (IPCA)**, calcula um **índice de diversificação** e emite **alertas em linguagem simples**.
É uma ferramenta **educativa**: mede e explica, mas **não recomenda** compra ou venda de investimentos (Resolução CVM nº 30).

## Equipe 04

| Integrante | RA | Papel |
|---|---|---|
| Luiz Otavio Correia Jaloto | 2591612523011 | Product Owner e Back-end/APIs |
| Samuel Henrique Farias Dias | 2591612523012 | Front-end e UX |
| Caio Marconato Bolfarini | 2591612523025 | Banco NoSQL, redes e implantação |
| Thiago Dias de Souza Nascimento | 2591612523032 | Scrum Master e ciência de dados |
| Eduardo Augusto Oliveira Brisolla | 2591612523020 | Testes, qualidade e modelagem de negócios |

Docente: Ronaldo Fernandes Medeiros.

## Funcionalidades (v0.4.0)

| Requisito | Funcionalidade |
|---|---|
| RF01, RF02 | Cadastro com aceite do termo de privacidade e login com JWT |
| RF04 | Renda fixa em % do CDI ou IPCA + taxa (aceita “105” ou “1,05”) |
| RF05 | Ações e FIIs pelo código, com cotação atualizada |
| RF06 | Importação do CSV de posição da Área do Investidor da B3 |
| RF07 | CDI (série 12) e IPCA (série 433) direto da API SGS do Banco Central, com cache |
| RF08 | Painel: patrimônio, alocação por classe e rentabilidade comparada ao CDI e ao IPCA |
| RF09 | Índice de diversificação (HHI) em faixas e alertas de concentração (> 25%) e de vencimento (≤ 30 dias) |
| RF10 | Glossário com 22 termos, acessível pelos ícones “?” |
| RNF03 | Exportação e exclusão completa da conta (LGPD) |

**Simulações e limitações:** a carteira de demonstração é simulada; as cotações vêm da brapi.dev com até 15 minutos de atraso
(sem token, só alguns códigos são liberados – use `BRAPI_TOKEN` para todos); a comparação com o CDI e o IPCA é feita no período
de cada aplicação, ponderada pelo valor aplicado. **Não implementado:** questionário de perfil (RF03), visão do gerente e resumo em PDF.

## Arquitetura

```
Navegador ──HTTPS──> Front-end (React + TypeScript + Recharts)
                         │ REST/JSON + JWT
                         ▼
                     API (Python FastAPI, pandas) ──HTTPS──> API SGS do Banco Central (CDI, IPCA)
                         │                       └─HTTPS──> brapi.dev (cotações)
                         ▼
                     MongoDB (users, portfolios, quotes_cache, indicators, alerts)
```

```
finsight/
├── backend/            API FastAPI
│   ├── app/            rotas, cálculos (services/analytics.py), importação CSV, Banco Central
│   ├── scripts/        seed_demo.py – usuário de demonstração
│   └── tests/          pytest (casos T01–T10 do plano de testes)
├── frontend/           React + Vite
└── docker-compose.yml  MongoDB + API + front-end
```

## Como executar

### Opção 1 – Docker (mais simples)

Requisitos: Docker Desktop.

1. Copie `.env.example` para `.env` e preencha `JWT_SECRET` com um texto aleatório de pelo menos 32 caracteres.
   Para gerar um: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
   Sem isso o compose para com erro, de propósito: a API roda com `ENV=production` e não aceita chave fraca.
2. Suba os serviços e crie o usuário de demonstração:

```bash
docker compose up --build
docker compose exec backend python scripts/seed_demo.py
```

- Front-end: http://localhost:8080
- API: http://localhost:8000 (a documentação interativa fica desligada com `ENV=production`)
- Usuário de demonstração: `demo@finsight.app`, com a senha definida em `DEMO_PASSWORD` no `.env`. Sem essa variável, o seed não cria a conta em produção. O botão que preenche o e-mail da demonstração no login só aparece com `VITE_DEMO=1` no build do front-end.

### Opção 2 – Sem Docker

Requisitos: Python 3.12+, Node.js 20+ e um MongoDB (local ou MongoDB Atlas gratuito).

**Back-end**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # Linux/macOS: cp .env.example .env  – ajuste MONGO_URI e preencha JWT_SECRET
python scripts/seed_demo.py
uvicorn app.main:app --reload
```

**Front-end** (em outro terminal)

```bash
cd frontend
npm install
npm run dev                     # abre em http://localhost:5173
```

## Testes

```bash
cd backend && pytest            # 21 testes: cálculos, importação CSV e API de ponta a ponta
cd frontend && npm test         # formatação e textos de comparação
```

Os testes da API usam `mongomock` (banco em memória) e séries sintéticas do CDI e do IPCA, para não depender da internet.
A integração contínua (GitHub Actions) roda os dois conjuntos a cada push.

## Fontes de dados e licenças

- Banco Central do Brasil – Sistema Gerenciador de Séries Temporais (SGS): dados abertos, citar a fonte.
- brapi.dev – cotações da B3 com atraso, conforme os termos de uso do provedor.
- Bibliotecas: React, Recharts, Vite, FastAPI e PyJWT (MIT); pandas e numpy (BSD-3); PyMongo e bcrypt (Apache 2.0).
- Código do FinSight: licença MIT (arquivo `LICENSE`).

## Aviso

O FinSight é uma ferramenta educativa desenvolvida em contexto acadêmico. As informações exibidas não constituem recomendação de
investimento. Na dúvida, procure um profissional habilitado.

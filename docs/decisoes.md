# Decisões técnicas e de domínio

Registro das escolhas feitas durante o refinamento. Itens marcados **[validar com o docente]** foram implementados
na opção mais conservadora, mas dependem de confirmação.

## B2 – Limites de entrada **[validar com o docente]**

| Campo | Limite adotado | Motivo |
|---|---|---|
| % do CDI | maior que 0 e até 500% | Nenhum título de varejo paga acima disso; 0 ou negativo não faz sentido para pós-fixado |
| Taxa do IPCA+ | de -10% a 50% ao ano | Aceita taxa real negativa (já ocorreu em títulos públicos) sem permitir base negativa na potência, que gerava número complexo |
| Valor aplicado | até R$ 100 milhões por aplicação | Teto muito acima do público (pequenos investidores); barra erro de digitação e overflow |
| Quantidade | até 100 milhões de cotas/ações | Mesmo motivo |
| Preço médio | até R$ 1 milhão por cota/ação | Mesmo motivo |
| Data da aplicação | até hoje, no fuso de Brasília | Aplicação no futuro não tem rendimento a calcular |
| Vencimento | não anterior à data da aplicação | Consistência básica |

Valores normalizados: `1,05` no campo "% do CDI" continua sendo lido como 105% (feedback FB05 do teste de usabilidade).

Dados antigos que violem esses limites (gravados antes da validação) não derrubam o painel: o ativo aparece como
"erro de cálculo", fica fora dos totais e gera um aviso para o usuário revisar o cadastro.

## B3 – Histórico do CDI e do IPCA

- A série é buscada desde a aplicação mais antiga da carteira, menos 45 dias de margem (feriados e mês incompleto do IPCA).
  Sem aplicações, busca 400 dias (o suficiente para os 12 meses do resumo).
- O SGS recusa com HTTP 406 consultas acima de **10 anos** em séries diárias. Isso foi verificado diretamente na API em
  24/11/2026 (mensagem: "O sistema aceita uma janela de consulta de, no máximo, 10 anos em séries de periodicidade diária").
  A busca usa janelas de 9 anos para ter folga. A série mensal do IPCA (433) aceitou 16 anos numa consulta só, mas usa a mesma janela.
- Cache por faixa: cada série guarda `covers_from` (primeira data coberta). Cache com menos de 12 horas que já cobre a faixa
  é usado sem consultar a API.
- Se a API falhar, o painel usa o último cache e mostra um aviso ("Não conseguimos atualizar o CDI e o IPCA agora").
  Se não houver cache nenhum, responde 503.

## B4 – Renda fixa vencida **[validar com o docente]**

- O valor de uma renda fixa para de acumular na data do vencimento. A comparação com o CDI e o IPCA desse ativo também
  usa o período da aplicação até o vencimento, para continuar sendo uma comparação justa.
- O ativo ganha status `vencido` e um aviso próprio, que só informa que o prazo terminou. O sistema **não** presume o que
  aconteceu depois (resgate automático, reaplicação) e não sugere o que fazer.
- Dúvida para validar: depois do vencimento, o dinheiro normalmente volta para a conta do associado. Manter o ativo vencido
  somando no patrimônio é a opção conservadora (o dinheiro continua existindo); o docente pode preferir retirá-lo dos totais.
- O cálculo do IPCA+ continua usando dias corridos/365 até o vencimento; a troca por 252 dias úteis é o item D3, fora deste pacote.

## S2 – Limite de tentativas **[validar com o docente]**

| Rota | Chave | Limite | Bloqueio |
|---|---|---|---|
| `POST /auth/login` | e-mail | 5 falhas por minuto | 60 s, dobrando a cada novo estouro (teto 15 min) |
| `POST /auth/login` | IP | 20 falhas por minuto | igual |
| `POST /auth/register` | IP e e-mail | 5 pedidos por minuto | 60 s, dobrando (teto 1 h) |

- A resposta é 429 com o cabeçalho `Retry-After`. Login certo zera o contador do e-mail, mas a memória de bloqueios
  anteriores dura 24 h (é ela que faz o bloqueio seguinte ser mais longo).
- Contadores ficam no MongoDB (coleção `rate_limits`, com índice TTL), sem dependência nova. Escolhido no lugar do slowapi
  porque o contador precisa ser compartilhado entre processos do servidor e já temos o banco.
- LGPD: as chaves guardam um hash SHA-256 do e-mail e do IP, nunca o valor em texto.
- `X-Forwarded-For` só é considerado quando a conexão vem de um IP listado em `TRUSTED_PROXIES` (vazio por padrão).
  Nesse caso vale o primeiro IP não confiável lido da direita para a esquerda. Atrás do nginx do Docker, é preciso
  configurar `TRUSTED_PROXIES` com o IP do container do nginx; isso depende do item S6 (proxy de /api), fora deste pacote.
- Limitação conhecida: o contador não é estritamente atômico (leitura e escrita separadas). Em rajadas simultâneas, algumas
  tentativas a mais podem passar antes do bloqueio. Aceitável para o volume do projeto; registrado para revisão.

## S3 – Configuração e JWT

- A configuração usa `pydantic-settings` (dependência nova, versão fixa 2.16.3) e é validada na subida.
  Com `ENV=production`, a API **não sobe** se `JWT_SECRET` for o valor padrão, um valor que já apareceu em arquivo de
  exemplo, ou tiver menos de 32 caracteres. Em `development` (padrão) o valor padrão continua aceito, para facilitar o
  desenvolvimento local.
- Tokens agora levam `iss` (`finsight-api`) e `aud` (`finsight-web`), e a validação exige `exp`, `iat`, `sub`, `iss` e `aud`.
  Token sem validade, de outro emissor ou para outro público recebe 401.
- Efeito colateral esperado: tokens emitidos pela v0.4.0 (sem `iss`/`aud`) deixam de valer; o usuário só precisa entrar de novo.
- `docker-compose.yml` não tem mais valor padrão para `JWT_SECRET` (`${JWT_SECRET:?...}`) e roda a API com `ENV=production`.
  A variável fica no arquivo `.env` da raiz (modelo em `.env.example`).

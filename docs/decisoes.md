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

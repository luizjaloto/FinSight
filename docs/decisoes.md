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

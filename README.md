# Loteca — 10S / 0D / 4T — 10 / 6 / 6

Projeto para gerar **um único palpite final por concurso da Loteca**, escolhendo, entre os palpites válidos, aquele mais alinhado aos **fatores historicamente associados a P14**, sempre respeitando todas as *Hard Constraints* da estratégia.

## Objetivo

A estratégia utiliza o histórico disponível em:

```text
data/concursos_anteriores.csv
```

O objetivo central é:

> **Gerar um único palpite final por concurso, otimizado para maximizar a chance de atingir 14 acertos a partir dos fatores que mais estiveram associados a P14 nos concursos anteriores, respeitando todas as Hard Constraints.**

A proposta não é simplesmente escolher o resultado mais provável em cada partida. O projeto busca aprender características dos **bilhetes completos** associados a 14 acertos e selecionar, no próximo concurso, o palpite válido mais parecido com esse perfil.

Formalmente:

```text
Palpite* = argmax Score_P14(palpite)
```

sujeito a todas as *Hard Constraints*.

> **Importante:** o `Score_P14` atual é um **score de similaridade/ordenação**, não uma probabilidade calibrada de atingir 14 pontos.

---

## Representação probabilística

Para cada partida:

- `p(1)` — vitória do mandante;
- `p(X)` — empate;
- `p(2)` — vitória do visitante.

As três probabilidades são ordenadas para formar:

- `p(top1)` — maior probabilidade;
- `p(top2)` — segunda maior;
- `p(top3)` — menor.

Em caso de empate, o desempate segue:

```text
1 > 2 > X
```

O resultado real também é representado por:

```text
top1_hit
top2_hit
top3_hit
```

com exatamente uma variável igual a `1` por partida.

---

## Hard Constraints

Todo palpite final deve satisfazer obrigatoriamente:

1. **10 secos, 0 duplos e 4 triplos**;
2. **10 top1, 6 top2 e 6 top3** entre todas as marcações;
3. se o **FLAMENGO/RJ** participar, sua vitória deve estar obrigatoriamente incluída nas marcações.

### Consequência estrutural

Cada triplo (`1X2`) contém um `top1`, um `top2` e um `top3`.

Os quatro triplos consomem:

```text
4 top1
4 top2
4 top3
```

Logo, os dez secos obrigatoriamente precisam ser:

```text
6 secos top1
2 secos top2
2 secos top3
```

Portanto, todo palpite válido possui a estrutura:

```text
4 triplos
6 secos top1
2 secos top2
2 secos top3
```

---

## Soft Constraint

Quando não houver perda significativa de qualidade global, favorecer soluções que **excluam a vitória do PALMEIRAS/SP**, priorizando empate ou derrota.

Essa preferência nunca pode violar uma *Hard Constraint* e deve funcionar apenas como critério secundário entre soluções de qualidade semelhante.

---

## Score de similaridade P14

O score mede o quanto um palpite completo se parece com padrões históricos associados a 14 acertos.

O objetivo de longo prazo é aproximar:

```text
P(P14 | características do bilhete)
```

em vez de considerar apenas:

```text
P(acerto de um jogo | características da partida)
```

### Estrutura atual do score

A implementação atual combina:

```text
Score_total = Score_local + Score_global_P14
```

onde:

- `Score_local` agrega os scores dos secos e dos triplos;
- `Score_global_P14` mede a distância do bilhete completo ao perfil histórico agregado de bilhetes compatíveis com P14.

### Componentes locais — secos

Nos secos contribuem, entre outros:

- taxa calibrada de acerto da posição `top1/top2/top3`;
- `gap12`;
- `gap23`;
- `balance`;
- semelhança com os perfis históricos de `dry_top1`, `dry_top2` e `dry_top3` associados a P14.

### Componentes locais — triplos

Nos triplos contribuem:

- `p(top1)`, `p(top2)` e `p(top3)`;
- `gap12`;
- `gap23`;
- `balance`;
- semelhança com o perfil histórico de jogos usados como triplo em bilhetes compatíveis com P14.

### Componentes globais do bilhete

O modelo já utiliza características agregadas como:

```text
triple_top1_mean
triple_top2_mean
triple_top3_mean
triple_gap12_mean
triple_gap23_mean
triple_balance_mean

dry_top1_top1_mean
dry_top1_top2_mean
dry_top1_top3_mean
dry_top1_gap12_mean
dry_top1_gap23_mean
dry_top1_balance_mean

dry_top2_...
dry_top3_...

min_dry_probability
mean_dry_probability
product_dry_probability
```

Durante a busca, cada candidato recebe um componente global calculado pela distância padronizada até o perfil histórico P14.

Assim, as features globais **já participam diretamente da otimização**, e não apenas da telemetria.

---

## Validação histórica — walk-forward

Qualquer avaliação deve impedir vazamento de informação futura.

Para um concurso histórico `t`:

```text
concursos < t
    ↓
treinamento
    ↓
gerar um único palpite para t
    ↓
revelar o resultado real de t
    ↓
calcular pontos e métricas
```

O código deve garantir:

```python
assert max(training_contests) < target_contest
```

Também devem ser registrados:

```text
trained_until
target_contest
training_matches
training_contests
```

---

## Backtest no nível do bilhete

O projeto possui `scripts/backtest.py`, que executa validação *walk-forward* concurso a concurso.

Para cada concurso elegível, o backtest:

1. treina usando apenas concursos anteriores;
2. gera exatamente um bilhete válido;
3. calcula a pontuação real;
4. registra P14, P13+ e P12+;
5. salva `Score_P14`, `Score_local` e `Score_global_P14`;
6. salva as features agregadas do bilhete.

Saída:

```text
output/backtest.csv
```

Campos principais:

```text
Concurso
Pontos
P14
P13_plus
P12_plus
Score_P14
Score_local
Score_global_P14
trained_until
training_matches
training_contests
```

Esse arquivo é a principal base para validar se novos componentes realmente melhoram o desempenho fora da amostra.

---

## Dataset histórico de bilhetes

O `output/backtest.csv` funciona como dataset histórico com **uma linha por concurso/palpite**.

Além das métricas de desempenho, deve preservar as features agregadas necessárias para estudar:

- quais características aparecem com mais frequência em bilhetes P14;
- quais fatores diferenciam P14 de P13/P12 e dos demais;
- quais componentes ajudam apenas dentro da amostra e quais sobrevivem ao *walk-forward*.

Esse dataset deve ser tratado como unidade principal de aprendizado no nível do bilhete.

---

## P14 como alvo principal; P13/P12 como apoio

P14 continua sendo o objetivo dominante, mas é um evento raro.

P13 e P12 podem ser usados como sinais auxiliares para reduzir instabilidade estatística, sem mudar a prioridade final.

Uma possibilidade futura:

```text
Score = w14 * P(P14) + w13 * P(P13+) + w12 * P(P12+)
```

com:

```text
w14 >> w13 > w12
```

Outra opção é manter modelos separados para `P14`, `P13+` e `P12+`.

---

## Baselines obrigatórios

Toda evolução do modelo deve ser comparada com estratégias mais simples.

Baselines recomendados:

1. **Probabilístico** — maximizar a probabilidade dos secos;
2. **Equilíbrio** — usar os quatro jogos mais equilibrados como triplos;
3. **Modelo sem score global** — componente global desligado;
4. **Modelo atual completo** — score local + score global P14.

Métricas principais:

```text
P14
P13+
P12+
média de pontos
mediana
desvio-padrão
```

Também calcular:

```text
Lift_P14 = TaxaP14_modelo / TaxaP14_baseline
Lift_P13 = TaxaP13+_modelo / TaxaP13+_baseline
Lift_P12 = TaxaP12+_modelo / TaxaP12+_baseline
```

Um componente novo só deve permanecer se melhorar o desempenho de forma consistente fora da amostra.

---

## Ajuste automático de pesos

Pesos como os usados em `ticket_p14` e `Score_global_P14` não devem ser escolhidos apenas manualmente.

Uma grade inicial possível:

```text
0.00
0.01
0.02
0.025
0.05
0.10
0.20
0.50
```

Cada configuração deve ser avaliada em *walk-forward*.

A escolha deve priorizar, nesta ordem:

1. P14;
2. P13+;
3. P12+;
4. média de pontos;
5. estabilidade entre janelas temporais.

O peso vencedor deve ser escolhido exclusivamente por desempenho fora da amostra.

---

## Ablation tests

Além de comparar versões completas, o projeto deve testar o efeito de remover um componente por vez.

Exemplos:

```text
modelo completo
modelo sem ticket_p14
modelo sem score dos triplos
modelo sem Score_global_P14
modelo sem calibração por faixa
modelo sem preferência Palmeiras
```

O objetivo é responder:

> **Qual componente realmente adiciona valor ao resultado final?**

Um componente que aumenta complexidade sem melhorar P14/P13+/P12+ deve ser removido ou simplificado.

---

## Ranking dos candidatos

Além do vencedor, é recomendável salvar os melhores candidatos em:

```text
output/top_candidates.csv
```

Campos sugeridos:

```text
rank
score_total
score_local
score_global_p14
triples
dry_top1
dry_top2
dry_top3
flamengo_ok
palmeiras_win_included
delta_to_best
```

Exemplo:

```text
1º  -10.097670
2º  -10.098011
3º  -10.101203
```

indica uma decisão relativamente frágil.

Já:

```text
1º  -10.097670
2º  -10.450000
```

indica maior separação entre o vencedor e os demais.

---

## Percentil de similaridade P14

Além do score bruto, uma saída mais interpretável é comparar o bilhete atual com a distribuição histórica dos scores.

Exemplo:

```text
Score de similaridade P14: -10.097670
Percentil histórico: 87%
```

O percentil não representa probabilidade de P14, mas ajuda a responder:

> **Quão parecido este bilhete é com os perfis historicamente associados a P14, em comparação com outros bilhetes avaliados?**

---

## Decomposição do score global

O componente global não deve aparecer apenas como um número agregado.

A telemetria futura deve mostrar quais features mais ajudaram e mais prejudicaram o bilhete.

Exemplo:

```text
Perfil global P14:
triple_balance_mean      -0.003
dry_top1_gap12_mean      -0.002
dry_top2_balance_mean    -0.011
dry_top3_top3_mean       -0.004
min_dry_probability      -0.008
```

Isso facilita auditoria e detecção de features excessivamente dominantes.

---

## Estabilidade do bilhete

O palpite final também deve ser avaliado por estabilidade.

Uma forma é alterar levemente pesos ou probabilidades e medir quantas marcações mudam.

Exemplos de métricas:

```text
jogos_inalterados
secos_inalterados
triplos_inalterados
jaccard_triples
mudancas_por_1pct_probabilidade
```

Um bilhete que muda drasticamente com pequenas perturbações deve ser tratado como decisão de baixa robustez.

---

## Sensibilidade às probabilidades

As probabilidades de entrada podem conter ruído.

Por isso, é útil executar testes de sensibilidade, perturbando `p(1)`, `p(X)` e `p(2)` em pequenas magnitudes e recalculando o palpite.

Objetivo:

> **Verificar se a escolha depende de diferenças mínimas ou se permanece estável em uma vizinhança plausível das probabilidades observadas.**

Essa análise deve ser separada do treinamento principal para evitar transformar ruído artificial em sinal.

---

## Regra do Flamengo no histórico P14

A construção de exemplos históricos compatíveis com P14 também deve respeitar a regra do Flamengo.

Se o Flamengo não venceu uma partida histórica, um bilhete P14 válido que inclua obrigatoriamente sua vitória só pode acertar aquela partida se ela estiver marcada como triplo.

Portanto, a geração dos perfis históricos P14 deve tratar essa condição explicitamente.

---

## Espaço de busca

A estrutura fixa reduz o problema a:

1. escolher os 4 triplos;
2. nos 10 restantes, escolher 6 secos top1, 2 top2 e 2 top3.

O espaço bruto é:

```text
C(14, 4) × 10! / (6! × 2! × 2!)
= 1001 × 1260
= 1.261.260
```

A implementação pode usar programação dinâmica, desde que preserve o ótimo global sob as restrições.

---

## Estrutura do repositório

```text
.
├── main.py
├── data/
│   ├── concursos_anteriores.csv
│   └── proximo_concurso.csv
├── models/
├── output/
│   ├── predictions.csv
│   ├── backtest.csv
│   └── top_candidates.csv      # planejado
├── scripts/
│   ├── backtest.py
│   ├── common.py
│   ├── preprocess_data.py
│   ├── predict_results.py
│   └── train_model.py
└── tests/
```

---

## Estado atual

O projeto já possui:

- leitura dos dados históricos e do próximo concurso;
- probabilidades e ranking `top1/top2/top3`;
- corte temporal sem uso de concursos futuros;
- calibração de acerto por posição probabilística;
- perfis locais de `gap12`, `gap23` e `balance`;
- perfis P14 por papel (`triple`, `dry_top1`, `dry_top2`, `dry_top3`);
- score dos secos;
- score próprio dos triplos;
- features agregadas do bilhete;
- **Score_global_P14 participando diretamente da otimização**;
- decomposição entre `Score_local` e `Score_global_P14`;
- busca eficiente sob 10S/0D/4T;
- validação 10/6/6;
- regra obrigatória do Flamengo na seleção do concurso atual;
- preferência secundária relativa ao Palmeiras;
- backtest walk-forward com uma observação por concurso;
- registro das features do bilhete no backtest;
- testes automatizados;
- saída em `output/predictions.csv`.

### Limitações principais atuais

As prioridades agora são menos sobre adicionar novas features e mais sobre **validar e calibrar o que já existe**:

1. o peso do componente global ainda precisa ser escolhido por *walk-forward*;
2. ainda falta comparação sistemática com baselines;
3. ainda falta ranking dos melhores candidatos;
4. ainda faltam *ablation tests*;
5. ainda falta medir estabilidade/sensibilidade;
6. o `Score_P14` ainda não é uma probabilidade calibrada de P14;
7. a construção dos perfis históricos deve garantir integralmente todas as *Hard Constraints*, inclusive a regra do Flamengo.

---

## Telemetria

A execução deve mostrar informação suficiente para auditar a decisão.

### Por jogo

- `p(1)`, `p(X)`, `p(2)`;
- ranking `top1/top2/top3`;
- seco ou triplo;
- posição usada no seco;
- `calibrated_hit`;
- `gap12`;
- `gap23`;
- `balance`;
- contribuição `ticket_p14`, quando aplicável.

### Por bilhete

Exemplo atual:

```text
=== SCORE DO BILHETE ===
Score P14: ...
  componente local: ...
  perfil global P14: ...
  triple: equilíbrio médio=...
dry_top1: equilíbrio médio=...
dry_top2: equilíbrio médio=...
dry_top3: equilíbrio médio=...
```

Evolução desejada:

```text
Score de similaridade P14: ...
Percentil histórico: ...
Delta para o 2º colocado: ...

Maiores contribuições positivas: ...
Maiores penalizações: ...
Estabilidade do bilhete: ...
```

---

## Roadmap — ordem de maior retorno

1. **Otimizar automaticamente os pesos** de `ticket_p14` e `Score_global_P14` via walk-forward;
2. **comparar sistematicamente com baselines** simples e com o modelo sem score global;
3. **implementar ranking dos melhores candidatos** e `delta_to_best`;
4. **executar ablation tests** para medir a contribuição real de cada componente;
5. **adicionar percentil de similaridade P14**;
6. **decompor o Score_global_P14 por feature**;
7. **medir estabilidade e sensibilidade** do bilhete a pequenas perturbações;
8. **garantir a regra do Flamengo também na construção histórica P14**;
9. **usar P13/P12 como sinais auxiliares**, mantendo P14 dominante;
10. **calibrar futuramente `P(P14 | bilhete)`** quando houver volume suficiente de observações walk-forward.

### Pareto prático

Se apenas cinco itens forem implementados primeiro:

```text
1. ajuste automático do peso global
2. ranking dos candidatos
3. ablation tests
4. comparação com baselines
5. percentil de similaridade P14
```

Esses itens têm maior retorno agora porque ajudam a distinguir **ganho real de desempenho** de mera complexidade adicional.

---

## Execução

Palpite do próximo concurso:

```bash
python main.py
```

Testes:

```bash
python -m unittest discover -v
```

Backtest:

```bash
python scripts/backtest.py
```

---

## Princípio do projeto

O objetivo não é apenas prever partidas isoladamente.

O foco é descobrir como usar as 22 marcações disponíveis da forma historicamente mais eficiente possível para aproximar o perfil de um bilhete de 14 acertos.

```text
histórico
    ↓
probabilidades e rankings
    ↓
walk-forward
    ↓
features por jogo e por bilhete
    ↓
padrões associados a P14
    ↓
geração dos candidatos válidos
    ↓
Score_local + Score_global_P14
    ↓
Hard Constraints
    ↓
Soft Constraint
    ↓
validação contra baselines
    ↓
palpite final
```

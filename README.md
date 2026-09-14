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

O score deve medir o quanto um palpite completo se parece com padrões históricos associados a 14 acertos.

O objetivo de longo prazo é aproximar:

```text
P(P14 | características do bilhete)
```

em vez de considerar apenas:

```text
P(acerto de um jogo | características da partida)
```

### Componentes locais

Nos secos, podem contribuir:

- taxa calibrada de acerto da posição `top1/top2/top3`;
- probabilidade do resultado escolhido;
- `gap12`;
- `gap23`;
- `balance`;
- semelhança com perfis históricos de `dry_top1`, `dry_top2` e `dry_top3` associados a P14.

Nos triplos, podem contribuir:

- `p(top1)`, `p(top2)` e `p(top3)`;
- `gap12`;
- `gap23`;
- `balance`;
- semelhança com o perfil histórico de jogos usados como triplo em bilhetes compatíveis com P14.

### Componentes globais do bilhete

O modelo deve evoluir para considerar explicitamente características agregadas, por exemplo:

```text
triple_balance_mean
triple_gap12_mean
triple_gap23_mean
dry_top1_prob_mean
dry_top2_prob_mean
dry_top3_prob_mean
dry_top1_balance_mean
dry_top2_balance_mean
dry_top3_balance_mean
min_dry_probability
mean_dry_probability
product_dry_probability
```

A meta é sair de um score predominantemente aditivo por jogo e chegar a:

```text
Score_ticket = Score_secos + Score_triplos + Score_global_P14
```

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

Proteção recomendada:

```python
assert max(training_contests) < target_contest
```

Registrar também:

```text
trained_until
target_contest
training_matches
training_contests
```

---

## Backtest no nível do bilhete

O projeto possui `scripts/backtest.py`, responsável por executar validação *walk-forward* concurso a concurso. fileciteturn21file0L1-L2

A avaliação deve produzir uma observação por concurso/palpite, com métricas como:

```text
Concurso
Pontos
P14
P13_plus
P12_plus
Score_P14
trained_until
```

Além disso, deve registrar features agregadas do bilhete para permitir aprender fatores que diferenciam bilhetes de alta pontuação dos demais.

Saída esperada:

```text
output/backtest.csv
```

---

## Dataset histórico de bilhetes

Uma evolução prioritária é consolidar um dataset com uma linha por concurso, contendo:

```text
contest
points
is_p14
is_p13_plus
is_p12_plus
score
triple_balance_mean
triple_gap12_mean
triple_gap23_mean
dry_top1_prob_mean
dry_top2_prob_mean
dry_top3_prob_mean
min_dry_probability
mean_dry_probability
```

Esse dataset deve ser a base para aprender um score realmente no **nível do bilhete**.

---

## P14 como alvo principal; P13/P12 como apoio

P14 continua sendo o objetivo dominante, mas é um evento raro.

P13 e P12 podem ser usados como sinais auxiliares para reduzir instabilidade estatística, sem mudar a prioridade final.

Uma opção:

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

Toda evolução deve ser comparada com estratégias simples.

Baselines recomendados:

1. **Probabilístico** — maximizar a probabilidade dos secos;
2. **Equilíbrio** — usar os quatro jogos mais equilibrados como triplos;
3. **Modelo anterior** — score baseado apenas em calibração e perfis locais.

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

Um modelo mais complexo só deve permanecer se superar consistentemente os baselines fora da amostra.

---

## Ajuste automático de pesos

Pesos de componentes como o perfil P14 não devem ser escolhidos apenas manualmente.

Uma grade inicial sugerida:

```text
0.00
0.01
0.025
0.05
0.10
0.20
```

Cada peso deve ser avaliado em *walk-forward* e comparado por P14, P13+, P12+ e média de pontos.

A escolha do peso deve usar apenas desempenho fora da amostra.

---

## Regra do Flamengo no histórico P14

A construção de exemplos históricos compatíveis com P14 também deve respeitar a regra do Flamengo.

Se o Flamengo não venceu uma partida histórica, um bilhete P14 válido que inclua obrigatoriamente a vitória do Flamengo só pode acertar aquela partida se ela estiver marcada como triplo.

Portanto, o gerador de perfis históricos P14 deve tratar essa condição explicitamente.

---

## Ranking dos candidatos

Além do vencedor, é recomendável salvar os melhores candidatos em:

```text
output/top_candidates.csv
```

Exemplo de colunas:

```text
rank
score
triples
dry_top1
dry_top2
dry_top3
flamengo_ok
palmeiras_win_included
```

Isso ajuda a medir a robustez da decisão.

Exemplo:

```text
1º  -9.812
2º  -9.816
3º  -9.820
```

indica uma decisão mais frágil do que:

```text
1º  -9.812
2º  -10.104
```

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
│   └── backtest.csv
├── scripts/
│   ├── backtest.py
│   ├── common.py
│   ├── preprocess_data.py
│   ├── predict_results.py
│   └── train_model.py
└── tests/
```

O repositório atual já contém `backtest.py`, além dos módulos de pré-processamento, treinamento e predição. fileciteturn21file0L1-L2

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
- busca eficiente sob 10S/0D/4T;
- validação 10/6/6;
- regra obrigatória do Flamengo;
- preferência secundária relativa ao Palmeiras;
- backtest walk-forward;
- testes automatizados;
- saída em `output/predictions.csv`.

### Limitação principal atual

O score ainda combina principalmente contribuições locais e perfis por papel. O próximo salto é fazer as **features agregadas do bilhete inteiro participarem diretamente da otimização**, e não apenas da telemetria.

Também é importante calibrar os pesos por *walk-forward* e medir ganho contra baselines.

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

Exemplo:

```text
=== SCORE DO BILHETE ===
Score de similaridade P14: ...

triple:   equilíbrio médio=...
dry_top1: equilíbrio médio=...
dry_top2: equilíbrio médio=...
dry_top3: equilíbrio médio=...
```

O score deve ser tratado como **score de ordenação/similaridade**, e não como probabilidade calibrada de P14 enquanto não houver uma camada específica de calibração.

---

## Roadmap — ordem de maior retorno

1. **Backtest walk-forward robusto** com comparação automática contra baselines;
2. **dataset histórico de bilhetes** com uma linha por concurso;
3. **score global do bilhete**, usando features agregadas;
4. **ajuste automático dos pesos** por desempenho fora da amostra;
5. **correção completa da regra do Flamengo** na geração dos perfis históricos P14;
6. **P13/P12 como sinais auxiliares**, mantendo P14 dominante;
7. **ranking dos melhores candidatos**;
8. **calibração futura de `P(P14 | bilhete)`**.

### Pareto prático

Se apenas quatro itens forem implementados primeiro:

```text
1. backtest.py walk-forward
2. dataset de features de bilhete
3. Score_global_P14
4. otimização automática dos pesos
```

Esses quatro itens têm o maior potencial de transformar o projeto de um otimizador de escolhas individuais em um verdadeiro **otimizador histórico de bilhetes P14**.

---

## Execução

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
Score_P14
    ↓
Hard Constraints
    ↓
Soft Constraint
    ↓
palpite final
```

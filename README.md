# Loteca — 10S / 0D / 4T — 10 / 6 / 6

Projeto para gerar **um único palpite final por concurso da Loteca**, escolhendo, entre todos os palpites válidos, aquele mais alinhado aos **fatores historicamente associados a P14**, sempre respeitando todas as *Hard Constraints* da estratégia.

## Objetivo

A estratégia utiliza o histórico disponível em:

```text
data/concursos_anteriores.csv
```

O objetivo central é:

> **Gerar um único palpite final por concurso, otimizado para maximizar a chance de atingir 14 acertos a partir dos fatores que mais estiveram associados a P14 nos concursos anteriores, respeitando todas as Hard Constraints.**

A proposta não é simplesmente escolher o resultado de maior probabilidade em cada partida. O projeto deve aprender quais características dos **bilhetes completos** estiveram mais associadas a 14 acertos e, para cada novo concurso, selecionar o palpite válido mais semelhante a esse perfil histórico.

Formalmente:

```text
Palpite* = argmax Score_P14(palpite)
```

sujeito a todas as *Hard Constraints*.

---

## Representação probabilística

Para cada partida, são representadas as probabilidades dos três resultados possíveis:

- `p(1)` — vitória do mandante;
- `p(X)` — empate;
- `p(2)` — vitória do visitante.

As probabilidades são ordenadas da maior para a menor para formar:

- `p(top1)` — maior probabilidade;
- `p(top2)` — segunda maior probabilidade;
- `p(top3)` — menor probabilidade.

Em caso de empate, o desempate segue a prioridade:

```text
1 > 2 > X
```

O resultado real de cada partida também é representado em relação ao ranking probabilístico por *One-Hot Encoding*:

- `top1_hit`
- `top2_hit`
- `top3_hit`

Exatamente uma dessas variáveis deve ser igual a `1` por partida.

---

## Hard Constraints

Todo palpite final deve obrigatoriamente satisfazer:

1. **Exatamente 10 secos, 0 duplos e 4 triplos**;
2. **Exatamente 10 top1, 6 top2 e 6 top3** entre todas as marcações;
3. Quando o **FLAMENGO/RJ** participar do concurso, o resultado correspondente à sua vitória deve estar obrigatoriamente incluído nas marcações.

### Consequência estrutural

Cada triplo (`1X2`) contém um resultado `top1`, um `top2` e um `top3`.

Os 4 triplos já consomem:

```text
4 top1
4 top2
4 top3
```

Como o total exigido é:

```text
10 top1
6 top2
6 top3
```

os 10 secos devem necessariamente ser:

```text
6 secos top1
2 secos top2
2 secos top3
```

Portanto, todo palpite válido tem a estrutura:

```text
4 triplos
6 secos top1
2 secos top2
2 secos top3
```

---

## Soft Constraint

Quando não houver perda significativa de qualidade global da aposta, favorecer soluções que **excluam a vitória do PALMEIRAS/SP**, priorizando empate ou derrota.

Essa preferência nunca pode violar uma *Hard Constraint* e deve ser tratada apenas como critério secundário ou de desempate entre soluções de qualidade semelhante.

---

## O que significa `Score_P14`

O `Score_P14` deve medir o quanto um palpite completo se parece com os padrões históricos encontrados nos bilhetes que alcançaram 14 acertos.

O foco é aprender:

```text
P(P14 | características do bilhete)
```

em vez de apenas:

```text
P(acerto de um jogo | características da partida)
```

O score pode combinar fatores dos secos, dos triplos e do bilhete como um todo.

### Fatores dos secos

Exemplos:

- probabilidade do resultado escolhido;
- `p(top1) - p(top2)`;
- `p(top2) - p(top3)`;
- grau de equilíbrio da partida;
- probabilidade média dos 6 secos `top1`;
- probabilidade média dos 2 secos `top2`;
- probabilidade média dos 2 secos `top3`;
- menor probabilidade entre os secos;
- produto ou soma dos logaritmos das probabilidades dos secos.

### Fatores dos triplos

Exemplos:

- `balance` médio dos 4 triplos;
- `gap12` médio dos 4 triplos;
- `gap23` médio dos 4 triplos;
- probabilidade média de `top1` nos jogos triplicados;
- entropia média dos jogos triplicados;
- frequência com que P14 ocorreu usando triplos em jogos com perfil semelhante.

A pergunta específica é:

> **Este jogo tem características historicamente compatíveis com um bom uso de triplo em bilhetes P14?**

Isso é diferente de apenas considerar que um jogo é ruim para ser usado como seco.

### Fatores globais do bilhete

Exemplos:

- média e dispersão das probabilidades dos secos;
- média de equilíbrio de todos os 14 jogos;
- perfil conjunto dos 4 triplos;
- perfil conjunto dos 6 secos `top1`;
- perfil conjunto dos 2 secos `top2`;
- perfil conjunto dos 2 secos `top3`;
- interação entre distribuição dos secos e dos triplos.

---

## Validação histórica — walk-forward

A avaliação deve impedir qualquer vazamento de informação futura.

Para um concurso histórico `t`:

```text
concursos < t
    ↓
treinamento / padrões históricos
    ↓
gerar um único palpite para t
    ↓
revelar o resultado real de t
    ↓
calcular a pontuação obtida
```

O próprio concurso avaliado e concursos posteriores jamais podem participar do treinamento usado para gerar o palpite daquele concurso.

Uma proteção explícita recomendada é:

```python
assert max(training_contests) < target_contest
```

Também é recomendável registrar no resultado do backtest:

```text
trained_until
target_contest
training_matches
training_contests
```

---

## Backtest no nível do bilhete

O projeto deve possuir uma camada explícita de backtest com **uma observação por concurso/palpite**, e não apenas estatísticas isoladas por partida.

Fluxo esperado:

```text
para cada concurso t:

1. usar somente concursos < t
2. gerar um único palpite válido para t
3. comparar com o resultado real
4. contar os acertos
5. extrair features do bilhete completo
6. armazenar o resultado
```

Saída sugerida:

```text
output/backtest.csv
```

Exemplos de colunas:

```text
Concurso
Pontos
P14
P13_plus
P12_plus
Score_P14
trained_until
triple_mean_balance
triple_mean_gap12
triple_mean_gap23
dry_top1_mean_prob
dry_top2_mean_prob
dry_top3_mean_prob
min_dry_probability
mean_dry_probability
```

Esse dataset é a base para descobrir quais fatores realmente diferenciam bilhetes de alta pontuação dos demais.

---

## Alvo principal e regularização por P13/P12

P14 é o objetivo principal, mas é naturalmente um evento raro.

Para reduzir instabilidade estatística, P13 e P12 podem ser utilizados como sinais auxiliares, sem mudar o objetivo final.

Uma opção é utilizar modelos separados:

```text
modelo_P14
modelo_P13_plus
modelo_P12_plus
```

com score agregado:

```text
Score = w14 * P(P14) + w13 * P(P13+) + w12 * P(P12+)
```

respeitando:

```text
w14 >> w13 > w12
```

Outra opção é utilizar um alvo hierárquico, desde que P14 mantenha peso claramente dominante.

---

## Baselines obrigatórios

Toda evolução do modelo deve ser comparada a estratégias simples.

Baselines recomendados:

1. **Baseline probabilístico** — maximizar a probabilidade dos secos;
2. **Baseline de equilíbrio** — colocar os 4 triplos nos 4 jogos mais equilibrados;
3. **Modelo atual** — score por taxa calibrada de acerto por posição/faixa de probabilidade.

As principais métricas de comparação devem ser:

```text
P14
P13+
P12+
média de pontos
mediana de pontos
desvio-padrão
```

Também deve ser calculado o ganho relativo (*lift*):

```text
Lift_P14 = TaxaP14_modelo / TaxaP14_baseline
```

Um modelo mais complexo só deve ser mantido se superar de forma consistente os baselines em validação histórica sem vazamento.

---

## Espaço de busca

A estrutura fixa reduz o problema a duas decisões:

1. escolher quais 4 dos 14 jogos serão triplos;
2. nos 10 jogos restantes, escolher exatamente:
   - 6 secos `top1`;
   - 2 secos `top2`;
   - 2 secos `top3`.

O número bruto de combinações estruturais é:

```text
C(14, 4) × 10! / (6! × 2! × 2!)
= 1001 × 1260
= 1.261.260
```

A implementação pode usar programação dinâmica ou outra forma equivalente para evitar materializar desnecessariamente todas as combinações, desde que o ótimo global dentro das restrições seja preservado.

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
│   └── backtest.csv          # planejado
├── scripts/
│   ├── common.py
│   ├── preprocess_data.py
│   ├── train_model.py
│   ├── predict_results.py
│   └── backtest.py           # planejado
└── tests/
```

---

## Responsabilidades dos módulos

### `scripts/common.py`

Responsável por funções e estruturas compartilhadas, como:

- leitura e validação dos dados;
- ranking `top1/top2/top3`;
- normalização de nomes de equipes;
- representação das partidas;
- validação final das *Hard Constraints*.

### `scripts/preprocess_data.py`

Responsável pelo pré-processamento dos dados, incluindo:

- leitura dos CSVs;
- conversão das odds;
- cálculo ou organização de `p(1)`, `p(X)` e `p(2)`;
- ranking `top1`, `top2`, `top3`;
- criação de `top1_hit`, `top2_hit`, `top3_hit`;
- geração de features por partida.

### `scripts/train_model.py`

Responsável por aprender padrões históricos sem utilizar concursos futuros.

No estado atual, o módulo aprende principalmente taxas calibradas de acerto por posição probabilística e perfis de `gap12`, `gap23` e `balance` no nível da partida.

A evolução prioritária é adicionar aprendizado no **nível do bilhete completo**, permitindo estimar um verdadeiro `Score_P14`.

### `scripts/predict_results.py`

Responsável por:

- gerar ou percorrer candidatos válidos;
- aplicar todas as *Hard Constraints*;
- aplicar o score do modelo;
- tratar a *Soft Constraint* do Palmeiras;
- selecionar um único palpite final;
- validar explicitamente o bilhete vencedor.

A evolução prioritária é fazer o score considerar explicitamente:

```text
Score_ticket = Score_secos + Score_triplos + Score_global_P14
```

### `scripts/backtest.py` — planejado

Responsável por:

- executar validação *walk-forward* concurso a concurso;
- gerar um único palpite histórico por concurso;
- calcular P14, P13+, P12+ e pontos;
- extrair features do bilhete;
- produzir `output/backtest.csv`;
- comparar modelo e baselines.

### `main.py`

Responsável por orquestrar o fluxo do concurso atual, treinar o modelo usando apenas dados anteriores, selecionar o palpite, validar as restrições e exibir a telemetria de auditoria.

---

## Estado atual da implementação

O projeto já possui:

- leitura dos dados históricos e do próximo concurso;
- probabilidades e ranking `top1/top2/top3`;
- corte temporal por concurso;
- score calibrado no nível de cada partida;
- busca eficiente sob as restrições 10S/0D/4T;
- validação 10/6/6;
- regra obrigatória do Flamengo;
- preferência secundária relativa ao Palmeiras;
- saída `output/predictions.csv`;
- testes automatizados.

### Limitação atual principal

O score atual ainda é predominantemente construído no **nível da partida**.

Ele aprende algo próximo de:

```text
P(top1/top2/top3 acertar | faixa de probabilidade e perfil da partida)
```

O objetivo final do projeto, porém, é aprender:

```text
P(P14 | características do bilhete completo)
```

Portanto, a prioridade do desenvolvimento é migrar o critério de seleção de um somatório de scores de jogos para um verdadeiro **score histórico de bilhete associado a P14**.

---

## Telemetria

A execução deve exibir informação suficiente para auditar a escolha final.

### Por jogo

- `p(1)`, `p(X)` e `p(2)`;
- ranking `top1`, `top2`, `top3`;
- resultado correspondente a cada posição;
- seco ou triplo;
- posição usada no seco;
- fatores que contribuíram para o score.

### Por bilhete

A evolução do projeto deve incluir um resumo semelhante a:

```text
=== SCORE DO BILHETE ===

Score total: ...

Contribuições:
Secos top1:       ...
Secos top2:       ...
Secos top3:       ...
Perfil triplos:   ...
Perfil global:    ...
Score P14:        ...
```

Também deve listar:

```text
Fatores mais favoráveis
Fatores mais desfavoráveis
```

além da validação completa das restrições.

---

## Ranking dos melhores candidatos

Além do palpite vencedor, é recomendável salvar os melhores candidatos em:

```text
output/top_candidates.csv
```

Exemplos de campos:

```text
rank
score_p14
triples
dry_top1
dry_top2
dry_top3
flamengo_ok
palmeiras_win_included
```

Isso permite medir a robustez da decisão.

Se os melhores scores forem muito próximos, a escolha final é frágil. Se o vencedor estiver claramente separado dos demais, o sinal do modelo é mais forte.

---

## Formato dos dados

Os arquivos:

```text
data/concursos_anteriores.csv
data/proximo_concurso.csv
```

utilizam:

```text
delimitador de colunas: ;
separador decimal nas odds: ,
```

---

## Formato do palpite

### Secos

```text
1
X
2
```

### Duplos

A estratégia atual exige zero duplos, mas o formato suportado é:

```text
1X
12
X2
```

### Triplos

```text
1X2
```

---

## Saídas

### Atual

```text
output/predictions.csv
```

Contém o único palpite final selecionado para o concurso analisado.

### Planejadas

```text
output/backtest.csv
output/top_candidates.csv
```

O palpite final deve sempre passar por validação explícita das *Hard Constraints* antes de ser aceito.

---

## Execução

O projeto utiliza Python 3.10 ou superior.

```bash
python main.py
```

A execução atual:

1. identifica o concurso de entrada;
2. treina usando somente concursos anteriores;
3. calcula o score dos candidatos sob as restrições;
4. seleciona um único palpite final;
5. valida todas as *Hard Constraints*;
6. grava `output/predictions.csv`.

Para executar os testes:

```bash
python -m unittest discover -v
```

---

## Roadmap de maior retorno

Prioridade recomendada:

### 1. Backtest walk-forward completo

Criar `scripts/backtest.py` e `output/backtest.csv`.

### 2. Features no nível do bilhete

Transformar cada palpite histórico em uma observação com características dos secos, triplos e composição global.

### 3. Score_P14 explícito

Treinar o modelo para diferenciar bilhetes P14 dos demais e incluir P13/P12 apenas como regularização auxiliar.

### 4. Score próprio dos triplos

Avaliar diretamente se cada jogo possui perfil historicamente adequado para consumir uma das quatro marcações triplas.

### 5. Baselines e lift

Comparar automaticamente cada evolução com estratégias simples e com o modelo atual.

### 6. Ranking dos melhores candidatos

Salvar os melhores candidatos e medir quão distante o vencedor está das alternativas.

### 7. Telemetria global do bilhete

Explicar quais fatores do bilhete aumentaram ou reduziram o `Score_P14`.

---

## Princípio do projeto

O objetivo não é apenas prever partidas isoladamente.

O foco é utilizar as 22 marcações disponíveis da estratégia da forma historicamente mais eficiente possível para buscar P14.

```text
histórico
    ↓
probabilidades e rankings
    ↓
backtest de bilhetes completos
    ↓
fatores associados a P14
    ↓
Score_P14
    ↓
geração/avaliação dos palpites válidos
    ↓
Hard Constraints
    ↓
Soft Constraint
    ↓
palpite final
```

Em resumo:

> **Escolher, entre todos os palpites válidos, aquele cujo perfil completo mais se aproxima dos padrões que historicamente mais estiveram associados a 14 acertos.**

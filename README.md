# Loteca — 10S / 0D / 4T — 10 / 6 / 6

Projeto para gerar **um único palpite final por concurso da Loteca**, escolhendo, entre os palpites válidos, aquele que mais se parece com os **padrões históricos associados a P14**, sempre respeitando todas as *Hard Constraints* da estratégia.

## Objetivo

A estratégia é baseada no histórico disponível em:

```text
data/concursos_anteriores.csv
```

O objetivo central é:

> **Escolher o palpite válido que mais se parece com os padrões históricos associados a P14, respeitando todas as Hard Constraints.**

A proposta não é apenas escolher o resultado de maior probabilidade em cada jogo. O projeto busca aprender, a partir dos concursos anteriores, quais características dos palpites estiveram mais associadas a pontuações máximas e usar esses padrões para selecionar o palpite do próximo concurso.

---

## Representação probabilística

Para cada partida, são representadas as probabilidades dos três resultados possíveis:

- `p(1)` — vitória do mandante;
- `p(X)` — empate;
- `p(2)` — vitória do visitante.

Em seguida, as três probabilidades são ordenadas da maior para a menor para formar:

- `p(top1)` — maior probabilidade;
- `p(top2)` — segunda maior probabilidade;
- `p(top3)` — menor probabilidade.

Em caso de probabilidades iguais, o desempate segue a prioridade:

```text
1 > 2 > X
```

O resultado real de cada partida também é representado em relação a esse ranking probabilístico por *One-Hot Encoding*:

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

Portanto, os 4 triplos já consomem:

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

os 10 secos devem obrigatoriamente ser distribuídos como:

```text
6 secos top1
2 secos top2
2 secos top3
```

Assim, qualquer palpite válido tem necessariamente a estrutura:

```text
4 triplos
6 secos top1
2 secos top2
2 secos top3
```

---

## Soft Constraint

Quando não houver perda significativa de qualidade global da aposta, favorecer soluções que **excluam a vitória do PALMEIRAS/SP**, priorizando empate ou derrota.

A preferência pelo Palmeiras não pode violar nenhuma *Hard Constraint*.

---

## Critério de seleção

O projeto deve avaliar os palpites válidos e selecionar aquele com maior similaridade aos padrões históricos associados a P14.

Formalmente:

```text
Palpite* = argmax Similaridade(palpite, padrões históricos de P14)
```

sujeito às *Hard Constraints*.

A função de similaridade pode ser construída a partir de fatores derivados das probabilidades e da composição do palpite, por exemplo:

- `p(top1)`, `p(top2)` e `p(top3)`;
- diferença entre `p(top1)` e `p(top2)`;
- diferença entre `p(top2)` e `p(top3)`;
- grau de equilíbrio da partida;
- perfil probabilístico dos jogos escolhidos como triplos;
- perfil dos secos `top1`;
- perfil dos secos `top2`;
- perfil dos secos `top3`;
- características agregadas do bilhete.

A prioridade é identificar fatores que, no histórico, estejam mais associados a P14 e a pontuações altas.

---

## Validação histórica

A avaliação deve evitar vazamento de informação futura.

Para um concurso histórico `t`, os padrões utilizados para gerar o palpite devem ser derivados apenas dos concursos anteriores:

```text
concursos < t
    ↓
padrões históricos
    ↓
palpite do concurso t
    ↓
resultado real do concurso t
    ↓
pontuação obtida
```

Esse processo permite avaliar a estratégia em esquema *walk-forward*.

O resultado real do concurso avaliado não deve participar da construção do palpite daquele mesmo concurso.

---

## Espaço de busca

A estrutura fixa da estratégia reduz o problema a duas decisões:

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

Esse espaço permite, em princípio, avaliar exaustivamente todos os palpites estruturalmente válidos antes da aplicação das demais restrições.

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
│   └── predictions.csv
└── scripts/
    ├── common.py
    ├── preprocess_data.py
    ├── train_model.py
    └── predict_results.py
```

### Responsabilidades previstas

#### `scripts/preprocess_data.py`

Responsável pelo pré-processamento dos dados, incluindo:

- leitura dos CSVs;
- conversão das odds;
- cálculo ou organização de `p(1)`, `p(X)` e `p(2)`;
- ranking `top1`, `top2`, `top3`;
- criação de `top1_hit`, `top2_hit`, `top3_hit`;
- geração de fatores derivados utilizados pelo modelo.

#### `scripts/train_model.py`

Responsável por aprender os padrões históricos associados a P14 e pontuações altas, respeitando a separação temporal necessária para o *walk-forward*.

#### `scripts/predict_results.py`

Responsável por:

- gerar os candidatos estruturalmente válidos;
- aplicar as *Hard Constraints*;
- calcular o score de similaridade histórica;
- aplicar a *Soft Constraint* quando apropriado;
- selecionar um único palpite final.

#### `main.py`

Responsável por orquestrar o fluxo completo do projeto e exibir a telemetria necessária para auditoria.

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

Embora a estratégia atual exija zero duplos, o formato previsto é:

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

## Telemetria

A execução deve exibir informação suficiente para auditar o palpite final, incluindo:

- probabilidades `p(1)`, `p(X)` e `p(2)`;
- ranking `top1`, `top2`, `top3`;
- resultado correspondente a cada posição do ranking;
- jogos escolhidos como secos e triplos;
- posição `top1`, `top2` ou `top3` utilizada nos secos;
- contagem final de `top1`, `top2` e `top3`;
- verificação das *Hard Constraints*;
- aplicação da regra do Flamengo;
- aplicação, quando cabível, da preferência relativa ao Palmeiras;
- score de similaridade histórica;
- fatores que mais contribuíram para o score do palpite vencedor.

---

## Saída

O projeto deve gerar um único palpite final para o concurso analisado e registrar as previsões em:

```text
output/predictions.csv
```

O palpite final deve sempre passar por uma validação explícita das *Hard Constraints* antes de ser considerado válido.

---

## Princípio do projeto

O objetivo não é apenas prever partidas isoladamente.

O foco é otimizar o uso das marcações disponíveis da Loteca, procurando a configuração válida que mais se aproxima dos padrões historicamente associados a **14 acertos**.

Em resumo:

```text
histórico
    ↓
probabilidades e rankings
    ↓
padrões associados a P14
    ↓
geração de palpites válidos
    ↓
score de similaridade
    ↓
Hard Constraints
    ↓
Soft Constraint
    ↓
palpite final
```

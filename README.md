# Painel do Orçamento Federal

Painel de acompanhamento da execução da despesa da União (Orçamentos Fiscal e da Seguridade Social), com destaque para as emendas parlamentares. Exercícios de 2020 em diante.

Orza Estudos e Assessoria · Cesar Lima

## O que o painel mostra

- **Execução da despesa**: dotação inicial e atualizada, empenhado, liquidado e pago; mapa por UF com clique para filtrar; segregação entre despesas obrigatórias, discricionárias e impositivas (resultado primário); série histórica; alerta de baixa execução; detalhamento por órgão, função, ação, GND, modalidade de aplicação, resultado primário e UF.
- **Emendas parlamentares**: mapa por UF de destino ou do autor; execução por partido, autor, tipo de emenda, ação e função; transferências especiais; restos a pagar pagos; valores por habitante; quadros de GND e modalidade das programações RP 6 a 9.
- Filtros por exercício, UF, partido, autor, resultado primário, GND, modalidade, ação, órgão e função. Todas as tabelas podem ser baixadas em Excel.

## Fontes

| Dado | Fonte |
|---|---|
| LOA e execução por programação | SIOP, dados abertos (`loaAAAA.csv.gz`) |
| Emendas por autor e localidade | Portal da Transparência, consulta de emendas parlamentares |
| Partido dos autores | Dados abertos da Câmara dos Deputados e do Senado Federal |
| População por UF | IBGE (Censo 2022 e estimativas anuais) |

A UF da LOA vem do localizador do gasto (subtítulo). Programações nacionais, multirregionais ou no exterior aparecem separadas do mapa. O partido é o da legislatura em que a emenda foi apresentada (56ª até a LOA 2023, 57ª a partir da LOA 2024).

## Atualização automática

O fluxo `.github/workflows/atualizar.yml` roda de segunda a sábado às 6h30 (horário de Brasília):

1. `pipeline/coleta_siop.py` baixa a LOA do exercício corrente no SIOP e agrega por resultado primário, órgão, função, ação, GND, modalidade e UF.
2. `pipeline/coleta_emendas.py` baixa as emendas de todos os exercícios no Portal da Transparência (os restos a pagar mudam todo dia).
3. `pipeline/coleta_parlamentares.py` atualiza os partidos.
4. `pipeline/montar.py` gera o site em `site/` e o publica no GitHub Pages.

Se uma fonte estiver fora do ar, o painel continua com os últimos dados coletados, guardados em `raw/`. Para rodar à mão: aba **Actions**, fluxo **Atualizar painel**, botão **Run workflow**.

## Rodar localmente

```bash
python pipeline/coleta_siop.py 2026      # opcional: um exercício específico
python pipeline/coleta_emendas.py 2026
python pipeline/montar.py
python -m http.server -d site 8000      # abrir http://localhost:8000
```

Não há dependências além do Python 3.10 ou superior.

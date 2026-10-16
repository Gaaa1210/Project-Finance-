# Project Finance — Painel da Carteira

Site para acompanhar meus investimentos no Brasil (ações, ETFs, FIIs, renda fixa e fundos).
Eu só digito o que comprei e por quanto; o app calcula o resto.
Ele abre no iPhone pelo Safari, com "Adicionar à Tela de Início".

> Ferramenta de acompanhamento e estudo. **Não é recomendação de investimento.**

## Como o projeto funciona

```
 iPhone (Safari)                     Servidor Python (FastAPI)              Fontes grátis
┌────────────────┐   pede dados    ┌──────────────────────────┐   busca   ┌────────────────────┐
│  Telas em      │ ──────────────► │ lê a planilha e calcula  │ ────────► │ Yahoo (cotações)   │
│  React         │ ◄────────────── │ tudo em Python           │ ◄──────── │ Banco Central (CDI)│
└────────────────┘   resultados    └──────────────────────────┘           │ CVM (fundos)       │
                                                                          └────────────────────┘
```

## Estrutura de pastas

```
Project-Finance-/
├── README.md                     ← este arquivo
├── .gitignore                    ← o que NÃO vai para o GitHub (sua planilha real, senhas)
│
├── backend/                      ← todo o Python
│   ├── requirements.txt          ← lista de bibliotecas para instalar
│   ├── criar_planilha_exemplo.py ← cria data/carteira.xlsx com dados de exemplo
│   ├── etapa1.py                 ← roda a Etapa 1 no terminal
│   ├── data/
│   │   └── carteira.xlsx         ← SUA planilha (abas: acoes, renda_fixa, fundos)
│   ├── carteira/                 ← o "motor" do app
│   │   ├── planilha.py           ← lê e confere a planilha
│   │   ├── cotacoes.py           ← busca preços e proventos no Yahoo Finance
│   │   ├── calculos_acoes.py     ← contas de ações/ETFs/FIIs (preço médio, lucro...)
│   │   ├── acoes.py              ← junta planilha + cotações + contas
│   │   ├── formatacao.py         ← mostra R$ 1.234,56 e +12,34%
│   │   └── dados_exemplo.py      ← preços FICTÍCIOS para testar sem internet
│   └── tests/
│       └── test_etapa1.py        ← testes automáticos dos cálculos
│
└── frontend/                     ← telas em React (Etapa 4)
```

Arquivos que ainda serão criados:
- Etapa 2: `carteira/indices_bcb.py` (CDI, Selic, IPCA) e `carteira/calculos_renda_fixa.py`
- Etapa 3: `carteira/fundos.py` (cotas da CVM)
- Etapa 4: `backend/api.py` (servidor FastAPI) e a pasta `frontend/` (React)
- Etapa 5: conexão com Google Sheets, publicação e configuração no iPhone

## Etapas

| Etapa | O que faz | Status |
|------|-----------|--------|
| 1 | Planilha + ações, ETFs e FIIs | ✅ pronta |
| 2 | Renda fixa (CDB, LCI, LCA, Tesouro) | ⏳ |
| 3 | Fundos de investimento | ⏳ |
| 4 | Servidor Python + telas em React | ⏳ |
| 5 | Google Sheets, publicação e iPhone | ⏳ |

## Etapa 1 — como instalar e rodar

Precisa do **Python 3.11 ou mais novo** ([python.org](https://www.python.org/downloads/)).

```bash
# 1. Baixe o projeto e entre na pasta do backend
git clone https://github.com/Gaaa1210/Project-Finance-.git
cd Project-Finance-/backend

# 2. Crie um "ambiente virtual" (uma caixinha só deste projeto para as bibliotecas)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# 3. Instale as bibliotecas
pip install -r requirements.txt

# 4. Crie a planilha de exemplo
python criar_planilha_exemplo.py

# 5. Rode!
python etapa1.py --offline   # preços fictícios, para testar sem internet
python etapa1.py             # preços reais do Yahoo Finance

# 6. Rode os testes automáticos
python -m unittest discover tests -v
```

### Colocando suas compras reais

Abra `backend/data/carteira.xlsx` no Excel, vá na aba **acoes**, apague os exemplos e
coloque uma linha por compra:

| ticker | tipo | setor | quantidade | preco_pago | data_compra | taxas |
|--------|------|-------|-----------:|-----------:|-------------|------:|
| PETR4  | Ação | Petróleo e Gás | 100 | 36,50 | 10/03/2025 | 4,90 |

- `ticker`: sem ".SA" (o app adiciona sozinho).
- `tipo`: `Ação`, `ETF` ou `FII`.
- `setor` e `taxas` são opcionais.
- Comprou o mesmo ativo várias vezes? Uma linha por compra; o preço médio é automático.

A planilha **não vai para o GitHub** (está no `.gitignore`), para seus dados ficarem privados.

## Limitações (honestas)

- Cotações do Yahoo têm ~15 minutos de atraso.
- Proventos do Yahoo são **brutos** (o JCP tem 15% de IR retido na fonte) e às vezes faltam
  pagamentos de ativos brasileiros.
- Por enquanto o app só considera **compras**; vendas ainda não são suportadas.
- O preço médio inclui as taxas, como pede a Receita Federal.

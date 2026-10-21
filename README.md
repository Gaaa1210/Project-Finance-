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
│   ├── api.py                    ← servidor FastAPI que entrega os dados às telas
│   ├── testar_noticias.py        ← testa as notícias no terminal
│   ├── atualizar_cvm.py          ← baixa os balanços da CVM para o banco de dados
│   ├── testar_cvm.py             ← mostra os números anuais de uma empresa
│   ├── testar_analise.py         ← mostra Raio-X, alertas e valuation no terminal
│   ├── data/
│   │   ├── carteira.xlsx         ← SUA planilha (abas: acoes, renda_fixa, fundos)
│   │   ├── cvm.sqlite            ← banco com os balanços da CVM (criado pelo atualizar_cvm.py)
│   │   └── cvm/                  ← arquivos .zip baixados da CVM
│   ├── carteira/                 ← o "motor" do app
│   │   ├── planilha.py           ← lê e confere a planilha
│   │   ├── cotacoes.py           ← busca preços e proventos no Yahoo Finance
│   │   ├── calculos_acoes.py     ← contas de ações/ETFs/FIIs (preço médio, lucro...)
│   │   ├── acoes.py              ← junta planilha + cotações + contas
│   │   ├── formatacao.py         ← mostra R$ 1.234,56 e +12,34%
│   │   ├── servico.py            ← prepara os dados de cada tela (vira JSON)
│   │   ├── empresas.py           ← lista de empresas da aba Notícias (edite à vontade)
│   │   ├── noticias.py           ← busca no Google Notícias e escolhe as mais em alta
│   │   ├── credibilidade.py      ← veículos confiáveis + filtro de títulos sensacionalistas
│   │   ├── cvm.py                ← baixa e guarda os balanços da CVM (SQLite)
│   │   ├── demonstrativos.py     ← série anual + últimos 12 meses + quantidade de ações
│   │   ├── mercado.py            ← taxa livre de risco (Banco Central) e beta (Yahoo)
│   │   ├── indicadores.py        ← indicadores, semáforo, conclusões e sinais de alerta
│   │   ├── valuation.py          ← fluxo de caixa descontado em 3 cenários (bancos: P/VP justo)
│   │   ├── analise.py            ← junta tudo para a tela da empresa
│   │   └── dados_exemplo.py      ← preços FICTÍCIOS para testar sem internet
│   └── tests/
│       └── test_etapa1.py        ← testes automáticos dos cálculos
│
└── frontend/                     ← telas em React (Vite)
    ├── package.json              ← lista de bibliotecas do React
    ├── vite.config.js            ← liga o React ao servidor Python (/api)
    └── src/
        ├── App.jsx               ← escolhe qual tela mostrar
        ├── api.js                ← conversa com o servidor Python
        ├── estilos.css           ← visual (estilo iOS, modo claro e escuro)
        ├── componentes/          ← moldura do iPhone 17, abas, gráficos
        └── telas/                ← Início, Ativos, Detalhe, Empresas, Empresa (Análise/Valuation/Notícias)...
```

Arquivos que ainda serão criados:
- Etapa 2: `carteira/indices_bcb.py` (CDI, Selic, IPCA) e `carteira/calculos_renda_fixa.py`
- Etapa 3: `carteira/fundos.py` (cotas da CVM)
- Etapa 5: conexão com Google Sheets, publicação e configuração no iPhone

## Etapas

| Etapa | O que faz | Status |
|------|-----------|--------|
| 1 | Planilha + ações, ETFs e FIIs | ✅ pronta |
| 2 | Renda fixa (CDB, LCI, LCA, Tesouro) | ⏳ |
| 3 | Fundos de investimento | ⏳ |
| 4 | Servidor Python + telas em React | 🟡 telas prontas (ações, ETFs e FIIs) |
| 5 | Google Sheets, publicação e iPhone | ⏳ |

## Etapa 1 — como instalar e rodar

Precisa do **Python 3.11 ou mais novo** ([python.org](https://www.python.org/downloads/)).

No Mac, use sempre **`python3`** (o comando `python` não existe no Mac e dá
`command not found`).

```bash
# 1. Entre na pasta do backend.
#    ATENÇÃO: o caminho tem espaço ("Project Finance"), então use ASPAS.
cd "$HOME/Documents/Project Finance/Project-Finance-/backend"

# 2. Crie um "ambiente virtual" (uma caixinha só deste projeto para as bibliotecas)
python3 -m venv .venv

# 3. Ative o ambiente (o começo da linha do terminal passa a mostrar "(.venv)")
source .venv/bin/activate

# 4. Instale as bibliotecas
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# 5. Crie a planilha de exemplo
python3 criar_planilha_exemplo.py

# 6. Rode!
python3 etapa1.py --offline   # preços fictícios, para testar sem internet
python3 etapa1.py             # preços reais do Yahoo Finance

# 7. Rode os testes automáticos
python3 -m unittest discover tests -v
```

Toda vez que abrir um terminal novo, repita os passos 1 e 3 (entrar na pasta e ativar
o `.venv`) antes de rodar o projeto.

### Problemas comuns no Mac

| Mensagem | O que fazer |
|----------|-------------|
| `zsh: command not found: python` | Use `python3` no lugar de `python`. |
| `cd: no such file or directory` | Faltaram as aspas no caminho com espaço. |
| Abre uma janela pedindo "ferramentas de linha de comando" | Clique em **Instalar**, espere terminar e rode o comando de novo. |
| `command not found: python3` | Instale o Python em [python.org](https://www.python.org/downloads/). |
| `ModuleNotFoundError: No module named 'pandas'` | O `.venv` não está ativado: rode `source .venv/bin/activate`. |
| `externally-managed-environment` | Mesmo caso: ative o `.venv` antes do `pip install`. |

## Etapa 4 — as telas (React) no navegador

São **dois programas** rodando ao mesmo tempo, cada um no seu Terminal:
o servidor Python (os cálculos) e o React (as telas).

Precisa do **Node.js** (para o React). Confira com `node --version`.
Se aparecer `command not found`, instale a versão LTS em [nodejs.org](https://nodejs.org/).

**Terminal 1 — servidor Python:**

```bash
cd "$HOME/Documents/Project Finance/Project-Finance-/backend"
source .venv/bin/activate
python3 -m pip install -r requirements.txt   # só na 1ª vez (instala FastAPI e Uvicorn)
python3 api.py --offline                     # ou: python3 api.py  (preços reais)
```

Deixe esse Terminal aberto. Teste em http://localhost:8000/api/saude
(deve aparecer `{"ok":true,...}`). A página http://localhost:8000/docs mostra a API.

**Terminal 2 — telas em React** (abra outra janela com ⌘ + N):

```bash
cd "$HOME/Documents/Project Finance/Project-Finance-/frontend"
npm install      # só na 1ª vez (baixa o React)
npm run dev
```

Abra **http://localhost:5173** no navegador. No computador o app aparece dentro de
um iPhone 17. Para desligar qualquer um dos dois: `Ctrl + C` no Terminal dele.

**Ver no iPhone de verdade (mesmo Wi-Fi):** o Terminal 2 mostra uma linha
`Network: http://192.168.x.x:5173`. Abra esse endereço no Safari do iPhone →
Compartilhar → **Adicionar à Tela de Início**. Funciona enquanto o Mac estiver ligado
com os dois Terminais rodando (publicar na internet é a Etapa 5).

O que já funciona: Início, Ativos, Detalhe (gráfico com preço médio, compras e
proventos), Desempenho (retorno por ativo) e Adicionar (grava a compra no `carteira.xlsx`).
Renda fixa, fundos e a comparação com CDI/Ibovespa/IPCA entram nas Etapas 2 e 3.

> Dica: feche o `carteira.xlsx` no Excel antes de adicionar compras pelo app.
> Se o Excel salvar uma versão antiga por cima, a compra nova some.

## Aba Notícias

Mostra as empresas da sua carteira e uma lista de empresas da B3, com uma barra de busca.
Tocando numa empresa, o app traz as **20 notícias mais em alta** dela, só de fontes confiáveis.

- **De onde vêm:** Google Notícias (feed RSS, grátis), últimos 7 dias, em duas buscas:
  - **Brasil** (em português): Valor, Estadão, Folha, O Globo, g1, InfoMoney, Exame, Brazil Journal...
  - **Internacional** (em inglês): Reuters, Bloomberg, Financial Times, WSJ, CNBC, BBC...
    Só para empresas com `busca_en` em `carteira/empresas.py` (as grandes).
  Se houver menos de 20 histórias, o app amplia para 30 dias.
- **Filtro de credibilidade** (`carteira/credibilidade.py`):
  1. só entram veículos da lista de confiáveis (fonte desconhecida fica escondida);
  2. títulos sensacionalistas ("URGENTE!!", "você não vai acreditar", tudo em MAIÚSCULAS) saem;
  3. história publicada por 2+ veículos confiáveis ganha o selo **Confirmada**.
  O app mostra quantas notícias foram escondidas e por quê.
- **O que é "em alta":** repercussão (quantos veículos), novidade, ordem do Google e
  nível do veículo (referência pesa mais que "conhecido").
- **Empresa fora da lista:** digite o ticker completo (ex.: `ABCD3`) na busca.
- As notícias são sempre **reais**, mesmo com `--offline`, então essa aba precisa de internet.

Testar no terminal, sem abrir o app:

```bash
python3 testar_noticias.py PETR4
```

Limitações (honestas): o filtro **reduz** o risco de notícia falsa, mas nenhum programa
garante que uma notícia é verdadeira. O feed do Google Notícias não é uma API oficial e pode
mudar. Notícias internacionais aparecem em inglês, e Bloomberg/FT/WSJ costumam ter paywall.
A BBC raramente cobre empresas brasileiras específicas.

## Balanços da CVM (base do relatório de saúde e do valuation)

Os números oficiais de todas as empresas da B3 vêm dos **dados abertos da CVM**
(grátis, desde 2010). O app baixa os arquivos e guarda num banco **SQLite**
(`backend/data/cvm.sqlite`), um banco de dados que mora num arquivo só e já vem com o Python.

```bash
python3 atualizar_cvm.py              # 1ª vez: alguns minutos (~150 MB). Depois é rápido.
python3 testar_cvm.py PETR4           # receita, lucro, EBITDA, dívida, capex... ano a ano
python3 testar_cvm.py WEGE3 --contas  # mostra também quais contas foram usadas
```

- Anuais (DFP) desde 2015 (`--desde 2010` para pegar tudo) e trimestrais (ITR) dos 2 últimos anos.
- Rode de novo depois de cada temporada de balanços (março, maio, agosto e novembro).
- Os números usam o **consolidado** (o grupo inteiro) e vêm em reais.
- **Bancos e seguradoras** têm outro plano de contas: EBIT, dívida e capex não se aplicam.
- **FIIs e ETFs** não aparecem (são fundos, não publicam balanço de empresa).
- Depreciação, capex e dividendos não têm código fixo na CVM: o app procura pelo nome da
  conta no fluxo de caixa. Use `--contas` para conferir o que foi encontrado.
- Os arquivos baixados e o banco **não vão para o GitHub** (estão no `.gitignore`).

## Análise e valuation das empresas (aba Empresas)

Na aba **Empresas**, toque numa empresa (ou digite qualquer ticker) para abrir a página dela,
com 3 seções. Dá para chegar também pela aba Ativos → ativo → "Análise e valuation da empresa".

**Análise**
- **Raio-X:** nota de 0 a 10 em Crescimento, Rentabilidade, Endividamento, Geração de caixa,
  Dividendos e Preço, cada uma com uma frase de conclusão (escrita por regras, sem IA).
- **Sinais de alerta:** patrimônio negativo, prejuízos recorrentes, receita ou margens caindo,
  lucro que não vira caixa, dívida crescendo mais que o EBITDA, dividendos maiores que o caixa livre.
- **Histórico em gráficos** (até 10 anos) e **todos os indicadores**, cada um com a regra do
  semáforo e a explicação. As regras ficam em `carteira/indicadores.py` (lista `REGRAS`).

**Valuation**
- **Fluxo de caixa descontado** de 5 anos + perpetuidade, em 3 cenários (negativo, neutro,
  positivo), com preço justo ponderado e margem de segurança.
- **Premissas editáveis:** crescimento, margem, capex, depreciação, capital de giro, IR, WACC e
  perpetuidade. As sugestões vêm do histórico da própria empresa (toque no ⓘ de cada uma).
- **"O que o preço atual supõe?"** (valuation reverso), **conta ano a ano**, **tabela de
  sensibilidade** e **custo de capital** com a fonte de cada número.
- **Bancos e seguradoras** usam o modelo de P/VP justo (Gordon).

Testar no terminal:

```bash
python3 testar_analise.py PETR4
```

Limitações (honestas): valuation é estimativa e depende muito das premissas; o valor de mercado
usa o preço do ticker escolhido para todas as classes de ações (ON e PN); participação de
minoritários não é descontada; as regras do semáforo são gerais (alguns setores têm padrões
próprios). Não é recomendação de investimento.

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

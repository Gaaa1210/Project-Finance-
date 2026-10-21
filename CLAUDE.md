# Contexto do projeto (leia antes de qualquer coisa)

Este arquivo resume tudo que já foi combinado com o dono do projeto (Gabriel) para que
qualquer nova conversa continue de onde parou, sem refazer perguntas.

## Quem é o usuário e como trabalhar com ele

- **Iniciante em Python**, aprendendo programação e automação com um projeto real.
- Usa **Mac** e **VS Code**. Digita os dados no computador e quer **ver o painel no iPhone**.
- **Tudo em português**: explicações, mensagens e comentários no código.
- Papel do Claude: **mentor de Python e desenvolvedor sênior**. Explicar cada passo em linguagem
  simples, dizer o que cada trecho de código faz, nunca pular passos.
- No Mac, usar sempre `python3` (não `python`) nos comandos.
- Trabalhar **em etapas** e **parar ao fim de cada uma** para ele testar.
- Em cada etapa entregar: código completo, como instalar e rodar, como testar com os dados de
  exemplo, e uma explicação curta dos conceitos novos aprendidos.
- Se algum requisito estiver vago: fazer uma suposição razoável, dizer qual foi e seguir.
- Ser honesto sobre limitações e aproximações. **Nunca inventar dados.**
- É uma ferramenta de acompanhamento e estudo, **não recomendação de investimento**.

## A ideia

Um **painel da carteira de investimentos no Brasil** (BRL, B3, CDI/Selic/IPCA, regras de IR para
pessoa física). O usuário só registra o que comprou e por quanto; o app calcula todo o resto.
Precisa funcionar bem no iPhone e ser **100% gratuito** (sem APIs pagas).

### Tipos de ativo
1. Ações, ETFs e FIIs (ex.: PETR4, IVVB11, HGLG11)
2. Renda fixa: CDB, LCI, LCA, Tesouro Direto
3. Fundos de investimento

### O que o usuário digita (uma linha por compra, na planilha)
- Ações/ETFs/FIIs: ticker, quantidade, preço pago, data da compra, taxas (opcional)
- Renda fixa: nome, tipo, valor investido, data da compra, vencimento, taxa
  (formatos: "110% do CDI", "IPCA + 6%", "13% pré")
- Fundos: nome ou CNPJ, valor investido, data da compra
- Compras repetidas do mesmo ativo são somadas e o preço médio é automático.

### O que o app calcula
**Ações, ETFs, FIIs:** preço atual (yfinance, sufixo ".SA"; atraso de 15 min é aceitável), total
investido, valor atual, lucro em R$ e %, variação do dia, preço médio, proventos recebidos e
retorno total com proventos.

**Renda fixa:** valor bruto atual estimado com CDI/Selic/IPCA da API do Banco Central (séries SGS);
IR pela tabela regressiva (22,5% até 180 dias, 20% até 360, 17,5% até 720, 15% acima); IOF nos
primeiros 30 dias; LCI e LCA isentas de IR para pessoa física; valor líquido se resgatar hoje e
valor no vencimento. **Rotular tudo como ESTIMATIVA** (os bancos calculam um pouco diferente).

**Fundos:** última cota pelos dados abertos da CVM (dados.cvm.gov.br), rentabilidade desde a
compra, avisar que as cotas são atualizadas com atraso.

**Carteira inteira:** patrimônio total, total investido, lucro total; alocação por tipo, setor e
ativo; desempenho contra CDI, Ibovespa e IPCA (1, 6 e 12 meses).

### Telas (mobile-first)
1. **Início:** patrimônio total, lucro total (verde se positivo, vermelho se negativo), variação do
   dia, gráfico de rosca da alocação
2. **Ativos:** lista agrupada por tipo; cada linha com nome, valor atual e lucro %
3. **Detalhe do ativo:** gráfico de preço com linha do preço médio, minhas compras, proventos
4. **Desempenho:** carteira vs CDI, Ibovespa e IPCA
5. **Adicionar/editar:** formulário para registrar uma nova compra

## Decisão de arquitetura (já escolhida pelo usuário)

O documento original pedia Streamlit, mas o usuário quer **React no frontend** e **muito Python**.
Foram apresentadas 3 opções e ele escolheu a **opção 2**:

- **Backend em Python com FastAPI**: lê a planilha, busca os dados de mercado e faz todos os
  cálculos. Expõe uma API em JSON.
- **Frontend em React**: só mostra os resultados nas 5 telas e envia o formulário de compra.
- É um **site** (não um app da App Store). No iPhone: abrir no Safari →
  Compartilhar → **Adicionar à Tela de Início**.
- Trade-off já explicado e aceito: são dois serviços para publicar, e servidores gratuitos podem
  "dormir" e demorar alguns segundos para acordar.

Dados: começar com planilha local (`backend/data/carteira.xlsx`) e depois migrar para Google
Sheets (gspread). Segredos (credenciais do Google) **nunca** no código nem no GitHub.

## Etapas e status

| Etapa | O que faz | Status |
|------|-----------|--------|
| 1 | Planilha de exemplo + leitura + cálculos de ações, ETFs e FIIs | ✅ pronta (no GitHub) |
| 2 | Calculadora de renda fixa (CDB, LCI, LCA, Tesouro) | ⏳ próxima |
| 3 | Fundos de investimento (CVM) | ⏳ |
| 4 | Servidor FastAPI + telas em React (as 5 telas) | 🟡 feita para ações/ETFs/FIIs |
| 5 | Google Sheets, publicação gratuita do backend e do frontend, configuração no iPhone | ⏳ |

### Pendência atual
- Etapa 1 **roda no Mac** (venv criado com `python3 -m venv .venv`).
- A Etapa 4 foi adiantada a pedido do usuário: `backend/api.py` (FastAPI) + `frontend/` (React com
  Vite, moldura de iPhone 17 no computador e tela cheia no celular). Testada com esbuild e Chromium
  no modo offline, mas **ainda não rodada no Mac** (`npm install` / `npm run dev` / `python3 api.py`).
  Verificar se ele tem Node.js. A busca real no Yahoo e o `pip install fastapi` também não foram
  testados no ambiente do Claude (sem acesso ao PyPI/Yahoo).
- Tela Desempenho: comparação com CDI/Ibovespa/IPCA está como "em breve" (depende da Etapa 2).
- Usuário rodou as telas no Mac e aprovou o visual (fez `npm install`).
- **Aba Notícias** feita (pedido do usuário): lista de empresas (carteira + `carteira/empresas.py`) com
  busca; ao tocar, as 20 notícias "em alta" via Google News RSS (`carteira/noticias.py`: agrupa
  títulos parecidos por Jaccard, nota = repercussão × novidade × posição no Google; 7 dias, amplia
  para 30). Depois ganhou **filtro de credibilidade** (`carteira/credibilidade.py`: lista de
  veículos nível 1/2 por domínio do `<source url>`, descarta desconhecidos e títulos
  sensacionalistas; selo "Confirmada" com 2+ veículos) e **busca internacional em inglês**
  (hl=en-US; campo `busca_en` em empresas.py; filtro Todas/Brasil/Internacional na tela).
  Combinado com o usuário: não existe detector de fake news confiável; é filtro de credibilidade.
  **Não testada contra o Google News real** (bloqueado no ambiente do Claude); pedir para
  ele rodar `python3 testar_noticias.py PETR4` e colar a saída se der erro.
- Código salvo no GitHub pelo usuário (commit da Etapa 4 + Notícias).
- **Relatório de saúde, decidido com o usuário:** números SÓ da CVM (não scraping de sites de RI);
  **sem IA por enquanto** (ele decidiu adiar; se voltar: IA só para ler texto de releases, nunca
  para números). Ordem: 1) dados CVM → SQLite ✅  2) indicadores + semáforo  3) valuation DCF com
  3 cenários (negativo/neutro/positivo, 5 anos, premissas do histórico e editáveis; bancos usam
  outro modelo)  4) IA (adiada).
- **Passo 1 feito:** `carteira/cvm.py` (baixa DFP/ITR/FCA de dados.cvm.gov.br, guarda em
  `data/cvm.sqlite`: tabelas contas, tickers, arquivos; só ORDEM_EXERC=ÚLTIMO, última VERSAO,
  consolidado com individual só para quem não tem consolidado, valores em reais),
  `carteira/demonstrativos.py` (série anual por código de conta fixo + busca por nome na DFC para
  depreciação/capex/dividendos), `atualizar_cvm.py`, `testar_cvm.py`, endpoint /api/fundamentos.
  **Não testado com os arquivos reais da CVM** (bloqueada no ambiente do Claude); testado com zips
  no formato documentado. Pedir para o usuário rodar `python3 atualizar_cvm.py` e
  `python3 testar_cvm.py PETR4 --contas` e colar a saída.
- **Passos 2 e 3 feitos (usuário pediu "pode começar já", serve para todos os perfis, quer
  cálculos precisos e premissas editáveis):** `carteira/indicadores.py` (indicadores, REGRAS do
  semáforo, raio_x com frases por regra, sinais_de_alerta, historico), `carteira/valuation.py`
  (DCF 5 anos + Gordon na perpetuidade; premissas padrão do histórico com spreads limitados;
  WACC = Ke/Kd; bancos: P/VP justo = (ROE−g)/(Ke−g); sensibilidade 5×5; valuation reverso por
  bisseção), `carteira/mercado.py` (taxa livre de risco: Focus Selic ano+3 → SGS 432 → 12%;
  beta 2 anos semanal vs ^BVSP com ajuste de Blume → 1,0), `carteira/analise.py`
  (montar_analise, recalcular_valuation), endpoints GET /api/analise/{t} e POST /api/valuation/{t},
  `testar_analise.py`. demonstrativos ganhou últimos 12 meses (DFP + ITR acumulado) e ações em
  circulação (planilha composicao_capital da CVM, tabela `acoes`). Frontend: aba "Notícias"
  virou **"Empresas"**; página `telas/Empresa.jsx` com seções Análise | Valuation | Notícias;
  navegação por pilha no App.jsx; `GraficoAnual.jsx`. **Nada disso testado com dados reais**
  (CVM, Focus, Yahoo bloqueados no ambiente do Claude); colunas da composicao_capital são
  suposição (QT_ACAO_TOTAL_CAP_INTEGR / QT_ACAO_TOTAL_TESOURO, busca por pedaços do nome).
- **Testado com dados reais no Mac (PETR4):** CVM, ações em circulação (12.888,7 mi), TTM, beta
  (0,76) e indicadores funcionaram. Problemas achados e corrigidos: Focus falhou (provável
  codificação '+' na URL OData → agora URL montada à mão com %20, e o motivo do erro aparece na
  fonte); capex < depreciação na perpetuidade → capex_na_perpetuidade = max(capex, depreciação);
  cenários extremos → distância de margem/capex limitada a 10–20%. Aviso na tela quando a taxa
  livre de risco não é de longo prazo. **Focus confirmado funcionando** (Selic 2029 = 10,0%).
  Perpetuidade agora é **4% igual nos 3 cenários** (decisão do usuário: o positivo com g 5% e
  WACC 11% ficava exagerado); cenários variam crescimento, margem, capex e WACC.
- Próximas ideias já combinadas: múltiplos vs histórico próprio (precisa de preço histórico),
  comparação com o setor, filtro de ações (screener), comparar 2 empresas, depois design.
- Plano anterior (por partes): 1) Notícias ✅  2) Relatório de saúde da empresa
  (balanços da CVM — DFP/ITR — guardados em SQLite + yfinance para múltiplos; semáforo por critério;
  bancos têm plano de contas diferente; precisa mapear ticker → CNPJ)  3) Melhorar o design
  (pedir prints de apps de referência). Renda fixa e fundos ficam para depois disso.

## Estrutura atual do código

```
backend/
├── requirements.txt          pandas, openpyxl, yfinance, requests
├── criar_planilha_exemplo.py cria data/carteira.xlsx (abas: acoes, renda_fixa, fundos)
├── etapa1.py                 roda a Etapa 1 no terminal (--offline usa preços fictícios)
├── api.py                    FastAPI: /api/carteira, /api/ativos/{t}, POST /api/compras, /api/empresas, /api/noticias/{t}
├── testar_noticias.py        imprime as notícias no terminal
├── atualizar_cvm.py          baixa balanços da CVM → data/cvm.sqlite
├── testar_cvm.py             imprime a série anual de uma empresa (--contas mostra contas achadas)
├── testar_analise.py         imprime Raio-X, alertas e valuation
├── data/carteira.xlsx        planilha do usuário (fora do Git, ver .gitignore)
├── carteira/
│   ├── planilha.py           lê e valida a planilha; ErroPlanilha com mensagens amigáveis
│   ├── cotacoes.py           yfinance; DadosCotacao; ErroCotacao; normalizar_ticker (.SA)
│   ├── calculos_acoes.py     funções puras: preço médio, lucro, variação, proventos, retorno
│   ├── acoes.py              resumir_acoes() e totalizar_acoes(): junta tudo
│   ├── formatacao.py         R$ 1.234,56 e +12,34%
│   ├── servico.py            monta o JSON das telas; cache de cotações 5 min, notícias 15 min
│   ├── empresas.py           lista curada de empresas da B3 + termos de busca de notícias
│   ├── noticias.py           Google News RSS (pt + en): ler, filtrar, agrupar, pontuar "em alta"
│   ├── credibilidade.py      veículos confiáveis (nível 1/2) + detector de título sensacionalista
│   ├── cvm.py                download e carga DFP/ITR/FCA da CVM em SQLite
│   ├── demonstrativos.py     série anual, últimos 12 meses, ações em circulação
│   ├── mercado.py            taxa livre de risco (Focus/SGS) e beta (yfinance)
│   ├── indicadores.py        indicadores, semáforo (REGRAS), raio-x, alertas
│   ├── valuation.py          DCF 3 cenários, Gordon p/ bancos, sensibilidade, reverso
│   ├── analise.py            orquestra a análise para a API
│   └── dados_exemplo.py      cotações FICTÍCIAS para o modo offline
└── tests/                    89 testes (python3 -m unittest discover tests -v)

frontend/                     React + Vite (npm run dev → localhost:5173, proxy /api → :8000)
└── src/  App.jsx, api.js, formatacao.js, estilos.css, componentes/, telas/
```

A aba `renda_fixa` da planilha de exemplo já está preenchida no formato da Etapa 2
(colunas: nome, tipo, valor_investido, data_compra, data_vencimento, taxa). A aba `fundos` tem só
o cabeçalho (nome, cnpj, valor_investido, data_compra).

## Convenções do código

- Cálculos financeiros em **funções separadas, puras e bem nomeadas** (fáceis de entender e mudar).
- Percentuais guardados como **fração** (0.10 = 10%); formatar só na hora de mostrar.
- Datas no padrão brasileiro (`dayfirst=True`).
- Erros com **mensagens amigáveis em português** (ticker inexistente, sem internet, planilha vazia);
  um ativo com problema não derruba o resto da carteira.
- Funções de busca de dados são **injetáveis** (passadas como parâmetro) para testar sem internet.
- Testes com `unittest` (biblioteca padrão), em `backend/tests/`.
- Commits em português.

## Suposições já feitas (e comunicadas ao usuário)

- O preço médio **inclui as taxas** (regra da Receita Federal).
- Por enquanto só **compras**; vendas ainda não são suportadas.
- O **setor** é preenchido pelo usuário na planilha (o Yahoo não traz isso de forma confiável).
- Proventos do Yahoo são **brutos** (JCP tem 15% de IR na fonte) e podem faltar alguns.
- A planilha real **não vai para o GitHub** (privacidade).

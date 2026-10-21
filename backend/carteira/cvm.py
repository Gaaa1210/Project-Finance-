"""
Balanços oficiais das empresas, direto dos DADOS ABERTOS DA CVM.

Toda empresa listada na B3 entrega seus balanços à CVM. A CVM publica tudo,
de graça, em arquivos .zip com planilhas CSV:
  - DFP = Demonstrações Financeiras Padronizadas (balanço ANUAL), desde 2010
  - ITR = Informações Trimestrais (balanço de cada TRIMESTRE)
  - FCA = Formulário Cadastral (aqui usamos para ligar o ticker ao CNPJ)

Este arquivo:
  1. baixa os .zip para backend/data/cvm/
  2. lê as planilhas que interessam (balanço, resultado e fluxo de caixa)
  3. guarda tudo num banco de dados SQLite: backend/data/cvm.sqlite

SQLite é um banco de dados que mora num arquivo só. Vem junto com o Python
(módulo sqlite3), não precisa instalar nem configurar nada.

Para baixar/atualizar, rode (na pasta backend):
    python3 atualizar_cvm.py
"""

import io
import sqlite3
import unicodedata
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

from carteira.planilha import PASTA_BACKEND

PASTA_CVM = PASTA_BACKEND / "data" / "cvm"          # onde ficam os .zip baixados
CAMINHO_BANCO = PASTA_BACKEND / "data" / "cvm.sqlite"

URL_BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
URLS = {
    "DFP": URL_BASE + "/DFP/DADOS/dfp_cia_aberta_{ano}.zip",
    "ITR": URL_BASE + "/ITR/DADOS/itr_cia_aberta_{ano}.zip",
    "FCA": URL_BASE + "/FCA/DADOS/fca_cia_aberta_{ano}.zip",
}

# Planilhas que lemos de cada zip DFP/ITR:
#   BPA = Balanço Patrimonial Ativo       BPP = Balanço Patrimonial Passivo
#   DRE = Demonstração do Resultado       DFC = Demonstração do Fluxo de Caixa
#   (a DFC vem em dois "métodos", MI = indireto e MD = direto; cada empresa usa um)
DEMONSTRATIVOS = {"BPA": "BPA", "BPP": "BPP", "DRE": "DRE", "DFC_MI": "DFC", "DFC_MD": "DFC"}

# A CVM escreve valores em reais ("UNIDADE") ou em milhares de reais ("MIL").
ESCALAS = {"UNIDADE": 1, "MIL": 1000}


class ErroCVM(Exception):
    """Problema ao baixar ou ler os dados da CVM (mensagem amigável)."""


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

def abrir_banco(caminho: Path = CAMINHO_BANCO) -> sqlite3.Connection:
    """Abre (ou cria) o banco e garante que as tabelas existem."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho)
    conexao.executescript("""
        -- Cada linha = uma conta de um balanço. Ex.: Receita (3.01) da Petrobras em 2023.
        CREATE TABLE IF NOT EXISTS contas (
            arquivo       TEXT,     -- de qual zip veio (ex.: 'DFP_2023')
            fonte         TEXT,     -- 'DFP' (anual) ou 'ITR' (trimestral)
            cnpj          TEXT,
            empresa       TEXT,
            dt_refer      TEXT,     -- data de referência do documento (AAAA-MM-DD)
            versao        INTEGER,  -- a empresa pode reapresentar; guardamos a última
            demonstrativo TEXT,     -- 'BPA', 'BPP', 'DRE' ou 'DFC'
            consolidado   INTEGER,  -- 1 = consolidado (grupo todo), 0 = individual
            dt_ini        TEXT,     -- início do período (vazio no balanço patrimonial)
            dt_fim        TEXT,     -- fim do período
            cd_conta      TEXT,     -- código da conta (ex.: '3.01')
            ds_conta      TEXT,     -- nome da conta (ex.: 'Receita de Venda de Bens e/ou Serviços')
            valor         REAL      -- sempre em REAIS (já multiplicamos quando vinha em milhares)
        );
        CREATE INDEX IF NOT EXISTS idx_contas_empresa ON contas (cnpj, fonte, demonstrativo);
        CREATE INDEX IF NOT EXISTS idx_contas_arquivo ON contas (arquivo);

        -- Ticker -> CNPJ (ex.: PETR4 -> 33.000.167/0001-01)
        CREATE TABLE IF NOT EXISTS tickers (
            ticker   TEXT PRIMARY KEY,
            cnpj     TEXT,
            empresa  TEXT,
            dt_refer TEXT
        );

        -- Quantidade de ações de cada empresa em cada documento (para o valor por ação)
        CREATE TABLE IF NOT EXISTS acoes (
            arquivo     TEXT,
            fonte       TEXT,
            cnpj        TEXT,
            dt_refer    TEXT,
            total       REAL,   -- ações que compõem o capital (ordinárias + preferenciais)
            tesouraria  REAL    -- ações recompradas pela própria empresa (não contam)
        );
        CREATE INDEX IF NOT EXISTS idx_acoes_empresa ON acoes (cnpj);

        -- Quais zips já foram carregados (para não carregar duas vezes)
        CREATE TABLE IF NOT EXISTS arquivos (
            arquivo      TEXT PRIMARY KEY,
            linhas       INTEGER,
            carregado_em TEXT
        );
    """)
    return conexao


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def caminho_zip(tipo: str, ano: int) -> Path:
    return PASTA_CVM / f"{tipo.lower()}_cia_aberta_{ano}.zip"


def baixar_zip(tipo: str, ano: int, forcar: bool = False) -> Path:
    """
    Baixa um zip da CVM (se ainda não estiver na pasta, ou se forcar=True).
    Devolve o caminho do arquivo. Gera ErroCVM se não conseguir.
    """
    destino = caminho_zip(tipo, ano)
    if destino.exists() and not forcar:
        return destino

    try:
        import requests
    except ImportError:
        raise ErroCVM("A biblioteca requests não está instalada. Rode: pip install -r requirements.txt")

    url = URLS[tipo].format(ano=ano)
    try:
        resposta = requests.get(url, timeout=120, stream=True)
    except requests.RequestException as erro:
        raise ErroCVM(f"Não consegui acessar o site da CVM ({type(erro).__name__}). Verifique sua internet.")

    if resposta.status_code == 404:
        raise ErroCVM(f"A CVM ainda não tem o arquivo {tipo} de {ano}.")
    if resposta.status_code != 200:
        raise ErroCVM(f"O site da CVM respondeu com erro {resposta.status_code} para {tipo} {ano}.")

    PASTA_CVM.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".baixando")
    with open(temporario, "wb") as arquivo:
        for pedaco in resposta.iter_content(chunk_size=1024 * 256):
            arquivo.write(pedaco)
    temporario.replace(destino)  # só "aparece" com o nome certo quando terminou
    return destino


# ---------------------------------------------------------------------------
# Leitura dos CSVs
# ---------------------------------------------------------------------------

def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().upper()


def ler_csv_do_zip(zip_aberto: zipfile.ZipFile, nome: str) -> pd.DataFrame:
    """
    Lê um CSV de dentro do zip. Os arquivos da CVM usam ';' como separador e,
    em geral, a codificação latin-1 (o jeito antigo de guardar acentos).
    """
    bruto = zip_aberto.read(nome)
    for codificacao in ("latin-1", "utf-8"):
        try:
            tabela = pd.read_csv(io.BytesIO(bruto), sep=";", encoding=codificacao, dtype=str)
            break
        except UnicodeDecodeError:
            continue
    tabela.columns = [c.strip().upper() for c in tabela.columns]
    return tabela


def _encontrar(nomes: list, *partes: str):
    """Acha, dentro do zip, o CSV cujo nome contém todas as 'partes'."""
    for nome in nomes:
        minusculo = nome.lower()
        if all(p.lower() in minusculo for p in partes):
            return nome
    return None


def preparar_demonstrativo(tabela: pd.DataFrame, fonte: str, demonstrativo: str, consolidado: bool) -> pd.DataFrame:
    """
    Limpa uma planilha de demonstrativo da CVM:
      - fica só com o exercício mais recente de cada documento (ORDEM_EXERC = 'ÚLTIMO');
        o 'PENÚLTIMO' é o ano anterior, repetido só para comparação;
      - fica só com a versão mais recente de cada documento (reapresentações);
      - converte o valor para reais.
    """
    if tabela.empty:
        return pd.DataFrame()

    ordem = tabela["ORDEM_EXERC"].map(_sem_acento)
    tabela = tabela[ordem == "ULTIMO"].copy()

    tabela["VERSAO"] = pd.to_numeric(tabela["VERSAO"], errors="coerce").fillna(1).astype(int)
    ultima = tabela.groupby(["CNPJ_CIA", "DT_REFER"])["VERSAO"].transform("max")
    tabela = tabela[tabela["VERSAO"] == ultima]

    escala = tabela["ESCALA_MOEDA"].map(_sem_acento).map(ESCALAS).fillna(1)
    valor = pd.to_numeric(tabela["VL_CONTA"].str.replace(",", ".", regex=False), errors="coerce")

    return pd.DataFrame({
        "fonte": fonte,
        "cnpj": tabela["CNPJ_CIA"].str.strip(),
        "empresa": tabela["DENOM_CIA"].str.strip(),
        "dt_refer": tabela["DT_REFER"],
        "versao": tabela["VERSAO"],
        "demonstrativo": demonstrativo,
        "consolidado": 1 if consolidado else 0,
        "dt_ini": tabela["DT_INI_EXERC"] if "DT_INI_EXERC" in tabela.columns else None,
        "dt_fim": tabela["DT_FIM_EXERC"],
        "cd_conta": tabela["CD_CONTA"].str.strip(),
        "ds_conta": tabela["DS_CONTA"].str.strip(),
        "valor": valor * escala,
    })


def ler_zip_balancos(caminho: Path, fonte: str) -> pd.DataFrame:
    """
    Lê os demonstrativos de um zip DFP ou ITR.

    Para economizar espaço, guardamos o CONSOLIDADO (o grupo inteiro, que é o que
    importa para o investidor) e só usamos o INDIVIDUAL das empresas que não
    publicam consolidado.
    """
    try:
        zip_aberto = zipfile.ZipFile(caminho)
    except zipfile.BadZipFile:
        raise ErroCVM(f"O arquivo {caminho.name} está corrompido. Apague-o e rode de novo.")

    nomes = zip_aberto.namelist()
    partes = []
    for chave, demonstrativo in DEMONSTRATIVOS.items():
        nome_con = _encontrar(nomes, f"_{chave}_con_")
        nome_ind = _encontrar(nomes, f"_{chave}_ind_")
        con = preparar_demonstrativo(ler_csv_do_zip(zip_aberto, nome_con), fonte, demonstrativo, True) if nome_con else pd.DataFrame()
        ind = preparar_demonstrativo(ler_csv_do_zip(zip_aberto, nome_ind), fonte, demonstrativo, False) if nome_ind else pd.DataFrame()
        if not ind.empty and not con.empty:
            ind = ind[~ind["cnpj"].isin(set(con["cnpj"]))]  # individual só de quem não tem consolidado
        partes += [p for p in (con, ind) if not p.empty]

    if not partes:
        raise ErroCVM(f"Não encontrei demonstrativos dentro de {caminho.name}.")
    return pd.concat(partes, ignore_index=True)


def ler_composicao_capital(caminho: Path, fonte: str) -> pd.DataFrame:
    """
    Lê a planilha 'composicao_capital' do zip DFP/ITR: quantas ações a empresa tem
    e quantas estão em tesouraria. Devolve tabela vazia se o zip não tiver essa planilha.
    """
    zip_aberto = zipfile.ZipFile(caminho)
    nome = _encontrar(zip_aberto.namelist(), "composicao_capital")
    if not nome:
        return pd.DataFrame()
    tabela = ler_csv_do_zip(zip_aberto, nome)

    def coluna(*pedacos):
        for c in tabela.columns:
            if all(p in c for p in pedacos):
                return c
        return None

    col_total = coluna("TOTAL", "CAP_INTEGR")
    col_tesouraria = coluna("TOTAL", "TESOURO")
    if not col_total:
        return pd.DataFrame()

    tabela["VERSAO"] = pd.to_numeric(tabela.get("VERSAO", 1), errors="coerce").fillna(1)
    tabela = tabela.sort_values("VERSAO").drop_duplicates(["CNPJ_CIA", "DT_REFER"], keep="last")
    return pd.DataFrame({
        "fonte": fonte,
        "cnpj": tabela["CNPJ_CIA"].str.strip(),
        "dt_refer": tabela["DT_REFER"],
        "total": pd.to_numeric(tabela[col_total], errors="coerce"),
        "tesouraria": pd.to_numeric(tabela[col_tesouraria], errors="coerce").fillna(0) if col_tesouraria else 0.0,
    })


def ler_zip_tickers(caminho: Path) -> pd.DataFrame:
    """
    Lê a planilha de 'valores mobiliários' do FCA, que tem os códigos de
    negociação (tickers) de cada empresa. Devolve: ticker, cnpj, empresa, dt_refer.
    """
    zip_aberto = zipfile.ZipFile(caminho)
    nome = _encontrar(zip_aberto.namelist(), "valor_mobiliario")
    if not nome:
        raise ErroCVM(f"Não encontrei a planilha de valores mobiliários em {caminho.name}.")
    tabela = ler_csv_do_zip(zip_aberto, nome)

    # Os nomes das colunas do FCA mudam um pouco entre anos; procuramos por pedaços.
    def coluna(*pedacos):
        for c in tabela.columns:
            if all(p in c for p in pedacos):
                return c
        raise ErroCVM(f"Coluna {pedacos} não encontrada em {nome}.")

    col_ticker = coluna("CODIGO", "NEGOCIACAO")
    col_cnpj = coluna("CNPJ")
    col_nome = coluna("NOME")
    col_data = coluna("DATA_REFERENCIA")

    resultado = pd.DataFrame({
        "ticker": tabela[col_ticker].str.strip().str.upper(),
        "cnpj": tabela[col_cnpj].str.strip(),
        "empresa": tabela[col_nome].str.strip(),
        "dt_refer": tabela[col_data],
    })
    resultado = resultado[resultado["ticker"].str.match(r"^[A-Z0-9]{4}\d{1,2}$", na=False)]
    # Se o mesmo ticker aparecer mais de uma vez, vale o documento mais recente.
    return resultado.sort_values("dt_refer").drop_duplicates("ticker", keep="last")


# ---------------------------------------------------------------------------
# Carregar no banco
# ---------------------------------------------------------------------------

def carregar_balancos(conexao: sqlite3.Connection, caminho: Path, fonte: str, ano: int) -> int:
    """Lê um zip DFP/ITR e grava no banco (substituindo o que havia desse zip)."""
    arquivo = f"{fonte}_{ano}"
    contas = ler_zip_balancos(caminho, fonte)
    contas.insert(0, "arquivo", arquivo)
    acoes = ler_composicao_capital(caminho, fonte)

    with conexao:  # "with" = tudo ou nada (se der erro no meio, nada é gravado)
        conexao.execute("DELETE FROM contas WHERE arquivo = ?", (arquivo,))
        contas.to_sql("contas", conexao, if_exists="append", index=False, chunksize=50_000)
        conexao.execute("DELETE FROM acoes WHERE arquivo = ?", (arquivo,))
        if not acoes.empty:
            acoes.insert(0, "arquivo", arquivo)
            acoes.to_sql("acoes", conexao, if_exists="append", index=False)
        conexao.execute(
            "INSERT OR REPLACE INTO arquivos VALUES (?, ?, datetime('now', 'localtime'))",
            (arquivo, len(contas)),
        )
    return len(contas)


def carregar_tickers(conexao: sqlite3.Connection, caminho: Path) -> int:
    tickers = ler_zip_tickers(caminho)
    with conexao:
        for linha in tickers.itertuples(index=False):
            conexao.execute(
                """INSERT INTO tickers VALUES (?, ?, ?, ?)
                   ON CONFLICT(ticker) DO UPDATE SET cnpj = excluded.cnpj,
                       empresa = excluded.empresa, dt_refer = excluded.dt_refer
                   WHERE excluded.dt_refer >= tickers.dt_refer""",
                (linha.ticker, linha.cnpj, linha.empresa, linha.dt_refer),
            )
    return len(tickers)


def atualizar(desde: int = 2015, anos_itr: int = 2, forcar: bool = False,
              caminho_banco: Path = CAMINHO_BANCO, avisar=print) -> None:
    """
    Baixa e carrega tudo:
      - DFP (anual) de 'desde' até o ano atual
      - ITR (trimestral) dos últimos 'anos_itr' anos
      - FCA (tickers) dos 2 últimos anos

    Os anos mais recentes são sempre baixados de novo (a CVM corrige e acrescenta
    documentos). Os antigos só são baixados se ainda não estiverem na pasta.
    """
    ano_atual = date.today().year
    conexao = abrir_banco(caminho_banco)
    tarefas = (
        [("FCA", ano) for ano in (ano_atual - 1, ano_atual)]
        + [("DFP", ano) for ano in range(desde, ano_atual + 1)]
        + [("ITR", ano) for ano in range(ano_atual - anos_itr + 1, ano_atual + 1)]
    )

    for tipo, ano in tarefas:
        recente = ano >= ano_atual - 1
        try:
            caminho = baixar_zip(tipo, ano, forcar=forcar or recente)
            if tipo == "FCA":
                quantidade = carregar_tickers(conexao, caminho)
                avisar(f"  ✅ {tipo} {ano}: {quantidade} tickers")
            else:
                quantidade = carregar_balancos(conexao, caminho, tipo, ano)
                avisar(f"  ✅ {tipo} {ano}: {quantidade:,} linhas".replace(",", "."))
        except ErroCVM as erro:
            avisar(f"  ⚠️  {tipo} {ano}: {erro}")

    conexao.execute("VACUUM")  # compacta o arquivo do banco
    conexao.close()

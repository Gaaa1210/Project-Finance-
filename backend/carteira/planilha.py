"""
Leitura da planilha de compras.

A planilha (data/carteira.xlsx) tem uma aba para cada tipo de investimento:
  - "acoes"       -> ações, ETFs e FIIs           (usada na Etapa 1)
  - "renda_fixa"  -> CDB, LCI, LCA, Tesouro       (Etapa 2)
  - "fundos"      -> fundos de investimento       (Etapa 3)

Cada linha é UMA compra. Se você comprou PETR4 três vezes, são três linhas.

Este arquivo só LÊ e CONFERE os dados. Os cálculos ficam em outros arquivos.
"""

from pathlib import Path

import pandas as pd

# Pasta onde está este arquivo -> sobe um nível (backend/) -> entra em data/
PASTA_BACKEND = Path(__file__).resolve().parent.parent
CAMINHO_PADRAO = PASTA_BACKEND / "data" / "carteira.xlsx"

# Colunas que a aba "acoes" PRECISA ter.
COLUNAS_ACOES_OBRIGATORIAS = ["ticker", "quantidade", "preco_pago", "data_compra"]

# Colunas opcionais: se não existirem ou estiverem vazias, usamos um valor padrão.
COLUNAS_ACOES_OPCIONAIS = {"taxas": 0.0, "tipo": "Ação", "setor": "Não informado"}

TIPOS_ACEITOS = {"Ação", "ETF", "FII"}


class ErroPlanilha(Exception):
    """
    Erro com mensagem amigável sobre a planilha.
    Criamos nosso próprio tipo de erro para separar "problema na sua planilha"
    de "bug no código".
    """


def converter_numero(valor):
    """
    Aceita números escritos de vários jeitos e devolve um float.
      32.5      -> 32.5
      "32,50"   -> 32.5
      "R$ 1.234,56" -> 1234.56
    Retorna None se a célula estiver vazia.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if texto == "":
        return None
    # Formato brasileiro: ponto separa milhar e vírgula separa decimal.
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return float(texto)  # se não for número, o float() gera ValueError


def ler_aba(caminho: Path, aba: str) -> pd.DataFrame:
    """Abre uma aba da planilha e devolve uma tabela (DataFrame) do pandas."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroPlanilha(
            f"Não encontrei a planilha em '{caminho}'.\n"
            "Rode 'python criar_planilha_exemplo.py' para criar uma de exemplo."
        )

    try:
        tabela = pd.read_excel(caminho, sheet_name=aba)
    except ValueError:
        # O pandas gera ValueError quando a aba não existe.
        raise ErroPlanilha(f"A planilha não tem uma aba chamada '{aba}'.")

    # Padroniza os nomes das colunas: minúsculas e sem espaços nas pontas.
    tabela.columns = [str(c).strip().lower() for c in tabela.columns]
    # Remove linhas totalmente vazias (comum no fim da planilha).
    return tabela.dropna(how="all")


def ler_compras_acoes(caminho: Path = CAMINHO_PADRAO) -> pd.DataFrame:
    """
    Lê a aba "acoes" e devolve uma tabela limpa, com uma linha por compra.

    Colunas da tabela devolvida:
      ticker, quantidade, preco_pago, data_compra, taxas, tipo, setor
    """
    tabela = ler_aba(caminho, "acoes")

    if tabela.empty:
        raise ErroPlanilha(
            "A aba 'acoes' está vazia. Adicione pelo menos uma compra "
            "(uma linha com ticker, quantidade, preco_pago e data_compra)."
        )

    faltando = [c for c in COLUNAS_ACOES_OBRIGATORIAS if c not in tabela.columns]
    if faltando:
        raise ErroPlanilha(
            "A aba 'acoes' não tem estas colunas obrigatórias: " + ", ".join(faltando)
        )

    # Garante que as colunas opcionais existam e preenche vazios com o padrão.
    for coluna, padrao in COLUNAS_ACOES_OPCIONAIS.items():
        if coluna not in tabela.columns:
            tabela[coluna] = padrao
        tabela[coluna] = tabela[coluna].fillna(padrao)

    compras = []
    problemas = []

    # iterrows() percorre a tabela linha por linha.
    # A linha 1 do Excel é o cabeçalho, então a linha de dados de índice 0 é a linha 2.
    for indice, linha in tabela.iterrows():
        numero_excel = indice + 2
        try:
            compras.append(_validar_linha_acao(linha))
        except (ValueError, TypeError) as erro:
            problemas.append(f"  - Linha {numero_excel}: {erro}")

    if problemas:
        raise ErroPlanilha(
            "Encontrei problemas na aba 'acoes':\n" + "\n".join(problemas)
        )

    return pd.DataFrame(compras)


def _validar_linha_acao(linha) -> dict:
    """
    Confere uma linha da aba "acoes" e devolve um dicionário limpo.
    Gera ValueError com uma explicação se algo estiver errado.
    (O "_" no começo do nome indica que é uma função de uso interno deste arquivo.)
    """
    ticker = str(linha["ticker"]).strip().upper()
    if ticker in ("", "NAN"):
        raise ValueError("ticker vazio")

    try:
        quantidade = converter_numero(linha["quantidade"])
        preco = converter_numero(linha["preco_pago"])
        taxas = converter_numero(linha["taxas"]) or 0.0
    except ValueError:
        raise ValueError(f"{ticker}: quantidade, preço ou taxas não é um número válido")

    if quantidade is None or quantidade <= 0:
        raise ValueError(f"{ticker}: a quantidade precisa ser maior que zero")
    if preco is None or preco <= 0:
        raise ValueError(f"{ticker}: o preço pago precisa ser maior que zero")
    if taxas < 0:
        raise ValueError(f"{ticker}: as taxas não podem ser negativas")

    # dayfirst=True: "05/03/2024" é 5 de março (padrão brasileiro), não 3 de maio.
    data = pd.to_datetime(linha["data_compra"], dayfirst=True, errors="coerce")
    if pd.isna(data):
        raise ValueError(f"{ticker}: data de compra inválida (use dd/mm/aaaa)")
    if data > pd.Timestamp.today():
        raise ValueError(f"{ticker}: a data de compra está no futuro")

    tipo = str(linha["tipo"]).strip()
    if tipo not in TIPOS_ACEITOS:
        raise ValueError(f"{ticker}: tipo '{tipo}' inválido (use Ação, ETF ou FII)")

    return {
        "ticker": ticker,
        "quantidade": quantidade,
        "preco_pago": preco,
        "data_compra": data.normalize(),  # normalize() zera o horário
        "taxas": taxas,
        "tipo": tipo,
        "setor": str(linha["setor"]).strip(),
    }

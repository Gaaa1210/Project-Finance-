"""
Consulta os balanços guardados no banco da CVM (ver cvm.py) e monta a
SÉRIE ANUAL de uma empresa: receita, lucro, dívida, caixa, investimentos...
um número por ano.

Como achamos cada número? Pelos códigos padronizados das contas da CVM.
Toda empresa (não financeira) usa os mesmos códigos para as contas principais:

    3.01  Receita líquida             1        Ativo total
    3.03  Lucro bruto                 1.01.01  Caixa e equivalentes
    3.05  EBIT (resultado operacional)  2.01.04  Empréstimos de curto prazo
    3.11  Lucro líquido               2.02.01  Empréstimos de longo prazo
    6.01  Caixa das operações         2.03     Patrimônio líquido

Algumas contas não têm código fixo (cada empresa dá um nome), como a
depreciação, o investimento em imobilizado (capex) e os dividendos pagos.
Para essas, procuramos pelo NOME da conta no fluxo de caixa.

Bancos e seguradoras usam outro plano de contas: o app avisa e, por enquanto,
mostra só o que dá para comparar (lucro, patrimônio, ativo).
"""

import re
import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd

from carteira.cvm import CAMINHO_BANCO, abrir_banco


class ErroDemonstrativos(Exception):
    """Empresa não encontrada, banco vazio etc. (mensagem amigável)."""


# Contas com código fixo: nome no app -> (demonstrativo, código da conta)
CONTAS_FIXAS = {
    "receita_liquida": ("DRE", "3.01"),
    "custo": ("DRE", "3.02"),
    "lucro_bruto": ("DRE", "3.03"),
    "ebit": ("DRE", "3.05"),
    "resultado_financeiro": ("DRE", "3.06"),
    "lucro_antes_ir": ("DRE", "3.07"),
    "ir_csll": ("DRE", "3.08"),
    "lucro_liquido": ("DRE", "3.11"),
    "lucro_controladores": ("DRE", "3.11.01"),
    "ativo_total": ("BPA", "1"),
    "ativo_circulante": ("BPA", "1.01"),
    "caixa": ("BPA", "1.01.01"),
    "aplicacoes_financeiras": ("BPA", "1.01.02"),
    "passivo_circulante": ("BPP", "2.01"),
    "emprestimos_cp": ("BPP", "2.01.04"),
    "emprestimos_lp": ("BPP", "2.02.01"),
    "patrimonio_liquido": ("BPP", "2.03"),
    "fluxo_operacional": ("DFC", "6.01"),
    "fluxo_investimento": ("DFC", "6.02"),
    "fluxo_financiamento": ("DFC", "6.03"),
}

# Contas sem código fixo: procuradas pelo nome, dentro de um grupo do fluxo de caixa.
#   nome no app -> (grupo da DFC, expressão que o nome da conta precisa ter)
CONTAS_POR_NOME = {
    # Depreciação e amortização: somadas de volta no caixa das operações (6.01)
    "depreciacao": ("6.01", r"deprecia|amortiza|exaust"),
    # Capex: compra de imobilizado e intangível, no caixa de investimento (6.02)
    "capex": ("6.02", r"(?:aquisi|adi[cç]|compra|investimento|aplica).*(?:imobilizado|intang)"),
    # Dividendos e JCP pagos, no caixa de financiamento (6.03)
    "dividendos_pagos": ("6.03", r"dividendo|juros sobre (?:o )?capital"),
}

COLUNAS = list(CONTAS_FIXAS) + list(CONTAS_POR_NOME) + [
    "divida_bruta", "divida_liquida", "ebitda", "fluxo_caixa_livre",
]


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()


# ---------------------------------------------------------------------------
# Encontrar a empresa
# ---------------------------------------------------------------------------

def encontrar_cnpj(ticker: str, conexao: sqlite3.Connection) -> tuple:
    """PETR4 -> ('33.000.167/0001-01', 'PETROLEO BRASILEIRO S.A. PETROBRAS')"""
    ticker = ticker.strip().upper()
    linha = conexao.execute("SELECT cnpj, empresa FROM tickers WHERE ticker = ?", (ticker,)).fetchone()
    if linha:
        return linha

    total = conexao.execute("SELECT COUNT(*) FROM tickers").fetchone()[0]
    if total == 0:
        raise ErroDemonstrativos(
            "O banco de balanços ainda está vazio. Rode primeiro: python3 atualizar_cvm.py"
        )
    if ticker.endswith("11"):
        raise ErroDemonstrativos(
            f"Não encontrei {ticker} entre as empresas da CVM. Se for um FII ou ETF, ele não "
            "publica balanço de empresa (é um fundo). Se for uma unit (ex.: SANB11), tente o "
            "ticker da ação ordinária (ex.: SANB3)."
        )
    raise ErroDemonstrativos(f"Não encontrei o ticker {ticker} no cadastro da CVM.")


# ---------------------------------------------------------------------------
# Série anual
# ---------------------------------------------------------------------------

def ler_contas_anuais(cnpj: str, conexao: sqlite3.Connection) -> pd.DataFrame:
    """Todas as contas dos balanços ANUAIS (DFP) de uma empresa."""
    return pd.read_sql_query(
        """SELECT dt_refer, demonstrativo, consolidado, cd_conta, ds_conta, valor
           FROM contas WHERE cnpj = ? AND fonte = 'DFP'""",
        conexao,
        params=(cnpj,),
    )


def _contas_folha(contas: pd.DataFrame) -> pd.DataFrame:
    """
    Fica só com as contas "folha" (sem subcontas). Isso evita somar duas vezes:
    ex.: se 6.02.01 = 6.02.01.01 + 6.02.01.02, somamos só as duas últimas.
    """
    codigos = set(contas["cd_conta"])
    tem_filha = {c for c in codigos for outro in codigos if outro.startswith(c + ".")}
    return contas[~contas["cd_conta"].isin(tem_filha)]


def calcular_ano(contas_do_ano: pd.DataFrame, detalhes: dict = None) -> dict:
    """
    Recebe as contas de UM ano (de um documento) e devolve os números principais.
    Valores em reais. Conta que não existir fica como None.
    Se 'detalhes' for um dicionário, ele recebe os nomes das contas usadas nas
    buscas por nome (útil para conferir se o app achou a conta certa).
    """
    resultado = {}
    indice = {(d, c): v for d, c, v in zip(contas_do_ano["demonstrativo"], contas_do_ano["cd_conta"], contas_do_ano["valor"])}
    for nome, chave in CONTAS_FIXAS.items():
        valor = indice.get(chave)
        resultado[nome] = None if valor is None or pd.isna(valor) else float(valor)

    dfc = _contas_folha(contas_do_ano[contas_do_ano["demonstrativo"] == "DFC"])
    for nome, (grupo, padrao) in CONTAS_POR_NOME.items():
        linhas = dfc[dfc["cd_conta"].str.startswith(grupo + ".")]
        combinam = linhas[linhas["ds_conta"].map(_sem_acento).str.contains(padrao, regex=True)]
        resultado[nome] = float(combinam["valor"].sum()) if not combinam.empty else None
        if detalhes is not None:
            detalhes[nome] = list(zip(combinam["cd_conta"], combinam["ds_conta"], combinam["valor"]))

    # Capex e dividendos aparecem negativos no fluxo de caixa (é dinheiro saindo).
    # Guardamos como número positivo, que é como se costuma falar ("capex de R$ 10 bi").
    for nome in ("capex", "dividendos_pagos"):
        if resultado[nome] is not None:
            resultado[nome] = abs(resultado[nome])

    # Contas derivadas (calculadas a partir das outras)
    cp, lp = resultado["emprestimos_cp"], resultado["emprestimos_lp"]
    if cp is not None or lp is not None:
        resultado["divida_bruta"] = (cp or 0.0) + (lp or 0.0)
        caixa_total = (resultado["caixa"] or 0.0) + (resultado["aplicacoes_financeiras"] or 0.0)
        resultado["divida_liquida"] = resultado["divida_bruta"] - caixa_total
    else:
        resultado["divida_bruta"] = resultado["divida_liquida"] = None

    ebit, depreciacao = resultado["ebit"], resultado["depreciacao"]
    resultado["ebitda"] = ebit + depreciacao if ebit is not None and depreciacao is not None else None

    fco, capex = resultado["fluxo_operacional"], resultado["capex"]
    resultado["fluxo_caixa_livre"] = fco - capex if fco is not None and capex is not None else None
    return resultado


def eh_financeira(contas: pd.DataFrame) -> bool:
    """Bancos e seguradoras: a receita (3.01) é 'Receitas da Intermediação Financeira' ou de seguros."""
    receita = contas[(contas["demonstrativo"] == "DRE") & (contas["cd_conta"] == "3.01")]
    if receita.empty:
        return False
    nome = _sem_acento(receita["ds_conta"].iloc[-1])
    return bool(re.search(r"intermediacao financeira|premios|seguros|receitas de juros", nome))


def serie_anual(ticker: str, caminho_banco: Path = CAMINHO_BANCO, anos: int = 10) -> dict:
    """
    A série anual de uma empresa, pronta para mostrar ou calcular indicadores.

    Devolve um dicionário:
      empresa, cnpj, ticker, financeira (True para bancos/seguradoras),
      tabela: DataFrame com um ANO por linha e uma coluna por número (em reais).
    """
    if not Path(caminho_banco).exists():
        raise ErroDemonstrativos("O banco de balanços ainda não existe. Rode primeiro: python3 atualizar_cvm.py")

    conexao = abrir_banco(caminho_banco)
    try:
        cnpj, empresa = encontrar_cnpj(ticker, conexao)
        contas = ler_contas_anuais(cnpj, conexao)
        trimestrais = ler_contas_trimestrais(cnpj, conexao)
        acoes = acoes_em_circulacao(cnpj, conexao)
    finally:
        conexao.close()

    if contas.empty:
        raise ErroDemonstrativos(f"{ticker.upper()} ({empresa}) não tem balanços anuais no banco.")

    linhas = []
    detalhes = {}  # contas encontradas por nome, do ano mais recente
    for dt_refer, contas_do_ano in contas.groupby("dt_refer"):
        # Se houver consolidado e individual no mesmo ano, fica o consolidado.
        if contas_do_ano["consolidado"].max() == 1:
            contas_do_ano = contas_do_ano[contas_do_ano["consolidado"] == 1]
        detalhes = {}
        linha = calcular_ano(contas_do_ano, detalhes)
        linha["ano"] = int(str(dt_refer)[:4])
        linhas.append(linha)

    tabela = pd.DataFrame(linhas).set_index("ano").sort_index()
    # Se houver dois documentos no mesmo ano (troca de data de exercício), fica o último.
    tabela = tabela[~tabela.index.duplicated(keep="last")].tail(anos)

    return {
        "ticker": ticker.strip().upper(),
        "cnpj": cnpj,
        "empresa": empresa,
        "financeira": eh_financeira(contas),
        "tabela": tabela[COLUNAS],
        "contas_por_nome_ultimo_ano": detalhes,
        "ultimos_12_meses": ultimos_12_meses(contas, trimestrais),
        "acoes": acoes,
    }


# ---------------------------------------------------------------------------
# Últimos 12 meses (o dado mais atual) e quantidade de ações
# ---------------------------------------------------------------------------

def ler_contas_trimestrais(cnpj: str, conexao: sqlite3.Connection) -> pd.DataFrame:
    """Todas as contas dos balanços TRIMESTRAIS (ITR) de uma empresa."""
    return pd.read_sql_query(
        """SELECT dt_refer, demonstrativo, consolidado, dt_ini, cd_conta, ds_conta, valor
           FROM contas WHERE cnpj = ? AND fonte = 'ITR'""",
        conexao,
        params=(cnpj,),
    )


def _documento(contas: pd.DataFrame, dt_refer: str) -> pd.DataFrame:
    """As contas de um documento (data), preferindo o consolidado."""
    doc = contas[contas["dt_refer"] == dt_refer]
    if not doc.empty and doc["consolidado"].max() == 1:
        doc = doc[doc["consolidado"] == 1]
    return doc


def _acumulado_no_ano(doc: pd.DataFrame) -> pd.DataFrame:
    """
    De um documento trimestral, fica só com os valores ACUMULADOS no ano (de janeiro
    até a data do documento). A DRE trimestral traz duas versões de cada conta:
    só o trimestre e o acumulado; o acumulado é a que começa em 1º de janeiro.
    O fluxo de caixa trimestral já vem acumulado.
    """
    if doc.empty:
        return doc
    inicio_ano = str(doc["dt_refer"].iloc[0])[:4] + "-01-01"
    dre = doc[(doc["demonstrativo"] == "DRE") & (doc["dt_ini"] == inicio_ano)]
    dfc = doc[doc["demonstrativo"] == "DFC"]
    return pd.concat([dre, dfc])


def ultimos_12_meses(anuais: pd.DataFrame, trimestrais: pd.DataFrame):
    """
    Os números dos últimos 12 meses (em inglês, "TTM"), que deixam os múltiplos
    mais atuais do que usar só o último balanço anual.

        Últimos 12 meses = último ano fechado
                         + acumulado deste ano até o último trimestre
                         − acumulado do mesmo período do ano passado

    Ex.: com o balanço de junho/2026:  ano de 2025 + jan-jun/2026 − jan-jun/2025.
    O balanço patrimonial (dívida, caixa, patrimônio) é o do último trimestre.

    Devolve um dicionário com os números (como calcular_ano) e as chaves
    'referencia' (data) e 'tipo' ('12 meses' ou 'anual'). None se não houver dados.
    """
    if anuais.empty:
        return None
    ultimo_anual = str(anuais["dt_refer"].max())

    def so_anual():
        resultado = calcular_ano(_documento(anuais, ultimo_anual))
        resultado.update({"referencia": ultimo_anual, "tipo": "anual"})
        return resultado

    if trimestrais.empty or str(trimestrais["dt_refer"].max()) <= ultimo_anual:
        return so_anual()

    ultimo_trimestre = str(trimestrais["dt_refer"].max())
    ano = int(ultimo_trimestre[:4])
    atual = _documento(trimestrais, ultimo_trimestre)
    anterior = _documento(trimestrais, f"{ano - 1}{ultimo_trimestre[4:]}")
    ano_fechado = _documento(anuais, f"{ano - 1}-12-31")
    acumulado_atual = _acumulado_no_ano(atual)
    acumulado_anterior = _acumulado_no_ano(anterior)
    if acumulado_atual.empty or acumulado_anterior.empty or ano_fechado.empty:
        return so_anual()  # faltou alguma peça (ex.: empresa com ano fiscal diferente)

    def por_conta(doc):
        return doc.groupby(["demonstrativo", "cd_conta"])["valor"].sum()

    fluxos_anuais = ano_fechado[ano_fechado["demonstrativo"].isin(["DRE", "DFC"])]
    soma = por_conta(fluxos_anuais).add(por_conta(acumulado_atual), fill_value=0).sub(
        por_conta(acumulado_anterior), fill_value=0)
    # Só as contas que existem no trimestre atual (evita "contas fantasmas").
    soma = soma[soma.index.isin(por_conta(acumulado_atual).index)]

    nomes = acumulado_atual.drop_duplicates(["demonstrativo", "cd_conta"]).set_index(["demonstrativo", "cd_conta"])["ds_conta"]
    fluxos = pd.DataFrame({
        "demonstrativo": [d for d, _ in soma.index],
        "cd_conta": [c for _, c in soma.index],
        "ds_conta": [nomes.get(chave, "") for chave in soma.index],
        "valor": soma.values,
    })
    balanco = atual[atual["demonstrativo"].isin(["BPA", "BPP"])][["demonstrativo", "cd_conta", "ds_conta", "valor"]]
    resultado = calcular_ano(pd.concat([fluxos, balanco], ignore_index=True))
    resultado.update({"referencia": ultimo_trimestre, "tipo": "12 meses"})
    return resultado


def acoes_em_circulacao(cnpj: str, conexao: sqlite3.Connection):
    """
    Quantidade de ações em circulação no documento mais recente:
    total do capital menos as ações em tesouraria (recompradas pela empresa).
    None se a CVM não tiver essa informação.
    """
    linha = conexao.execute(
        """SELECT total, tesouraria, dt_refer FROM acoes
           WHERE cnpj = ? AND total > 0 ORDER BY dt_refer DESC, fonte LIMIT 1""",
        (cnpj,),
    ).fetchone()
    if not linha:
        return None
    total, tesouraria, dt_refer = linha
    return {"quantidade": float(total) - float(tesouraria or 0), "referencia": dt_refer}

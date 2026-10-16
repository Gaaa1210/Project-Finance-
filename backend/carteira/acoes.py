"""
Junta tudo para ações, ETFs e FIIs:
  planilha (suas compras) + cotações (Yahoo) + cálculos  =>  resumo da carteira

A função principal é 'resumir_acoes'. Ela recebe as compras e devolve:
  1. uma tabela com uma linha por ativo (preço médio, lucro, dividendos...);
  2. uma lista de avisos (ativos que não deu para cotar, por exemplo).
"""

from typing import Callable

import pandas as pd

from carteira import calculos_acoes as calc
from carteira.cotacoes import DadosCotacao, ErroCotacao, buscar_dados_ticker


def resumir_acoes(
    compras: pd.DataFrame,
    buscar_cotacao: Callable[[str], DadosCotacao] = buscar_dados_ticker,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Calcula a posição de cada ativo.

    'buscar_cotacao' é a função usada para buscar preços. Normalmente é a do
    Yahoo, mas nos testes passamos uma função com preços fixos. Assim dá para
    testar os cálculos sem internet.
    """
    linhas = []
    avisos = []

    # groupby("ticker") separa as compras por ativo: todas de PETR4 juntas etc.
    for ticker, compras_do_ativo in compras.groupby("ticker"):
        posicao = calc.calcular_preco_medio(compras_do_ativo)

        linha = {
            "ticker": ticker,
            # Se o mesmo ticker tiver tipos/setores diferentes, vale o da 1ª linha.
            "tipo": compras_do_ativo["tipo"].iloc[0],
            "setor": compras_do_ativo["setor"].iloc[0],
            "quantidade": posicao["quantidade"],
            "preco_medio": posicao["preco_medio"],
            "total_investido": posicao["total_investido"],
            "num_compras": len(compras_do_ativo),
            "primeira_compra": compras_do_ativo["data_compra"].min(),
        }

        try:
            dados = buscar_cotacao(ticker)
        except ErroCotacao as erro:
            # Sem cotação, mostramos o que sabemos (preço médio, investido)
            # e deixamos os campos de mercado vazios. O resto da carteira continua.
            avisos.append(str(erro))
            linhas.append(linha)
            continue

        valor_atual = calc.calcular_valor_atual(posicao["quantidade"], dados.preco_atual)
        lucro_reais, lucro_pct = calc.calcular_lucro(valor_atual, posicao["total_investido"])
        var_dia_reais, var_dia_pct = calc.calcular_variacao_dia(
            posicao["quantidade"], dados.preco_atual, dados.fechamento_anterior
        )
        dividendos = calc.calcular_dividendos_recebidos(compras_do_ativo, dados.dividendos)
        retorno_reais, retorno_pct = calc.calcular_retorno_total(
            valor_atual, dividendos, posicao["total_investido"]
        )

        linha.update({
            "preco_atual": dados.preco_atual,
            "valor_atual": valor_atual,
            "lucro_reais": lucro_reais,
            "lucro_pct": lucro_pct,
            "variacao_dia_reais": var_dia_reais,
            "variacao_dia_pct": var_dia_pct,
            "dividendos_recebidos": dividendos,
            "retorno_total_reais": retorno_reais,
            "retorno_total_pct": retorno_pct,
        })
        linhas.append(linha)

    nenhum_cotado = bool(linhas) and len(avisos) == len(linhas)

    # Remove avisos repetidos, mantendo a ordem (dict.fromkeys guarda só o 1º de cada).
    avisos = list(dict.fromkeys(avisos))

    # Se NENHUM ativo foi cotado, o problema provavelmente é a internet
    # (a não ser que o aviso já diga que falta instalar a biblioteca).
    if nenhum_cotado and not any("instalada" in a for a in avisos):
        avisos.insert(0, "Nenhum ativo foi cotado. Verifique sua conexão com a internet.")

    return pd.DataFrame(linhas), avisos


def totalizar_acoes(resumo: pd.DataFrame) -> dict:
    """
    Soma a carteira de ações inteira.
    Ativos sem cotação ficam de fora do valor atual e do lucro (para não distorcer),
    mas entram no total investido. O campo 'ativos_sem_cotacao' avisa quantos são.
    """
    if resumo.empty:
        return {"total_investido": 0.0, "valor_atual": 0.0, "lucro_reais": 0.0,
                "lucro_pct": 0.0, "variacao_dia_reais": 0.0, "dividendos_recebidos": 0.0,
                "ativos_sem_cotacao": 0}

    if "valor_atual" in resumo.columns:
        cotados = resumo[resumo["valor_atual"].notna()]
    else:
        cotados = resumo.iloc[0:0]  # tabela vazia: nada foi cotado

    investido_cotados = float(cotados["total_investido"].sum())
    valor_atual = float(cotados["valor_atual"].sum()) if not cotados.empty else 0.0
    lucro_reais, lucro_pct = calc.calcular_lucro(valor_atual, investido_cotados)

    return {
        "total_investido": float(resumo["total_investido"].sum()),
        "valor_atual": valor_atual,
        "lucro_reais": lucro_reais,
        "lucro_pct": lucro_pct,
        "variacao_dia_reais": float(cotados["variacao_dia_reais"].sum()) if not cotados.empty else 0.0,
        "dividendos_recebidos": float(cotados["dividendos_recebidos"].sum()) if not cotados.empty else 0.0,
        "ativos_sem_cotacao": len(resumo) - len(cotados),
    }

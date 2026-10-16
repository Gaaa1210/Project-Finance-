"""
Cálculos financeiros de ações, ETFs e FIIs.

Todas as funções aqui são "puras": recebem números e devolvem números.
Elas não acessam a internet nem a planilha. Isso facilita:
  - entender cada conta isoladamente;
  - testar com números que você mesmo escolhe;
  - mudar uma regra sem quebrar o resto.

Convenção: percentuais são frações. 0.10 significa 10%.
"""

import pandas as pd


# ---------------------------------------------------------------------------
# Custo e preço médio
# ---------------------------------------------------------------------------

def calcular_custo_compra(quantidade: float, preco_pago: float, taxas: float = 0.0) -> float:
    """
    Quanto saiu do seu bolso em UMA compra.
    Exemplo: 100 ações a R$ 30,00 com R$ 5,00 de taxas = 3.000 + 5 = R$ 3.005,00
    """
    return quantidade * preco_pago + taxas


def calcular_preco_medio(compras: pd.DataFrame) -> dict:
    """
    Junta várias compras do MESMO ativo e calcula o preço médio.

    Preço médio = custo total de todas as compras / quantidade total

    As taxas entram no custo, como manda a Receita Federal para o cálculo do IR.

    Exemplo:
      Compra 1: 100 ações a R$ 30,00 + R$ 5 de taxa = R$ 3.005
      Compra 2:  50 ações a R$ 36,00 + R$ 5 de taxa = R$ 1.805
      Total: 150 ações, R$ 4.810  ->  preço médio = 4.810 / 150 = R$ 32,07

    'compras' é uma tabela com as colunas: quantidade, preco_pago, taxas.
    """
    custos = [
        calcular_custo_compra(q, p, t)
        for q, p, t in zip(compras["quantidade"], compras["preco_pago"], compras["taxas"])
    ]
    quantidade_total = float(compras["quantidade"].sum())
    custo_total = float(sum(custos))

    return {
        "quantidade": quantidade_total,
        "total_investido": custo_total,
        "preco_medio": custo_total / quantidade_total,
    }


# ---------------------------------------------------------------------------
# Valor atual e lucro
# ---------------------------------------------------------------------------

def calcular_valor_atual(quantidade: float, preco_atual: float) -> float:
    """Quanto suas ações valem hoje: quantidade x preço atual."""
    return quantidade * preco_atual


def calcular_lucro(valor_atual: float, total_investido: float) -> tuple[float, float]:
    """
    Lucro (ou prejuízo, se negativo) em reais e em percentual.
    Exemplo: investiu 1.000, vale 1.200  ->  (200.0, 0.20)  =  R$ 200 e +20%
    """
    lucro_reais = valor_atual - total_investido
    lucro_percentual = lucro_reais / total_investido if total_investido else 0.0
    return lucro_reais, lucro_percentual


def calcular_variacao_dia(
    quantidade: float, preco_atual: float, fechamento_anterior: float
) -> tuple[float, float]:
    """
    Quanto o ativo mudou hoje em relação ao fechamento do pregão anterior.
    Devolve (variação em R$ na sua posição, variação em %).

    Limitação: se você comprou hoje, o valor em R$ considera o dia inteiro,
    não só a partir da hora da sua compra.
    """
    variacao_percentual = (preco_atual - fechamento_anterior) / fechamento_anterior
    variacao_reais = quantidade * (preco_atual - fechamento_anterior)
    return variacao_reais, variacao_percentual


# ---------------------------------------------------------------------------
# Dividendos
# ---------------------------------------------------------------------------

def calcular_quantidade_na_data(compras: pd.DataFrame, data: pd.Timestamp) -> float:
    """
    Quantas ações você tinha ANTES de uma data.

    Usamos isso com a "data ex" do dividendo: só recebe quem comprou ANTES dela.
    Quem compra na própria data ex já não tem direito àquele pagamento.
    """
    compradas_antes = compras[compras["data_compra"] < data]
    return float(compradas_antes["quantidade"].sum())


def calcular_dividendos_recebidos(compras: pd.DataFrame, dividendos: pd.Series) -> float:
    """
    Soma todos os proventos (dividendos, JCP, rendimentos de FII) que você recebeu.

    'dividendos' é uma série do pandas:
      índice = data ex do provento
      valor  = quanto foi pago POR AÇÃO

    Para cada provento: valor por ação x quantas ações você tinha antes da data ex.

    Limitações (importante!):
      - Os valores vêm do Yahoo Finance e são BRUTOS. O JCP tem 15% de IR retido
        na fonte, então o que caiu na sua conta pode ser menor.
      - O Yahoo às vezes não tem todos os proventos de ativos brasileiros.
    """
    if dividendos is None or len(dividendos) == 0:
        return 0.0

    total = 0.0
    for data_ex, valor_por_acao in dividendos.items():
        quantidade = calcular_quantidade_na_data(compras, data_ex)
        total += quantidade * float(valor_por_acao)
    return total


def calcular_retorno_total(
    valor_atual: float, dividendos_recebidos: float, total_investido: float
) -> tuple[float, float]:
    """
    Retorno total = valorização das ações + proventos recebidos.
    Devolve (retorno em R$, retorno em %).

    Exemplo: investiu 1.000, vale 1.100, recebeu 50 de dividendos
             -> R$ 150 e +15%
    """
    retorno_reais = valor_atual + dividendos_recebidos - total_investido
    retorno_percentual = retorno_reais / total_investido if total_investido else 0.0
    return retorno_reais, retorno_percentual
